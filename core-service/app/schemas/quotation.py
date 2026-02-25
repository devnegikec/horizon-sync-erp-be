"""Quotation schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ── Customer schemas (defined first so they can be referenced below) ──────────

class QuotationCustomerInfo(BaseModel):
    """Minimal customer info used in list responses"""

    id: UUID
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class QuotationCustomerDetail(BaseModel):
    """Full customer info used in detail / PDF responses"""

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


# ── Item-level schemas ────────────────────────────────────────────────────────

class QuotationItemStockLevels(BaseModel):
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    quantity_available: int = 0


class QuotationItemGroup(BaseModel):
    id: UUID
    name: str
    code: str


class QuotationTaxBreakupItem(BaseModel):
    rule_name: str
    tax_type: str
    rate: float
    is_compound: bool


class QuotationTaxInfo(BaseModel):
    id: UUID
    template_name: str
    template_code: str
    is_compound: bool
    breakup: list[QuotationTaxBreakupItem]


class QuotationItemBase(BaseModel):
    item_id: UUID
    qty: Decimal | float = Field(..., gt=0)
    uom: str = Field(..., min_length=1, max_length=50)
    rate: Decimal | float = Field(..., ge=0)
    amount: Decimal | float = Field(..., ge=0)
    sort_order: int = 0
    # Tax fields (optional on create - auto-calculated from item's tax template)
    tax_template_id: UUID | None = None
    tax_rate: Decimal | float = Field(default=0, ge=0, description="Tax % at quote time")
    tax_amount: Decimal | float = Field(default=0, ge=0, description="Tax currency value")
    total_amount: Decimal | float = Field(default=0, ge=0, description="amount - discount_amount + tax_amount")
    # Discount: type 'flat' | 'percentage', value (fixed amount or %), computed discount_amount
    discount_type: str = Field(default="percentage", pattern="^(flat|percentage)$", description="Discount type")
    discount_value: Decimal | float = Field(default=0, ge=0, description="Discount: % or fixed amount")
    discount_amount: Decimal | float = Field(default=0, ge=0, description="Computed discount amount")


class QuotationItemCreate(QuotationItemBase):
    """tax_template_id optional - tax calculated from item's applicable template if omitted"""


class QuotationItemResponse(QuotationItemBase):
    id: UUID
    organization_id: UUID
    quotation_id: UUID
    item_code: str | None = None
    item_name: str | None = None
    min_order_qty: int = 1
    max_order_qty: int | None = None
    standard_rate: str = "0.00"
    stock_levels: QuotationItemStockLevels
    item_group: QuotationItemGroup | None = None
    tax_info: QuotationTaxInfo | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Quotation schemas ─────────────────────────────────────────────────────────

class QuotationBase(BaseModel):
    quotation_no: str = Field(..., min_length=1, max_length=100)
    customer_id: UUID
    quotation_date: datetime
    valid_until: datetime | None = None
    status: str = Field(default="draft", pattern="^(draft|sent|accepted|rejected|expired)$")
    grand_total: Decimal | float = 0
    currency: str = Field(default="INR", max_length=10)
    remarks: str | None = None
    converted_to_sales_order: bool = False
    discount_type: str = Field(default="percentage", pattern="^(flat|percentage)$", description="Discount on total")
    discount_value: Decimal | float = Field(default=0, ge=0, description="Discount % or fixed amount on total")
    discount_amount: Decimal | float = Field(default=0, ge=0, description="Computed discount on total")


class QuotationCreate(BaseModel):
    """Create quotation schema - quotation_no is auto-generated"""

    quotation_no: str | None = Field(
        None, min_length=1, max_length=100, description="Auto-generated if not provided"
    )
    customer_id: UUID
    quotation_date: datetime
    valid_until: datetime | None = None
    status: str = Field(default="draft", pattern="^(draft|sent|accepted|rejected|expired)$")
    grand_total: Decimal | float = 0
    currency: str = Field(default="INR", max_length=10)
    remarks: str | None = None
    discount_type: str | None = Field(default="percentage", pattern="^(flat|percentage)$")
    discount_value: Decimal | float = Field(default=0, ge=0)
    discount_amount: Decimal | float = Field(default=0, ge=0)
    items: list[QuotationItemCreate] = []


class QuotationUpdate(BaseModel):
    quotation_date: datetime | None = None
    valid_until: datetime | None = None
    status: str | None = Field(None, pattern="^(draft|sent|accepted|rejected|expired)$")
    remarks: str | None = None
    discount_type: str | None = Field(None, pattern="^(flat|percentage)$")
    discount_value: Decimal | float | None = None
    discount_amount: Decimal | float | None = None
    items: list[QuotationItemCreate] | None = None


class QuotationResponse(QuotationBase):
    id: UUID
    organization_id: UUID
    customer: QuotationCustomerDetail | None = None
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    items: list[QuotationItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class QuotationListItem(BaseModel):
    id: UUID
    organization_id: UUID
    quotation_no: str
    customer: QuotationCustomerInfo | None = None
    status: str
    quotation_date: datetime
    valid_until: datetime | None = None
    grand_total: Decimal
    currency: str = "INR"
    discount_type: str | None = None
    discount_value: Decimal | float | None = None
    discount_amount: Decimal | float | None = None
    converted_to_sales_order: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuotationListResponse(BaseModel):
    quotations: list[QuotationListItem]
    pagination: PaginationMeta


class ConvertToSalesOrderResponse(BaseModel):
    sales_order_id: UUID
    sales_order_no: str
    message: str = "Quotation successfully converted to sales order"


class QuotationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(draft|sent|accepted|rejected|expired)$")
