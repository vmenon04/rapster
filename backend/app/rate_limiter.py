"""
Production-grade async rate limiter with Upstash Redis support.
"""
import time
import asyncio
from typing import Optional, Any
from collections import defaultdict
from fastapi import HTTPException, status, Request
from app.logger import get_logger
from app.config import get_settings

logger = get_logger("rate_limiter")
settings = get_settings()

# Fallback in-memory store
_memory_store = defaultdict(list)

# Redis client (optional)
_redis_client: Optional[Any] = None
_redis_healthy = True  # Track Redis health


async def get_redis_client():
    """Get or create Redis client for Upstash."""
    global _redis_client, _redis_healthy
    
    # Return None immediately if Redis was marked unhealthy recently
    if not _redis_healthy:
        return None
    
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            
            # Get Upstash Redis URL from settings
            redis_url = getattr(settings, 'redis_url', None)
            if not redis_url:
                logger.warning("REDIS_URL not found in environment, falling back to memory store")
                _redis_client = False
                _redis_healthy = False
                return None
            
            # Create Redis client with Upstash-optimized settings
            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=20  # Connection pooling for Upstash
            )
            
            # Test connection
            await _redis_client.ping()
            logger.info("Upstash Redis connection established for rate limiting")
            _redis_healthy = True
            
        except ImportError:
            logger.warning("redis package not installed, falling back to memory store")
            _redis_client = False
            _redis_healthy = False
        except Exception as e:
            logger.warning(f"Upstash Redis not available, falling back to memory store: {e}")
            _redis_client = False
            _redis_healthy = False
    
    return _redis_client if _redis_client is not False else None


async def reset_redis_health():
    """Reset Redis health check (useful for recovery)."""
    global _redis_healthy, _redis_client
    _redis_healthy = True
    _redis_client = None  # Force reconnection


class AsyncRateLimiter:
    """Production-grade async rate limiter optimized for Upstash Redis."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._last_cleanup = 0
        self._cleanup_interval = 300  # Cleanup memory store every 5 minutes
    
    async def _cleanup_memory_store(self):
        """Periodic cleanup of memory store to prevent memory leaks."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            expired_keys = []
            for key, timestamps in _memory_store.items():
                # Clean old entries
                _memory_store[key] = [
                    req_time for req_time in timestamps
                    if current_time - req_time < self.window_seconds
                ]
                # Mark empty keys for removal
                if not _memory_store[key]:
                    expired_keys.append(key)
            
            # Remove empty keys
            for key in expired_keys:
                del _memory_store[key]
            
            self._last_cleanup = current_time
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit keys")
    
    async def _check_redis_limit(self, key: str, current_time: float) -> bool:
        """Check rate limit using Upstash Redis with optimized operations."""
        global _redis_healthy
        
        redis = await get_redis_client()
        if not redis:
            return await self._check_memory_limit(key, current_time)
        
        try:
            # For Upstash, use a single Lua script for atomic operations
            # This reduces round trips and improves performance
            lua_script = """
            local key = KEYS[1]
            local window_start = ARGV[1]
            local current_time = ARGV[2]
            local max_requests = tonumber(ARGV[3])
            local expiry = tonumber(ARGV[4])
            
            -- Remove expired entries
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
            
            -- Add current request
            redis.call('ZADD', key, current_time, current_time)
            
            -- Get count
            local count = redis.call('ZCARD', key)
            
            -- Set expiry
            redis.call('EXPIRE', key, expiry)
            
            return count
            """
            
            # Calculate window start
            window_start = current_time - self.window_seconds
            expiry = self.window_seconds + 10  # Buffer for clock skew
            
            # Execute Lua script
            request_count = await redis.eval(
                lua_script,
                1,  # Number of keys
                key,  # Key
                str(window_start),  # ARGV[1]
                str(current_time),  # ARGV[2] 
                str(self.max_requests),  # ARGV[3]
                str(expiry)  # ARGV[4]
            )
            
            return int(request_count) > self.max_requests
                
        except Exception as e:
            logger.error(f"Upstash Redis rate limit check failed: {e}")
            # Mark Redis as unhealthy for a short period
            _redis_healthy = False
            asyncio.create_task(self._schedule_redis_recovery())
            return await self._check_memory_limit(key, current_time)
    
    async def _schedule_redis_recovery(self):
        """Schedule Redis health recovery after a delay."""
        await asyncio.sleep(30)  # Wait 30 seconds before trying Redis again
        await reset_redis_health()
    
    async def _check_memory_limit(self, key: str, current_time: float) -> bool:
        """Fallback memory-based rate limiting with periodic cleanup."""
        await self._cleanup_memory_store()
        
        # Clean old entries for this specific key
        _memory_store[key] = [
            req_time for req_time in _memory_store[key]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check limit
        if len(_memory_store[key]) >= self.max_requests:
            return True
        
        # Add current request
        _memory_store[key].append(current_time)
        return False
    
    async def check_rate_limit(self, client_id: str) -> bool:
        """Check if rate limit is exceeded."""
        current_time = time.time()
        key = f"rate_limit:{client_id}"
        
        return await self._check_redis_limit(key, current_time)


def async_rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Async rate limiting dependency factory."""
    limiter = AsyncRateLimiter(max_requests, window_seconds)
    
    async def _rate_limit_dependency(request: Request):
        # Get client IP with proxy support
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if await limiter.check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(window_seconds)}
            )
    
    return _rate_limit_dependency


# User-specific rate limiting
def async_user_rate_limit(max_requests: int = 1000, window_seconds: int = 3600):
    """User-specific rate limiting (higher limits for authenticated users)."""
    limiter = AsyncRateLimiter(max_requests, window_seconds)
    
    async def _user_rate_limit_dependency(request: Request, current_user: Optional[Any] = None):
        # Use user ID if authenticated, otherwise fall back to IP
        if current_user and hasattr(current_user, 'id'):
            client_id = f"user:{current_user.id}"
        else:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
            client_id = f"ip:{client_ip}"
        
        if await limiter.check_rate_limit(client_id):
            logger.warning(f"Rate limit exceeded for: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(window_seconds)}
            )
    
    return _user_rate_limit_dependency
