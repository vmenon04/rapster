#!/usr/bin/env python3
"""
Simple RQ worker for background jobs.
"""
import os
import sys
import signal
from rq import Worker
from app.queue import get_queue_manager, Queues
from app.logger import get_logger

logger = get_logger("worker")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down worker...")
    sys.exit(0)


def main():
    """Run the RQ worker."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get queue manager
    queue_manager = get_queue_manager()
    logger.info("Worker starting...")
    
    # Get queues to process
    queues = [
        queue_manager.get_queue(Queues.AUDIO_PROCESSING),
        queue_manager.get_queue(Queues.DEFAULT)
    ]
    
    # Create and start worker
    worker = Worker(queues, connection=queue_manager.get_connection())
    
    logger.info(f"Worker listening on queues: {[q.name for q in queues]}")
    worker.work()


if __name__ == "__main__":
    main()
