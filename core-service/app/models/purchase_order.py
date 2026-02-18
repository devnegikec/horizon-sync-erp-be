"""Purchase Order model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text
from app.models.types import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PurchaseOrderStatus
from app.models.types import JSONB


class PurchaseOrder(Base):
    """Purchase Order model for procurement workflow"""

    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Reference to RFQ (optional)
    rfq_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)

    # Party (Supplier)
    party_type = Column(String(50), nullable=False, default="SUPPLIER")
    party_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Status
    status = Column(
        Enum(
            PurchaseOrderStatus,
            name="purchaseorderstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
    )

    # Financial fields
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(15, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(5, 4), nullable=True)
    discount_amount = Column(Numeric(15, 2), nullable=False, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)

    # Extra
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
    line_items = relationship(
        "PurchaseOrderLine",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<PurchaseOrder(id={self.id}, status='{self.status}', grand_total={self.grand_total})>"


class PurchaseOrderLine(Base):
    """Purchase Order Line Item model"""

    __tablename__ = "purchase_order_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    purchase_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantity and pricing
    quantity = Column(Numeric(15, 4), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    line_total = Column(Numeric(15, 2), nullable=False, default=0)

    # Received quantity tracking
    received_quantity = Column(Numeric(15, 4), nullable=False, default=0)

    # Extra
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="line_items")

    def __repr__(self):
        return f"<PurchaseOrderLine(id={self.id}, item_id={self.item_id}, quantity={self.quantity}, unit_price={self.unit_price})>"
