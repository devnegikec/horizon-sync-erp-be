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
    required_date: date
    description: str | None = None


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

    notes: str | None = None


class MaterialRequestCreate(MaterialRequestBase):
    """Schema for creating Material Request"""

    line_items: list[MaterialRequestLineCreate] = Field(
        ..., min_length=1, description="At least one line item required"
    )


class MaterialRequestUpdate(BaseModel):
    """Schema for updating Material Request (DRAFT only)"""

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
    status: str
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
