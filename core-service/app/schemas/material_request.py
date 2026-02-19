"""Material Request schemas"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class MaterialRequestLineBase(BaseModel):
    """Base schema for Material Request Line"""

    item_id: UUID
    quantity: Decimal | float = Field(..., gt=0, description="Quantity must be positive")
    uom: str | None = Field(None, max_length=50, description="Unit of Measure (Kgs, Boxes, Pallets, etc.)")
    required_date: date
    description: str | None = None
    estimated_unit_cost: Decimal | float | None = Field(None, ge=0, description="Estimated cost per unit")
    requested_for: str | None = Field(None, max_length=255, description="Employee name or ID")
    requested_for_department: str | None = Field(None, max_length=100, description="Department name")


class MaterialRequestLineCreate(MaterialRequestLineBase):
    """Schema for creating Material Request Line"""

    pass


class MaterialRequestLineResponse(MaterialRequestLineBase):
    """Schema for Material Request Line response"""

    id: UUID
    organization_id: UUID
    material_request_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MaterialRequestBase(BaseModel):
    """Base schema for Material Request"""

    request_no: str | None = Field(None, max_length=50, description="Human-readable reference number (e.g., MR-2024-001)")
    type: str = Field(
        "purchase",
        pattern="^(purchase|transfer|issue)$",
        description="Request type: purchase (buy from vendor), transfer (move between warehouses), issue (give to department)"
    )
    priority: str = Field(
        "medium",
        pattern="^(low|medium|high|urgent)$",
        description="Priority level for procurement officer"
    )
    target_warehouse_id: UUID | None = Field(None, description="Target warehouse where goods should land")
    requested_by: UUID | None = Field(None, description="User ID who requested this")
    department: str | None = Field(None, max_length=100, description="Department requesting the materials")
    notes: str | None = None


class MaterialRequestCreate(MaterialRequestBase):
    """Schema for creating Material Request"""

    line_items: list[MaterialRequestLineCreate] = Field(
        ..., min_length=1, description="At least one line item required"
    )


class MaterialRequestUpdate(BaseModel):
    """Schema for updating Material Request (DRAFT only)"""

    request_no: str | None = Field(None, max_length=50)
    type: str | None = Field(None, pattern="^(purchase|transfer|issue)$")
    priority: str | None = Field(None, pattern="^(low|medium|high|urgent)$")
    target_warehouse_id: UUID | None = None
    requested_by: UUID | None = None
    department: str | None = Field(None, max_length=100)
    notes: str | None = None
    line_items: list[MaterialRequestLineCreate] | None = None


class MaterialRequestResponse(MaterialRequestBase):
    """Schema for Material Request response"""

    id: UUID
    organization_id: UUID
    status: str = Field(
        ...,
        pattern="^(draft|submitted|partially_quoted|fully_quoted|cancelled)$",
    )
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    line_items: list[MaterialRequestLineResponse] = []
    model_config = ConfigDict(from_attributes=True)


class MaterialRequestListItem(BaseModel):
    """Schema for Material Request list item"""

    id: UUID
    organization_id: UUID
    request_no: str | None = None
    type: str
    priority: str
    status: str
    department: str | None = None
    created_at: datetime
    created_by: UUID | None = None
    line_items_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class MaterialRequestListResponse(BaseModel):
    """Schema for Material Request list response"""

    material_requests: list[MaterialRequestListItem]
    pagination: PaginationMeta


class MaterialRequestStatusUpdate(BaseModel):
    """Schema for Material Request status update"""

    status: str = Field(
        ...,
        pattern="^(draft|submitted|partially_quoted|fully_quoted|cancelled)$",
    )
