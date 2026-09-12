"""Bin stock level model for tracking stock at individual bin locations"""

import enum
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


class InventoryStatus(str, enum.Enum):
    """Inventory status values for bin stock levels.

    - ``available``: normal, pickable stock.
    - ``blocked``: physically blocked / not usable.
    - ``damaged``: damaged goods (exception-handled).
    - ``hold``: operational hold pending review.
    - ``quality``: quality-control quarantine.
    - ``reserved``: reserved for an existing allocation (complements the
      worker-level ``bin_reservation`` table).
    - ``picked``: picked out of the source bin, awaiting staging (WF-016).
    - ``in_transit_to_stage``: en route to the staging lane (WF-016 / PR-10).
    """

    AVAILABLE = "available"
    BLOCKED = "blocked"
    DAMAGED = "damaged"
    HOLD = "hold"
    QUALITY = "quality"
    RESERVED = "reserved"
    PICKED = "picked"
    IN_TRANSIT_TO_STAGE = "in_transit_to_stage"


#: Valid bin-stock status transitions for the outbound pick flow
#: (``available → picked → in_transit_to_stage``, WF-016 / T-09).
INVENTORY_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    InventoryStatus.AVAILABLE.value: frozenset({InventoryStatus.PICKED.value}),
    InventoryStatus.PICKED.value: frozenset(
        {InventoryStatus.IN_TRANSIT_TO_STAGE.value, InventoryStatus.AVAILABLE.value}
    ),
    InventoryStatus.IN_TRANSIT_TO_STAGE.value: frozenset(
        {InventoryStatus.AVAILABLE.value}
    ),
}


def can_transition_inventory_status(current: str | None, target: str) -> bool:
    """Return True if ``current`` → ``target`` is a valid status transition.

    Same-status is always allowed (idempotent / replay-safe no-op).
    """
    current = current or InventoryStatus.AVAILABLE.value
    if current == target:
        return True
    return target in INVENTORY_STATUS_TRANSITIONS.get(current, frozenset())


# Statuses eligible for pick allocation (FEFO/FIFO resolution). PR-02 makes this
# configurable via ``pick.inventory_statuses_pickable``; default is ``available``.
PICKABLE_INVENTORY_STATUSES: list[str] = [InventoryStatus.AVAILABLE.value]


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
    inventory_status = Column(
        String(20),
        nullable=False,
        default=InventoryStatus.AVAILABLE.value,
        index=True,
    )
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
