"""Invoice schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class InvoiceBase(BaseModel):
    invoice_no: str | None = Field(None, min_length=1, max_length=100)
    invoice_type: str = Field(..., pattern="^(sales|purchase)$")
    party_id: UUID
    party_type: str = Field(..., min_length=1, max_length=20)
    posting_date: datetime
    due_date: datetime | None = None
    status: str = Field(
        default="draft", pattern="^(draft|pending|paid|partial|overdue|cancelled)$"
    )
    grand_total: Decimal | float = 0
    outstanding_amount: Decimal | float = 0
    currency: str = Field(default="INR", max_length=10)
    reference_type: str | None = None
    reference_id: UUID | None = None
    remarks: str | None = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    posting_date: datetime | None = None
    due_date: datetime | None = None
    status: str | None = Field(
        None, pattern="^(draft|pending|paid|partial|overdue|cancelled)$"
    )
    remarks: str | None = None


class CustomerDetails(BaseModel):
    customer_name: str
    customer_code: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    tax_number: str | None = None
    status: str | None = None


class SupplierDetails(BaseModel):
    supplier_name: str
    supplier_code: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    tax_number: str | None = None
    status: str | None = None


class InvoiceItemResponse(BaseModel):
    id: UUID
    organization_id: UUID
    invoice_id: UUID
    item_id: UUID | None = None
    item_code: str | None = None
    item_name: str | None = None
    description: str | None = None
    qty: Decimal
    uom: str
    rate: Decimal | None = None
    amount: Decimal | None = None
    sort_order: int | None = None
    tax_template_id: str | None = None
    tax_rate: str | None = None
    tax_amount: str | None = None
    total_amount: str | None = None
    min_order_qty: int | None = None
    max_order_qty: int | None = None
    standard_rate: str | None = None
    tax_info: dict | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceResponse(InvoiceBase):
    id: UUID
    organization_id: UUID
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    customer: CustomerDetails | None = None
    supplier: SupplierDetails | None = None
    items: list[InvoiceItemResponse] | None = None
    model_config = ConfigDict(from_attributes=True)


class InvoiceListItem(BaseModel):
    id: UUID
    organization_id: UUID
    invoice_no: str
    invoice_type: str
    party_id: UUID
    status: str
    posting_date: datetime
    grand_total: Decimal
    outstanding_amount: Decimal | float | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvoiceListResponse(BaseModel):
    invoices: list[InvoiceListItem]
    pagination: PaginationMeta
