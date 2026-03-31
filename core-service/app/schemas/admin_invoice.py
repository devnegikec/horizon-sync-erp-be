"""Pydantic schemas for admin invoice and payment tracking.

Admin-specific response schemas that extend existing invoice/payment list items
with cross-org fields (organization_name). Detail and creation schemas are reused
directly from the existing invoice and payment_entry modules.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PaginationMeta


# ── Admin Invoice Schemas ────────────────────────────────────────────


class AdminInvoiceListItem(BaseModel):
    """Single invoice in the admin cross-org paginated list.

    Mirrors InvoiceListItem fields and adds organization_name for cross-org context.
    Includes subscription billing fields for subscription invoices (Task 1B-1).
    """

    id: UUID
    organization_id: UUID
    organization_name: str | None = None
    invoice_no: str
    invoice_type: str
    party_id: UUID
    party_name: str | None = None
    party_code: str | None = None
    status: str
    posting_date: datetime
    due_date: datetime | None = None
    grand_total: Decimal
    outstanding_amount: Decimal | float | None = None
    created_at: datetime
    
    # Subscription billing fields (Task 1B-1)
    billing_cycle: str | None = None
    subscription_period_start: datetime | None = None 
    subscription_period_end: datetime | None = None
    seat_count: int | None = None
    credit_usage: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminInvoiceListResponse(BaseModel):
    """Paginated list of invoices for admin cross-org view."""

    invoices: list[AdminInvoiceListItem]
    pagination: PaginationMeta


# ── Admin Payment Schemas ────────────────────────────────────────────


class AdminPaymentListItem(BaseModel):
    """Single payment in the admin cross-org paginated list.

    Mirrors PaymentEntryListItem fields and adds organization_name for cross-org context.
    """

    id: UUID
    organization_id: UUID
    organization_name: str | None = None
    payment_type: str
    party_id: UUID
    amount: Decimal
    currency_code: str
    payment_date: datetime
    payment_mode: str
    reference_no: str | None = None
    status: str
    source: str
    receipt_number: str | None = None
    unallocated_amount: Decimal
    created_at: datetime

    # Party display
    party_name: str | None = None
    party_code: str | None = None
    party_email: str | None = None
    party_phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminPaymentListResponse(BaseModel):
    """Paginated list of payments for admin cross-org view."""

    payments: list[AdminPaymentListItem]
    page: int
    total_pages: int
    total_count: int
    page_size: int
