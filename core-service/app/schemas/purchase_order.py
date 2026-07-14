"""Purchase Order schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class PurchaseOrderLineBase(BaseModel):
    """Base schema for Purchase Order Line"""

    item_id: UUID
    quantity: Decimal | float = Field(
        ..., gt=0, description="Quantity must be positive"
    )
    unit_price: Decimal | float = Field(
        ..., ge=0, description="Unit price must be non-negative"
    )


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    """Schema for creating Purchase Order Line"""

    pass


class PurchaseOrderLineResponse(PurchaseOrderLineBase):
    """Schema for Purchase Order Line response"""

    id: UUID
    organization_id: UUID
    purchase_order_id: UUID
    line_total: Decimal
    received_quantity: Decimal
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderBase(BaseModel):
    """Base schema for Purchase Order"""

    purchase_order_no: str | None = Field(None, min_length=1, max_length=100)
    party_id: UUID = Field(..., description="Supplier ID")
    tax_rate: Decimal | float | None = Field(
        None, ge=0, le=1, description="Tax rate (0-1)"
    )
    discount_amount: Decimal | float | None = Field(
        None, ge=0, description="Discount amount"
    )


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating Purchase Order"""

    rfq_id: UUID | None = None
    reference_type: str | None = Field(None, pattern="^RFQ$")
    reference_id: UUID | None = None
    line_items: list[PurchaseOrderLineCreate] = Field(
        ..., min_length=1, description="At least one line item required"
    )


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating Purchase Order (DRAFT only)"""

    party_id: UUID | None = None
    tax_rate: Decimal | float | None = Field(None, ge=0, le=1)
    discount_amount: Decimal | float | None = Field(None, ge=0)
    line_items: list[PurchaseOrderLineCreate] | None = None


class PurchaseOrderResponse(PurchaseOrderBase):
    """Schema for Purchase Order response"""

    id: UUID
    organization_id: UUID
    rfq_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    party_type: str = Field(..., pattern="^SUPPLIER$")
    status: str = Field(
        ...,
        pattern="^(draft|submitted|partially_received|fully_received|closed|cancelled)$",
    )
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    line_items: list[PurchaseOrderLineResponse] = []
    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderListItem(BaseModel):
    """Schema for Purchase Order list item"""

    id: UUID
    organization_id: UUID
    purchase_order_no: str | None = None
    rfq_id: UUID | None = None
    party_id: UUID
    status: str
    grand_total: Decimal
    created_at: datetime
    created_by: UUID | None = None
    line_items_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderListResponse(BaseModel):
    """Schema for Purchase Order list response"""

    purchase_orders: list[PurchaseOrderListItem]
    pagination: PaginationMeta


class PurchaseOrderStatusUpdate(BaseModel):
    """Schema for Purchase Order status update"""

    status: str = Field(
        ...,
        pattern="^(draft|submitted|partially_received|fully_received|closed|cancelled)$",
    )
