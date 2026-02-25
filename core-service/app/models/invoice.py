"""Invoice and invoice items models"""

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
from app.models.base import InvoiceStatus, InvoiceType
from app.models.types import JSONB, UUID


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_no = Column(String(100), nullable=False)
    # DB column is 'posting_date'; expose as posting_date and as invoice_date for compatibility
    posting_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    invoice_type = Column(String(50), nullable=False)
    status = Column(String(50), default="Draft", nullable=False)
    party_id = Column(UUID(as_uuid=True), nullable=True)  # customer or supplier by invoice_type
    total_amount = Column(Numeric(15, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
    discount_type = Column(String(20), default="percentage", nullable=True)
    discount_value = Column(Numeric(15, 2), default=0, nullable=True)
    discount_amount = Column(Numeric(15, 2), default=0)
    total_paid = Column(Numeric(15, 2), default=0)
    balance_due = Column(Numeric(15, 2), default=0)
    currency = Column(String(10), default="USD")
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    
    @property
    def party_type(self):
        """Get party type based on invoice type"""
        return 'Customer' if self.invoice_type == 'SALES' else 'Supplier'
    
    @property
    def grand_total(self):
        """Alias for total_amount for backward compatibility"""
        return self.total_amount
    
    @property
    def outstanding_amount(self):
        """Alias for balance_due for backward compatibility"""
        return self.balance_due

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
