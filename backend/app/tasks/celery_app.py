from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "codesheriff",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.review_task"],   # ← tells Celery where to find tasks
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result expiry (1 day)
    result_expires=86400,
)
