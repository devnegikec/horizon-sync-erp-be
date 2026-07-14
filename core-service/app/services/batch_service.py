"""Batch service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import BatchNotFoundException, DuplicateBatchNoException
from app.models.base import BatchStatus
from app.models.batch import Batch
from app.repositories.batch_repository import BatchRepository
from app.schemas.batch import BatchCreate, BatchUpdate


class BatchService:
    """Service for batch operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BatchRepository(db)

    def create(self, data: BatchCreate, organization_id: UUID) -> Batch:
        """Create a new batch. Raises DuplicateBatchNoException if (batch_no, item_id) exists."""
        if self.repo.get_by_batch_no_and_item(
            data.batch_no, data.item_id, organization_id
        ):
            raise DuplicateBatchNoException(
                f"Batch '{data.batch_no}' already exists for this item"
            )
        d = data.model_dump()
        d["organization_id"] = organization_id
        if d.get("status"):
            try:
                d["status"] = BatchStatus(str(d["status"]).lower())
            except (ValueError, KeyError):
                d["status"] = BatchStatus.ACTIVE
        return self.repo.create(d)

    def get_by_id(self, batch_id: UUID, organization_id: UUID) -> Batch:
        """Get batch by ID. Raises BatchNotFoundException if not found."""
        b = self.repo.get_by_id(batch_id, organization_id)
        if not b:
            raise BatchNotFoundException(f"Batch with ID {batch_id} not found")
        return b

    def update(self, batch_id: UUID, data: BatchUpdate, organization_id: UUID) -> Batch:
        """Update a batch."""
        batch = self.get_by_id(batch_id, organization_id)
        d = data.model_dump(exclude_unset=True)
        if d.get("status"):
            try:
                d["status"] = BatchStatus(str(d["status"]).lower())
            except (ValueError, KeyError):
                del d["status"]
        return self.repo.update(batch, d)

    def delete(self, batch_id: UUID, organization_id: UUID) -> None:
        """Delete a batch."""
        batch = self.get_by_id(batch_id, organization_id)
        self.repo.delete(batch)

    def get_list(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Batch], dict]:
        """List batches with pagination."""
        page_size = min(page_size, 100)
        status_enum = None
        if status:
            try:
                status_enum = BatchStatus(str(status).lower())
            except (ValueError, KeyError):
                pass
        items, total = self.repo.list_batches(
            organization_id=organization_id,
            item_id=item_id,
            status=status_enum,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return items, pagination
