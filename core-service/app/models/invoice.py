"""Invoice and invoice items models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_no = Column(String(100), nullable=False)
    invoice_type = Column(String(50), nullable=False)
    party_id = Column(UUID(as_uuid=True), nullable=True)
    party_type = Column(String(50), nullable=True)
    posting_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="draft", nullable=False)
    grand_total = Column(Numeric(15, 2), default=0)
    outstanding_amount = Column(Numeric(15, 2), default=0)
    currency = Column(String(10), default="USD")
    reference_type = Column(String(100), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
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
    net_total = Column(Numeric(15, 2), default=0)
    total_tax = Column(Numeric(15, 2), default=0)
    total_charges = Column(Numeric(15, 2), default=0)
    discount_type = Column(String(20), default="percentage", nullable=True)
    discount_value = Column(Numeric(15, 2), default=0, nullable=True)
    
    # Subscription billing fields (Task 1B-1)
    billing_cycle = Column(String(20), nullable=True)  # monthly, quarterly, yearly
    subscription_period_start = Column(DateTime(timezone=True), nullable=True)
    subscription_period_end = Column(DateTime(timezone=True), nullable=True)
    seat_count = Column(Integer, nullable=True)  # Number of seats being billed
    credit_usage = Column(Numeric(15, 2), nullable=True)  # Credit consumption amount

    @property
    def invoice_date(self):
        """Alias for posting_date for backward compatibility"""
        return self.posting_date

    # Relationships
    items = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_code = Column(String(100), nullable=True)
    item_name = Column(String(255), nullable=True)
    qty = Column(Numeric(15, 3), nullable=False)
    uom = Column(String(50), nullable=False)
    rate = Column(Numeric(15, 2), nullable=True)
    amount = Column(Numeric(15, 2), nullable=True)
    sort_order = Column(Integer, default=0)
    # Tax columns
    tax_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tax_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    # Discount columns
    discount_type = Column(String(20), default="percentage", nullable=True)
    discount_value = Column(Numeric(15, 2), default=0, nullable=True)
    discount_amount = Column(Numeric(15, 2), default=0, nullable=True)
    total_amount = Column(
        Numeric(15, 2), default=0
    )  # amount - discount_amount + tax_amount
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    item = relationship("Item")
