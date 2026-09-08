"""Packing slip and packing slip item models.

A packing slip groups picked goods (from one or more completed outbound
orders) into an internal staging document. Items trace back to their source
pick list and order, and carry the bin / handling unit they were staged on.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PackingSlipStatus
from app.models.types import JSONB, UUID


class PackingSlip(Base):
    __tablename__ = "packing_slips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    packing_slip_no = Column(String(100), nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(
            PackingSlipStatus,
            name="packingslipstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=PackingSlipStatus.DRAFT,
        nullable=False,
    )

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    items = relationship(
        "PackingSlipItem", back_populates="packing_slip", cascade="all, delete-orphan"
    )


class PackingSlipItem(Base):
    __tablename__ = "packing_slip_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    packing_slip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("packing_slips.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Trace columns: which order and pick list the picked goods came from.
    # Plain UUIDs (no FK) so a packing slip survives source-document deletion.
    order_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    pick_list_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    qty = Column(Numeric(15, 3), nullable=False)
    uom = Column(String(50), nullable=False)
    per_case_qty = Column(Numeric(15, 3), nullable=True)
    case_qty = Column(Numeric(15, 3), nullable=True)
    loose_qty = Column(Numeric(15, 3), nullable=True)
    batch_no = Column(String(100), nullable=True)
    serial_nos = Column(JSONB, nullable=True)

    # Staging / pallet grouping.
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    handling_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("handling_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    packing_slip = relationship("PackingSlip", back_populates="items")
    item = relationship("Item")
