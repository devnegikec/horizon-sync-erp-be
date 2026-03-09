"""ItemSupplier model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ItemSupplier(Base):
    """Item-supplier link (item_suppliers). supplier_id has no FK in DDL; validated in service."""

    __tablename__ = "item_suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    supplier_part_no = Column(String(100), nullable=True)
    lead_time_days = Column(Integer, nullable=True)
    is_default = Column(Boolean, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    item = relationship("Item", backref="item_suppliers")

    def __repr__(self):
        return (
            f"<ItemSupplier(id={self.id}, item_id={self.item_id}, "
            f"supplier_id={self.supplier_id})>"
        )
