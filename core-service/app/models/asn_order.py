"""Advance Stock Notice (ASN) order and items models"""

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
from app.models.base import AsnOrderStatus
from app.models.types import JSONB, UUID


class AsnOrder(Base):
    """Advance Stock Notice (ASN) order — pre-notification of incoming stock."""

    __tablename__ = "asn_orders"
    __audited__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asn_order_no = Column(String(100), nullable=False, index=True)

    # Warehouse references (from → to)
    warehouse_id_from = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )
    warehouse_id_to = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
        nullable=True,
    )

    order_date = Column(DateTime(timezone=True), nullable=False)
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(
            AsnOrderStatus,
            name="asnorderstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=AsnOrderStatus.DRAFT,
        nullable=False,
    )
    grand_total = Column(Numeric(15, 3), default=0)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    reference_no = Column(String(100), nullable=True)
    remarks = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    from_warehouse = relationship("Warehouse", foreign_keys=[warehouse_id_from])
    to_warehouse = relationship("Warehouse", foreign_keys=[warehouse_id_to])
    items = relationship(
        "AsnOrderItem", back_populates="asn_order", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AsnOrder(id={self.id}, no='{self.asn_order_no}', status={self.status})>"


class AsnOrderItem(Base):
    """Line item for an ASN order"""

    __tablename__ = "asn_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    asn_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asn_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    qty = Column(Numeric(15, 3), nullable=False)
    uom = Column(String(50), nullable=False)
    sort_order = Column(Integer, default=0)
    delivered_qty = Column(Numeric(15, 3), default=0, nullable=False)
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    asn_order = relationship("AsnOrder", back_populates="items")
    item = relationship("Item")

    def __repr__(self):
        return (
            f"<AsnOrderItem(id={self.id}, asn_order_id={self.asn_order_id}, "
            f"item_id={self.item_id}, qty={self.qty})>"
        )
