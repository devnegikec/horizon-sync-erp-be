"""RFQ (Request for Quotation) schemas"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class SupplierQuoteBase(BaseModel):
    """Base schema for Supplier Quote"""

    supplier_id: UUID
    quoted_price: Decimal | float = Field(..., ge=0, description="Quoted price must be non-negative")
    quoted_delivery_date: date
    supplier_notes: str | None = None


class SupplierQuoteCreate(SupplierQuoteBase):
    """Schema for creating Supplier Quote"""

    pass


class SupplierQuoteResponse(SupplierQuoteBase):
    """Schema for Supplier Quote response"""

    id: UUID
    organization_id: UUID
    rfq_line_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RFQLineBase(BaseModel):
    """Base schema for RFQ Line"""

    item_id: UUID
    quantity: Decimal | float = Field(..., gt=0, description="Quantity must be positive")
    required_date: date
    description: str | None = None


class RFQLineCreate(RFQLineBase):
    """Schema for creating RFQ Line"""

    pass


class RFQLineResponse(RFQLineBase):
    """Schema for RFQ Line response"""

    id: UUID
    organization_id: UUID
    rfq_id: UUID
    created_at: datetime
    updated_at: datetime
    quotes: list[SupplierQuoteResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RFQSupplierBase(BaseModel):
    """Base schema for RFQ Supplier"""

    supplier_id: UUID


class RFQSupplierCreate(RFQSupplierBase):
    """Schema for creating RFQ Supplier"""

    pass


class RFQSupplierResponse(RFQSupplierBase):
    """Schema for RFQ Supplier response"""

    id: UUID
    organization_id: UUID
    rfq_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RFQBase(BaseModel):
    """Base schema for RFQ"""

    closing_date: date


class RFQCreate(RFQBase):
    """Schema for creating RFQ"""

    material_request_id: UUID | None = None
    reference_type: str | None = Field(None, pattern="^MATERIAL_REQUEST$")
    reference_id: UUID | None = None
    line_items: list[RFQLineCreate] | None = Field(
        None, description="Line items (optional when creating from Material Request)"
    )
    supplier_ids: list[UUID] = Field(
        ..., min_length=1, description="At least one supplier required"
    )


class RFQUpdate(BaseModel):
    """Schema for updating RFQ (DRAFT only)"""

    closing_date: date | None = None
    line_items: list[RFQLineCreate] | None = None
    supplier_ids: list[UUID] | None = None


class RFQResponse(RFQBase):
    """Schema for RFQ response"""

    id: UUID
    organization_id: UUID
    material_request_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    status: str = Field(
        ...,
        pattern="^(draft|sent|partially_responded|fully_responded|closed)$",
    )
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    line_items: list[RFQLineResponse] = []
    suppliers: list[RFQSupplierResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RFQListItem(BaseModel):
    """Schema for RFQ list item"""

    id: UUID
    organization_id: UUID
    material_request_id: UUID | None = None
    status: str
    closing_date: date
    created_at: datetime
    created_by: UUID | None = None
    line_items_count: int = 0
    suppliers_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class RFQListResponse(BaseModel):
    """Schema for RFQ list response"""

    rfqs: list[RFQListItem]
    pagination: PaginationMeta


class RFQStatusUpdate(BaseModel):
    """Schema for RFQ status update"""

    status: str = Field(
        ...,
        pattern="^(draft|sent|partially_responded|fully_responded|closed)$",
    )


class RecordQuoteRequest(BaseModel):
    """Schema for recording supplier quote"""

    rfq_line_id: UUID
    supplier_id: UUID
    quoted_price: Decimal | float = Field(..., ge=0, description="Quoted price must be non-negative")
    quoted_delivery_date: date
    supplier_notes: str | None = None
