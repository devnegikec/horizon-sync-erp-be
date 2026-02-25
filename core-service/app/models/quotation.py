"""Quotation and quotation items models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
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
from app.models.base import QuotationStatus
from app.models.types import JSONB, UUID


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    quotation_no = Column(String(100), nullable=False)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    quotation_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    valid_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(
            QuotationStatus,
            name="quotationstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=QuotationStatus.DRAFT,
        nullable=False,
    )
    grand_total = Column(Numeric(15, 2), default=0)
    currency = Column(String(10), default="INR")
    remarks = Column(Text, nullable=True)
    # Document-level discount on total (sum of line totals)
    discount_type = Column(String(20), default="percentage", nullable=True)
    discount_value = Column(Numeric(15, 2), default=0, nullable=True)
    discount_amount = Column(Numeric(15, 2), default=0, nullable=True)
    converted_to_sales_order = Column(Boolean, default=False, nullable=False)
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

    items = relationship(
        "QuotationItem", back_populates="quotation", cascade="all, delete-orphan"
    )
    customer = relationship("Customer", foreign_keys=[customer_id])


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    quotation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    qty = Column(Numeric(15, 3), nullable=False)
    uom = Column(String(50), nullable=False)
    rate = Column(Numeric(15, 2), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    sort_order = Column(Integer, default=0)
    # Tax columns
    tax_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tax_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)  # amount - discount_amount + tax_amount
    # Discount: type 'flat' | 'percentage', value (fixed amount or %), computed discount_amount
    discount_type = Column(String(20), default="percentage", nullable=True)
    discount_value = Column(Numeric(15, 2), default=0, nullable=True)
    discount_amount = Column(Numeric(15, 2), default=0, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    quotation = relationship("Quotation", back_populates="items")
    item = relationship("Item")
