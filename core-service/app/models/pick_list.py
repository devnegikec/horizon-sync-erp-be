"""Pick list and pick list items models"""

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
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PickListStatus
from app.models.types import JSONB, UUID


class PickList(Base):
    __tablename__ = "pick_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pick_list_no = Column(String(100), nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(
            PickListStatus,
            name="pickliststatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=PickListStatus.DRAFT,
        nullable=False,
    )
    pick_date = Column(DateTime(timezone=True), nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    remarks = Column(Text, nullable=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Columns added by migration 047 for SAP invoice-triggered outbound workflow
    invoice_reference = Column(String(255), nullable=True)
    invoice_data = Column(JSONB, nullable=True)
    dispatch_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dispatch_records.id"),
        nullable=True,
    )

    # Columns added by migration 095 for staging (PR-10 / T-10, WF-019/020).
    staging_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    staged_at = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    items = relationship(
        "PickListItem", back_populates="pick_list", cascade="all, delete-orphan"
    )
    dispatch_record = relationship("DispatchRecord", foreign_keys=[dispatch_record_id])


class PickListItem(Base):
    __tablename__ = "pick_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pick_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pick_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )
    qty = Column(Numeric(15, 3), nullable=False)
    picked_qty = Column(Numeric(15, 3), default=0)
    uom = Column(String(50), nullable=False)
    per_case_qty = Column(Numeric(15, 3), nullable=True)
    case_qty = Column(Numeric(15, 3), nullable=True)
    loose_qty = Column(Numeric(15, 3), nullable=True)
    batch_no = Column(String(100), nullable=True)
    serial_nos = Column(JSONB, nullable=True)
    sort_order = Column(Integer, default=0)
    # Column added by migration 047 for bin location tracking
    bin_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_locations.id"),
        nullable=True,
    )
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    pick_list = relationship("PickList", back_populates="items")
    bin_location = relationship("WarehouseLocation")
