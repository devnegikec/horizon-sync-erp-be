"""Queue adapter for QR Block generation."""

from uuid import UUID

from app.config import settings
from app.qr_block_tasks import generate_qr_block_task


def enqueue_qr_block(
    block_id: UUID,
    organization_id: UUID,
    task_id: str,
) -> None:
    generate_qr_block_task.apply_async(
        args=[str(block_id), str(organization_id)],
        task_id=task_id,
        queue=settings.celery_qr_queue_name,
    )
