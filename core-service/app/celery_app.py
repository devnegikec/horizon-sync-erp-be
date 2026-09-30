"""Celery application for durable Core Service background jobs."""

from celery import Celery

from app.config import settings

broker_url = settings.celery_broker_url or settings.redis_url

celery_app = Celery(
    "horizon_core",
    broker=broker_url,
    include=[
        "app.qr_block_tasks",
        "app.tasks.transfer_reconciliation",
        "app.tasks.putaway_tasks",
    ],
)
celery_app.conf.update(
    task_default_queue=settings.celery_qr_queue_name,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": settings.celery_visibility_timeout_seconds,
    },
)

# Scheduled jobs (run with `celery -A app.celery_app beat`).
celery_app.conf.beat_schedule = {
    "transfer-reconcile-missing-serials": {
        "task": "transfer.reconcile_missing_serials",
        "schedule": 86400.0,  # daily
    },
}
