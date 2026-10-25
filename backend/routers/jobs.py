"""
routers/jobs.py — Background job trigger and status-check endpoints.
"""
from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from schemas import JobStatusResponse, JobTriggerRequest
from sessions import get_current_user
from tasks import celery_app, dummy_task

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/trigger", response_model=JobStatusResponse)
async def trigger_job(
    body: JobTriggerRequest,
    current_user: dict = Depends(get_current_user),
):
    """Enqueue the dummy background task and return the task ID."""
    task = dummy_task.delay(body.message)
    return JobStatusResponse(task_id=task.id, status="queued")


@router.get("/{task_id}", response_model=JobStatusResponse)
async def job_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll the current status and result of a previously queued task."""
    result = AsyncResult(task_id, app=celery_app)
    return JobStatusResponse(
        task_id=task_id,
        status=result.status,
        result=result.result if result.ready() else None,
    )
