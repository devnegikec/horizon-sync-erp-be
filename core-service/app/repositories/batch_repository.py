"""Batch repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import BatchStatus
from app.models.batch import Batch


class BatchRepository:
    """Repository for batch database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Batch:
        """Create a new batch."""
        batch = Batch(**data)
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_by_id(self, batch_id: UUID, organization_id: UUID) -> Batch | None:
        """Get batch by ID."""
        return (
            self.db.query(Batch)
            .filter(
                Batch.id == batch_id,
                Batch.organization_id == organization_id,
            )
            .first()
        )

    def get_by_batch_no_and_item(
        self, batch_no: str, item_id: UUID, organization_id: UUID
    ) -> Batch | None:
        """Get batch by batch_no and item_id."""
        return (
            self.db.query(Batch)
            .filter(
                Batch.batch_no == batch_no,
                Batch.item_id == item_id,
                Batch.organization_id == organization_id,
            )
            .first()
        )

    def update(self, batch: Batch, data: dict) -> Batch:
        """Update batch fields."""
        for key, value in data.items():
            if hasattr(batch, key) and value is not None:
                setattr(batch, key, value)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def delete(self, batch: Batch) -> None:
        """Hard delete a batch."""
        self.db.delete(batch)
        self.db.commit()

    def list_batches(
        self,
        organization_id: UUID,
        item_id: UUID | None = None,
        status: BatchStatus | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Batch], int]:
        """List batches with filters and pagination."""
        query = self.db.query(Batch).filter(Batch.organization_id == organization_id)

        if item_id:
            query = query.filter(Batch.item_id == item_id)
        if status is not None:
            query = query.filter(Batch.status == status)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Batch.batch_no.ilike(term),
                    Batch.supplier_batch_no.ilike(term),
                    Batch.description.ilike(term),
                )
            )

        total = query.count()
        sort_col = getattr(Batch, sort_by, Batch.created_at)
        query = query.order_by(
            sort_col.desc() if sort_order == "desc" else sort_col.asc()
        )
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
