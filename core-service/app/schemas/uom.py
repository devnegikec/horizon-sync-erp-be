"""UOM related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class UOMBase(BaseModel):
    """Base UOM schema with common fields"""

    name: str = Field(..., min_length=1, max_length=50)
    abbreviation: str = Field(..., min_length=1, max_length=10)
    uom_type: str | None = Field(None, max_length=20, description="count | weight | volume | length | time")
    precision: int = Field(default=0, ge=0)
    description: str | None = None


class UOMCreate(UOMBase):
    """Schema for creating a new UOM"""

    pass


class UOMUpdate(BaseModel):
    """Schema for updating a UOM (all fields optional)"""

    name: str | None = Field(None, min_length=1, max_length=50)
    abbreviation: str | None = Field(None, min_length=1, max_length=10)
    uom_type: str | None = Field(None, max_length=20)
    precision: int | None = Field(None, ge=0)
    description: str | None = None


class UOMResponse(BaseModel):
    """Schema for UOM response"""

    id: UUID
    organization_id: UUID
    name: str
    abbreviation: str
    uom_type: str | None = None
    precision: int = 0
    description: str | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UOMListResponse(BaseModel):
    """Schema for paginated UOM list response"""

    uoms: list[UOMResponse]
    pagination: PaginationMeta
