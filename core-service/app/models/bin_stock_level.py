"""Bin stock level model for tracking stock at individual bin locations"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class BinStockLevel(Base):
    """Tracks stock quantity for a specific item at a specific bin location."""

    __tablename__ = "bin_stock_levels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )
    quantity_on_hand = Column(Numeric(15, 3), default=0)
    batch_number = Column(String(100), nullable=True)
    # Expiry date for FEFO (First Expired, First Out) picking. Nullable: when
    # absent, FIFO (created_at) ordering is used instead.
    expiry_date = Column(Date, nullable=True)
    packaging_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "bin_location_id", "item_id", "batch_number", name="uq_bin_item_batch"
        ),
    )

    # Relationships
    bin_location = relationship("WarehouseLocation", back_populates="bin_stock_levels")
    item = relationship("Item")
    packaging_unit = relationship("ItemPackagingUnit")

    def __repr__(self):
        return (
            f"<BinStockLevel(id={self.id}, bin={self.bin_location_id}, "
            f"item={self.item_id}, qty={self.quantity_on_hand})>"
        )
