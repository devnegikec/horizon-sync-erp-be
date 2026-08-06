"""Durable QR Block generation tasks."""

import logging
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.qr_product_service import QRProductService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="qseal.generate_block",
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_qr_block_task(
    self,
    block_id: str,
    organization_id: str,
) -> None:
    """Generate one tenant-scoped QR Block and persist its terminal state."""
    db = SessionLocal()
    try:
        QRProductService(db).process_block(
            UUID(block_id),
            UUID(organization_id),
            task_id=self.request.id,
        )
    except Exception:
        logger.exception(
            "QR Block worker task failed: block_id=%s organization_id=%s",
            block_id,
            organization_id,
        )
        raise
    finally:
        db.close()
