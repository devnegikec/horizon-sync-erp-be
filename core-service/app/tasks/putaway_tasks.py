"""Celery task: process a bulk put-away job in the background."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app import models as _models  # noqa: F401 - register every ORM mapper
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.bulk_put_away_job import BulkPutAwayJob, BulkPutAwayJobStatus
from app.services.put_away_service import PutAwayService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="putaway.complete_bulk",
    acks_late=True,
    reject_on_worker_lost=True,
)
def complete_bulk_putaway_task(self, job_id: str) -> None:
    """Complete a queued bulk put-away job and persist the per-item result."""
    db = SessionLocal()
    try:
        job = db.get(BulkPutAwayJob, UUID(job_id))
        if job is None:
            logger.warning("Bulk put-away job %s not found", job_id)
            return

        job.status = BulkPutAwayJobStatus.PROCESSING
        db.commit()

        request = job.request_data or {}
        org_id = UUID(request["organization_id"])
        worker_id = UUID(request["worker_id"])
        service = PutAwayService(db)

        if job.job_type == "items":
            result = service.complete_items_bulk(
                put_away_list_id=UUID(request["put_away_list_id"]),
                item_ids=[UUID(i) for i in request["item_ids"]],
                worker_id=worker_id,
                org_id=org_id,
                bin_id_override=(
                    UUID(request["bin_id"]) if request.get("bin_id") else None
                ),
            )
        else:  # "qr"
            result = service.complete_putaway_bulk(
                bin_id=UUID(request["bin_id"]),
                items=request["items"],
                worker_id=worker_id,
                org_id=org_id,
                put_away_list_id=(
                    UUID(request["put_away_list_id"])
                    if request.get("put_away_list_id")
                    else None
                ),
            )

        summary = result.get("summary", {})
        job.result = result
        job.completed_items = int(summary.get("completed_count", 0))
        job.failed_items = int(summary.get("failed_count", 0))
        job.total_items = job.completed_items + job.failed_items
        job.status = BulkPutAwayJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        db.commit()
        logger.info(
            "Bulk put-away job %s completed: %d ok, %d failed",
            job_id,
            job.completed_items,
            job.failed_items,
        )
    except Exception as exc:  # noqa: BLE001 - never take the worker down
        logger.exception("Bulk put-away job %s failed", job_id)
        db.rollback()
        try:
            job = db.get(BulkPutAwayJob, UUID(job_id))
            if job is not None:
                job.status = BulkPutAwayJobStatus.FAILED
                job.error = str(exc)
                job.completed_at = datetime.now(UTC)
                db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Could not mark bulk put-away job %s failed", job_id)
        raise
    finally:
        db.close()
