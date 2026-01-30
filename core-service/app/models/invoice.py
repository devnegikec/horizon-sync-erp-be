"""Invoice and invoice items models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.base import InvoiceStatus, InvoiceType
from app.models.types import JSONB


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_no = Column(String(100), nullable=False)
    invoice_type = Column(
        Enum(
            InvoiceType,
            name="invoicetype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
    )
    party_id = Column(UUID(as_uuid=True), nullable=False)
    party_type = Column(String(20), nullable=False)
    posting_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(
            InvoiceStatus,
            name="invoicestatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=InvoiceStatus.DRAFT,
        nullable=False,
    )
    grand_total = Column(Numeric(15, 2), default=0)
    outstanding_amount = Column(Numeric(15, 2), default=0)
    currency = Column(String(10), default="INR")
    reference_type = Column(String(50), nullable=True)
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
