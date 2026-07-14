"""Item Price model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class ItemPrice(Base):
    """Item Price model for managing item pricing by price list"""

    __tablename__ = "item_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Primary fields
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_list_id = Column(UUID(as_uuid=True), nullable=True)
    price = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(10), nullable=True)

    # Validity period
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_upto = Column(DateTime(timezone=True), nullable=True)

    # Minimum quantity for this price
    min_qty = Column(Integer, nullable=True)

    # Additional data
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    item = relationship("Item", back_populates="item_prices")

    def __repr__(self) -> str:
        return f"<ItemPrice(id={self.id}, item_id={self.item_id}, price={self.price})>"
