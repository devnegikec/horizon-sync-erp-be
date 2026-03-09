"""Batch model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import BatchStatus
from app.models.types import JSONB, UUID


class Batch(Base):
    """Batch model for batch tracking on items"""

    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    batch_no = Column(String(100), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )

    manufacturing_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)

    supplier_id = Column(UUID(as_uuid=True), nullable=True)
    supplier_batch_no = Column(String(100), nullable=True)

    status = Column(
        Enum(
            BatchStatus,
            name="batchstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )

    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    description = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    item = relationship("Item", backref="batches")

    def __repr__(self):
        return (
            f"<Batch(id={self.id}, batch_no='{self.batch_no}', item_id={self.item_id})>"
        )
