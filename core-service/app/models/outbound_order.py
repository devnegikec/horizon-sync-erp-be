"""Outbound order and outbound order item models.

An outbound order is the upstream document (ASN or SAP sales order) that a
pick list is generated from. Importing a PDF/CSV order file now creates
``OutboundOrder`` rows (not pick lists); a confirmed order is then converted
into one or more pick lists (split per assigned worker).
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
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import (
    OutboundOrderItemStockStatus,
    OutboundOrderStatus,
    OutboundOrderType,
)
from app.models.types import JSONB, UUID


class OutboundOrder(Base):
    __tablename__ = "outbound_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    order_no = Column(String(100), nullable=False)
    order_type = Column(
        Enum(
            OutboundOrderType,
            name="outboundordertype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=OutboundOrderType.SAP,
        nullable=False,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(
            OutboundOrderStatus,
            name="outboundorderstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=OutboundOrderStatus.DRAFT,
        nullable=False,
    )
    invoice_reference = Column(String(255), nullable=True)
    source_filename = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Upstream document linkage (e.g. an internal-transfer ASN that generated
    # this order at the source warehouse).
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    reference_no = Column(String(100), nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    items = relationship(
        "OutboundOrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OutboundOrderItem(Base):
    __tablename__ = "outbound_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    outbound_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("outbound_orders.id", ondelete="CASCADE"),
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
    uom = Column(String(50), nullable=False)
    sku = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    per_case_qty = Column(Numeric(15, 3), nullable=True)
    case_qty = Column(Numeric(15, 3), nullable=True)
    loose_qty = Column(Numeric(15, 3), nullable=True)
    batch_no = Column(String(100), nullable=True)

    # Fulfilment availability snapshot, refreshed whenever the order is listed
    # or confirmed: in_stock when available >= qty, else out_of_stock.
    stock_status = Column(
        Enum(
            OutboundOrderItemStockStatus,
            name="outboundorderitemstockstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=OutboundOrderItemStockStatus.OUT_OF_STOCK,
        nullable=False,
    )
    available_qty = Column(Numeric(15, 3), nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    order = relationship("OutboundOrder", back_populates="items")
    item = relationship("Item")
