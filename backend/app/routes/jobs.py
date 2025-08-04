"""
Simple job management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.queue import get_queue_manager
from app.dependencies import get_current_user
from app.models import User
from app.logger import get_logger

logger = get_logger("jobs_api")
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get the status of a background job."""
    queue_manager = get_queue_manager()
    status = queue_manager.get_job_status(job_id)
    
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return {"job": status}


@router.post("/cancel/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Cancel a background job."""
    queue_manager = get_queue_manager()
    success = queue_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be cancelled"
        )
    
    return {"message": f"Job {job_id} cancelled"}
