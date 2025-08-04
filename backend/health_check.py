#!/usr/bin/env python3
"""
Docker health check script for the music app.
"""
import sys
import os
import requests
import time

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.queue import get_queue_manager
from app.logger import get_logger

logger = get_logger("health_check")


def check_api_health():
    """Check if the API is responding."""
    try:
        response = requests.get("http://localhost:8000/audio/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
        return False
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        return False


def check_redis_connection():
    """Check Redis connection."""
    try:
        queue_manager = get_queue_manager()
        connection = queue_manager.get_connection()
        connection.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


def check_worker_queues():
    """Check if workers are processing jobs."""
    try:
        queue_manager = get_queue_manager()
        
        # Check queue accessibility
        info = queue_manager.get_queue_info("default")
        return info is not None
    except Exception as e:
        logger.error(f"Queue health check failed: {e}")
        return False


def main():
    """Run all health checks."""
    print("🏥 Music App Health Check")
    print("=" * 40)
    
    checks = [
        ("🌐 API Server", check_api_health),
        ("📡 Redis Connection", check_redis_connection), 
        ("🔄 Worker Queues", check_worker_queues),
    ]
    
    all_healthy = True
    
    for name, check_func in checks:
        try:
            result = check_func()
            status = "✅ HEALTHY" if result else "❌ UNHEALTHY"
            print(f"{name:<20} {status}")
            
            if not result:
                all_healthy = False
        except Exception as e:
            print(f"{name:<20} ❌ ERROR: {e}")
            all_healthy = False
    
    print("=" * 40)
    
    if all_healthy:
        print("🎉 All systems healthy!")
        sys.exit(0)
    else:
        print("⚠️  Some systems are unhealthy!")
        sys.exit(1)


if __name__ == "__main__":
    main()
