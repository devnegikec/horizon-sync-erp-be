"""Invoice and invoice items models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Numeric,
    String,
    Text,
)
from app.models.types import UUID

from app.database import Base
from app.models.types import JSONB


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_no = Column(String(100), nullable=False)
    invoice_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    invoice_type = Column(String(50), nullable=False)
    status = Column(String(50), default="Draft", nullable=False)
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), nullable=True)
    total_amount = Column(Numeric(15, 2), default=0)
    tax_amount = Column(Numeric(15, 2), default=0)
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
    def party_id(self):
        """Get party ID based on invoice type"""
        return self.customer_id if self.invoice_type == 'SALES' else self.supplier_id
    
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
    def posting_date(self):
        """Alias for invoice_date for backward compatibility"""
        return self.invoice_date
