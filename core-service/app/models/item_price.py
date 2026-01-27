"""ItemPrice model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ItemPrice(Base):
    """Item price by price list (item_prices table). No created_by/updated_by in DDL."""

    __tablename__ = "item_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    price_list_id = Column(UUID(as_uuid=True), nullable=True)
    price = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(10), nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_upto = Column(DateTime(timezone=True), nullable=True)
    min_qty = Column(Integer, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    item = relationship("Item", backref="item_prices")

    def __repr__(self):
        return f"<ItemPrice(id={self.id}, item_id={self.item_id}, price={self.price})>"
