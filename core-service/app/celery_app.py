"""
Celery application configuration for async QR block generation.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "qr_generation",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    result_expires=86400,  # Results expire after 24 hours
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["app.tasks"])
