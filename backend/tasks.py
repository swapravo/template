"""
tasks.py — Celery application and all task definitions.
Tasks are thin dispatchers — they call functions from other modules.
No inline business logic. No raw DB queries. No HTTP calls.
"""
import time

from celery import Celery

from config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(bind=True, name="tasks.dummy_task")
def dummy_task(self, message: str) -> dict:
    """
    Dummy task for smoke-testing the Celery broker and worker connection.
    Simulates 2 seconds of work and returns a confirmation payload.
    Replace the body with a real dispatch call when building real tasks.
    """
    time.sleep(2)
    return {"received": message, "status": "done", "task_id": self.request.id}
