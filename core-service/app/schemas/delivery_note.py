"""Delivery note schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class CustomerInfo(BaseModel):
    """Customer information embedded in delivery note"""

    customer_name: str
    customer_code: str
    phone: str | None = None
    email: str | None = None


class WarehouseInfo(BaseModel):
    """Warehouse information embedded in delivery note"""

    warehouse_name: str
    warehouse_code: str


class NestedReference(BaseModel):
    """Nested reference details (id, name, code)"""

    id: str
    name: str
    code: str


class NestedReferenceWithType(BaseModel):
    """Nested reference with type (for sales_order, pick_list, etc.)"""

    id: str
    reference_type: str
    name: str
    code: str


class DeliveryNoteItemBase(BaseModel):
    item_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    rate: Decimal | float | None = None
    amount: Decimal | float | None = None
    warehouse_id: UUID | None = None
    batch_no: str | None = None
    serial_nos: list[str] | None = None
    sort_order: int = 0


class DeliveryNoteItemCreate(DeliveryNoteItemBase):
    pass


class DeliveryNoteItemResponse(BaseModel):
    """Delivery note item with enriched item details"""

    id: UUID
    item: NestedReference | None = None
    qty: Decimal
    uom: str
    rate: Decimal | None = None
    amount: Decimal | None = None
    warehouse_id: UUID | None = None
    batch_no: str | None = None
    serial_nos: list[str] | None = None
    sort_order: int
    extra_data: dict | None = None
    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteBase(BaseModel):
    delivery_note_no: str | None = Field(None, min_length=1, max_length=100)
    customer_id: UUID
    delivery_date: datetime
    status: str = Field(default="draft", pattern="^(draft|submitted|cancelled)$")
    warehouse_id: UUID | None = None
    pick_list_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    remarks: str | None = Field(None, max_length=1000)


class DeliveryNoteCreate(DeliveryNoteBase):
    items: list[DeliveryNoteItemCreate] = Field(default_factory=list)


class DeliveryNoteUpdate(BaseModel):
    delivery_date: datetime | None = None
    status: str | None = Field(None, pattern="^(draft|submitted|cancelled)$")
    warehouse_id: UUID | None = None
    remarks: str | None = Field(None, max_length=1000)


class DeliveryNoteResponse(DeliveryNoteBase):
    id: UUID
    organization_id: UUID
    customer: CustomerInfo | None = None
    warehouse: WarehouseInfo | None = None
    reference: NestedReferenceWithType | None = None
    items: list[DeliveryNoteItemResponse] = Field(default_factory=list)
    extra_data: dict | None = None
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteListItem(BaseModel):
    id: UUID
    organization_id: UUID
    delivery_note_no: str
    customer_id: UUID
    customer: CustomerInfo | None = None
    status: str
    delivery_date: datetime
    warehouse_id: UUID | None = None
    warehouse: WarehouseInfo | None = None
    remarks: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteListResponse(BaseModel):
    delivery_notes: list[DeliveryNoteListItem]
    pagination: PaginationMeta


class ConvertToInvoiceItemRequest(BaseModel):
    """Single item to bill from a delivery note"""

    item_id: UUID
    qty_to_bill: Decimal | float = Field(..., gt=0)


class ConvertToInvoiceRequest(BaseModel):
    """Request body for converting a delivery note to an invoice.
    Only delivered items (from the DN) can be billed."""

    items: list[ConvertToInvoiceItemRequest] = Field(..., min_length=1)
    due_date: datetime | None = None
    remarks: str | None = None


class ConvertToInvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_no: str
    grand_total: Decimal
    message: str = "Delivery note successfully converted to invoice"
