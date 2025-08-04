"""
FastAPI dependencies for authentication and database management.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import extract_user_from_token
from app.crud import get_user_by_id_async
from app.models import User
from app.logger import get_logger
from app.exceptions import DatabaseError

logger = get_logger("dependencies")

# Security scheme
security = HTTPBearer()

# Database dependency
def get_database_client():
    """Get database client for dependency injection."""
    from app.crud import supabase_client
    try:
        yield supabase_client
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get the current authenticated user."""
    try:
        # Validate token format
        if not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is required"
            )
        
        # Extract user info from token
        user_data = extract_user_from_token(credentials.credentials)
        user_id = user_data["user_id"]
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database (now async)
        user = await get_user_by_id_async(user_id)
        if not user:
            logger.warning(f"User not found in database: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        return user
        
    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error during authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user


# Import rate limiting from dedicated module
from app.rate_limiter import async_rate_limit, async_user_rate_limit

# Convenience aliases for different rate limits
rate_limit_strict = async_rate_limit(max_requests=50, window_seconds=60)
rate_limit_normal = async_rate_limit(max_requests=100, window_seconds=60)
rate_limit_upload = async_rate_limit(max_requests=10, window_seconds=300)  # 10 uploads per 5 min
user_rate_limit = async_user_rate_limit(max_requests=1000, window_seconds=3600)  # 1000 per hour for users
