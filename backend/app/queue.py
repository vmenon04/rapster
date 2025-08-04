"""
Simple Redis Queue (RQ) configuration and job management.
"""
import redis
from rq import Queue, Job
from typing import Optional, Dict, Any
from app.config import get_settings
from app.logger import get_logger

logger = get_logger("queue")
settings = get_settings()


class Queues:
    """Queue names."""
    DEFAULT = "default"
    AUDIO_PROCESSING = "audio_processing"


class QueueManager:
    """Simple queue manager for RQ operations."""
    
    def __init__(self):
        """Initialize the queue manager."""
        self._connection = None
        self._queues = {}
        
    def get_connection(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._connection is None:
            self._connection = redis.from_url(
                settings.redis_url,
                decode_responses=False,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            # Test connection
            try:
                self._connection.ping()
                logger.info("Connected to Redis")
            except redis.ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._connection
    
    def get_queue(self, name: str = Queues.DEFAULT) -> Queue:
        """Get or create a queue."""
        if name not in self._queues:
            connection = self.get_connection()
            self._queues[name] = Queue(name, connection=connection)
        return self._queues[name]
    
    def enqueue_job(self, queue_name: str, func, *args, **kwargs) -> Job:
        """Enqueue a job for background processing."""
        queue = self.get_queue(queue_name)
        job = queue.enqueue(func, *args, **kwargs)
        logger.info(f"Enqueued job {job.id} in queue '{queue_name}'")
        return job
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status by ID."""
        try:
            job = Job.fetch(job_id, connection=self.get_connection())
            return {
                "id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        try:
            job = Job.fetch(job_id, connection=self.get_connection())
            job.cancel()
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return False


# Global queue manager instance
_queue_manager = None


def get_queue_manager() -> QueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager
"""
Simple Redis Queue (RQ) configuration and job management.
"""
import redis
from rq import Queue, Job
from typing import Optional, Dict, Any
from app.config import get_settings
from app.logger import get_logger

logger = get_logger("queue")
settings = get_settings()


class Queues:
    """Queue names."""
    DEFAULT = "default"
    AUDIO_PROCESSING = "audio_processing"


class QueueManager:
    """Simple queue manager for RQ operations."""
    
    def __init__(self):
        """Initialize the queue manager."""
        self._connection = None
        self._queues = {}
        
    def get_connection(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._connection is None:
            self._connection = redis.from_url(
                settings.redis_url,
                decode_responses=False,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            # Test connection
            try:
                self._connection.ping()
                logger.info("Connected to Redis")
            except redis.ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._connection
    
    def get_queue(self, name: str = Queues.DEFAULT) -> Queue:
        """Get or create a queue."""
        if name not in self._queues:
            connection = self.get_connection()
            self._queues[name] = Queue(name, connection=connection)
        return self._queues[name]
    
    def enqueue_job(self, queue_name: str, func, *args, **kwargs) -> Job:
        """Enqueue a job for background processing."""
        queue = self.get_queue(queue_name)
        job = queue.enqueue(func, *args, **kwargs)
        logger.info(f"Enqueued job {job.id} in queue '{queue_name}'")
        return job
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status by ID."""
        try:
            job = Job.fetch(job_id, connection=self.get_connection())
            return {
                "id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        try:
            job = Job.fetch(job_id, connection=self.get_connection())
            job.cancel()
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return False


# Global queue manager instance
_queue_manager = None


def get_queue_manager() -> QueueManager:
    """Get the global queue manager instance."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager
