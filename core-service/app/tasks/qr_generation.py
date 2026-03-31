"""
Celery task for async QR block generation.
"""
import logging
from datetime import UTC, datetime
from uuid import UUID

import redis
import sqlalchemy.exc
from celery import Task

from app.celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.repositories.qr_product_repository import QRBlockRepository
from app.services.credit_service import CreditService
from app.services.qr_product_service import QRProductService
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""

    _db = None

    @property
    def db(self):
        """Get or create database session."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        """Close database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(
        sqlalchemy.exc.OperationalError,
        redis.exceptions.ConnectionError,
    ),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def generate_qr_block_task(
    self,
    block_id: str,
    organization_id: str,
    user_id: str,
):
    """
    Background task to generate QR block.

    Args:
        block_id: UUID of the QRBlock
        organization_id: UUID of the organization
        user_id: UUID of the user who created the block
    """
    logger.info(
        f"Starting QR block generation: block_id={block_id}, "
        f"task_id={self.request.id}, org_id={organization_id}"
    )

    db = self.db
    block_repo = QRBlockRepository(db)

    try:
        # Load block
        block = block_repo.get_by_id(UUID(block_id), UUID(organization_id))
        if not block:
            raise ValueError(f"Block not found: {block_id}")

        # Update status to in_progress
        block.status = "in_progress"
        block.task_status = "started"
        db.commit()

        # Initialize service
        service = QRProductService(db)

        # Load product
        product = service.get_product(block.product_id, UUID(organization_id))
        if not product:
            raise ValueError(f"Product not found: {block.product_id}")

        # Load brand and decrypt key if needed
        brand = None
        private_key = None
        if product.brand_id and service.key_service:
            from app.repositories.brand_repository import BrandRepository

            brand_repo = BrandRepository(db)
            brand = brand_repo.get_by_id(product.brand_id, UUID(organization_id))
            if brand and brand.private_key_encrypted:
                private_key = service.key_service.decrypt_private_key(
                    brand.private_key_encrypted
                )

        # Generate items in batches
        batch_size = settings.celery_batch_size
        total_items = block.quantity

        for batch_start in range(0, total_items, batch_size):
            batch_end = min(batch_start + batch_size, total_items)
            batch_count = batch_end - batch_start

            # Generate batch
            service._generate_product_items_batch(
                block=block,
                product=product,
                brand=brand,
                private_key=private_key,
                organization_id=UUID(organization_id),
                user_id=UUID(user_id),
                start_index=batch_start,
                count=batch_count,
            )

            # Update progress
            block.progress_current = batch_end
            db.commit()

            # Update Celery task state
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": batch_end,
                    "total": total_items,
                    "percent": int((batch_end / total_items) * 100),
                    "status": f"Generated {batch_end}/{total_items} items",
                },
            )

            logger.info(
                f"Batch complete: {batch_end}/{total_items} items for block {block_id}"
            )

        # Generate Excel file
        logger.info(f"Generating Excel file for block {block_id}...")
        excel_bytes, filename = service._build_excel_for_block(
            block.id, UUID(organization_id)
        )

        # Upload to GCS
        logger.info(f"Uploading Excel to GCS for block {block_id}...")
        gcs_path = f"qr-blocks/{organization_id}/{block.id}/{filename}"
        storage_service.upload_file(
            gcs_path,
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Get signed URL
        download_url = storage_service.get_signed_url(gcs_path, expiry_minutes=60)

        # Mark completed
        block.status = "completed"
        block.task_status = "success"
        block.download_url = download_url
        block.completed_at = datetime.now(UTC)
        db.commit()

        # Deduct credits
        credit_service = CreditService(db)
        credit_service.deduct_credits(UUID(organization_id), block.id, block.quantity)

        logger.info(
            f"QR block generation complete: block_id={block_id}, "
            f"items_generated={total_items}"
        )

        return {
            "block_id": block_id,
            "status": "completed",
            "items_generated": total_items,
        }

    except Exception as e:
        logger.exception(
            f"QR block generation failed: block_id={block_id}, error={str(e)}"
        )

        # Update block status to failed
        try:
            block = block_repo.get_by_id(UUID(block_id), UUID(organization_id))
            if block:
                block.status = "failed"
                block.task_status = "failure"
                block.error_message = str(e)[:1000]  # Truncate to 1000 chars
                db.commit()
        except Exception as update_error:
            logger.exception(
                f"Failed to update block status: block_id={block_id}, "
                f"error={str(update_error)}"
            )

        # Retry if retries remaining
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        raise
