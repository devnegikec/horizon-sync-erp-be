"""Sales Order schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta

# ── Customer schemas ──────────────────────────────────────────────────────────


class SalesOrderCustomerInfo(BaseModel):
    """Minimal customer info used in list responses"""

    id: UUID
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class SalesOrderCustomerDetail(BaseModel):
    """Full customer info used in detail responses"""

    id: UUID
    name: str
    code: str
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

    model_config = ConfigDict(from_attributes=True)


class SalesOrderItemStockLevels(BaseModel):
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    quantity_available: int = 0


class SalesOrderItemGroup(BaseModel):
    id: UUID
    name: str
    code: str


class SalesOrderTaxBreakupItem(BaseModel):
    rule_name: str
    tax_type: str
    rate: float
    is_compound: bool


class SalesOrderTaxInfo(BaseModel):
    id: UUID
    template_name: str
    template_code: str
    is_compound: bool
    breakup: list[SalesOrderTaxBreakupItem]


class SalesOrderItemBase(BaseModel):
    item_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    rate: Decimal | float = Field(..., ge=0)
    amount: Decimal | float = Field(..., ge=0)
    sort_order: int = 0
    # Tax fields (optional on create - auto-calculated from item's tax template)
    tax_template_id: UUID | None = None
    tax_rate: Decimal | float = Field(
        default=0, ge=0, description="Tax % at order time"
    )
    tax_amount: Decimal | float = Field(
        default=0, ge=0, description="Tax currency value"
    )
    total_amount: Decimal | float = Field(
        default=0, ge=0, description="amount - discount_amount + tax_amount"
    )
    discount_type: str = Field(
        default="percentage", pattern="^(flat|percentage)$", description="Discount type"
    )
    discount_value: Decimal | float = Field(
        default=0, ge=0, description="Discount % or fixed amount"
    )
    discount_amount: Decimal | float = Field(
        default=0, ge=0, description="Computed discount amount"
    )


class SalesOrderItemCreate(SalesOrderItemBase):
    """tax_template_id optional - tax calculated from item's applicable template if omitted"""


class SalesOrderItemResponse(SalesOrderItemBase):
    id: UUID
    organization_id: UUID
    sales_order_id: UUID
    item_code: str | None = None
    item_name: str | None = None
    min_order_qty: int = 1
    max_order_qty: int | None = None
    standard_rate: str = "0.00"
    stock_levels: SalesOrderItemStockLevels
    item_group: SalesOrderItemGroup | None = None
    tax_info: SalesOrderTaxInfo | None = None
    billed_qty: Decimal | float = 0
    delivered_qty: Decimal | float = 0
    pending_billing_qty: Decimal | float = 0
    pending_delivery_qty: Decimal | float = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SalesOrderBase(BaseModel):
    sales_order_no: str | None = Field(None, min_length=1, max_length=100)
    customer_id: UUID
    order_date: datetime
    delivery_date: datetime | None = None
    status: str = Field(
        default="draft",
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    )
    grand_total: Decimal | float = 0
    currency: str = Field(default="INR", max_length=10)
    discount_type: str | None = Field(
        default="percentage",
        pattern="^(flat|percentage)$",
        description="Document-level discount type",
    )
    discount_value: Decimal | float | None = Field(
        default=0, ge=0, description="Discount % or fixed amount"
    )
    discount_amount: Decimal | float | None = Field(
        default=0, ge=0, description="Computed document discount amount"
    )
    reference_type: str | None = None
    reference_id: UUID | None = None
    remarks: str | None = Field(None, max_length=1000)


class SalesOrderCreate(SalesOrderBase):
    items: list[SalesOrderItemCreate] = []


class SalesOrderUpdate(BaseModel):
    order_date: datetime | None = None
    delivery_date: datetime | None = None
    status: str | None = Field(
        None,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    )
    remarks: str | None = Field(None, max_length=1000)
    discount_type: str | None = Field(
        None, pattern="^(flat|percentage)$", description="Document-level discount type"
    )
    discount_value: Decimal | float | None = Field(
        default=None, ge=0, description="Discount % or fixed amount"
    )
    discount_amount: Decimal | float | None = Field(
        default=None, ge=0, description="Computed document discount amount"
    )
    items: list[SalesOrderItemCreate] | None = None


class SalesOrderResponse(SalesOrderBase):
    id: UUID
    organization_id: UUID
    customer: SalesOrderCustomerDetail | None = None
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    items: list[SalesOrderItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class SalesOrderListItem(BaseModel):
    id: UUID
    organization_id: UUID
    sales_order_no: str
    customer_id: UUID
    customer: SalesOrderCustomerInfo | None = None
    status: str
    order_date: datetime
    grand_total: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SalesOrderListResponse(BaseModel):
    sales_orders: list[SalesOrderListItem]
    pagination: PaginationMeta


class ConvertToInvoiceItemRequest(BaseModel):
    item_id: UUID
    qty_to_bill: Decimal | float = Field(..., gt=0)


class ConvertToInvoiceRequest(BaseModel):
    items: list[ConvertToInvoiceItemRequest]


class ConvertToInvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_no: str
    message: str = "Sales order successfully converted to invoice"


class ConvertToDeliveryNoteItemRequest(BaseModel):
    item_id: UUID
    qty_to_deliver: Decimal | float = Field(..., gt=0)


class ConvertToDeliveryNoteRequest(BaseModel):
    items: list[ConvertToDeliveryNoteItemRequest]


class ConvertToDeliveryNoteResponse(BaseModel):
    delivery_note_id: UUID
    delivery_note_no: str
    message: str = "Sales order successfully converted to delivery note"


class SalesOrderStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    )
