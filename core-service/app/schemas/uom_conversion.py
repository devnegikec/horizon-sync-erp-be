"""UOM Conversion related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class UOMConversionBase(BaseModel):
    """Base UOM Conversion schema with common fields"""

    item_id: UUID | None = None
    from_uom: str = Field(..., min_length=1, max_length=50)
    to_uom: str = Field(..., min_length=1, max_length=50)
    from_uom_id: UUID | None = None
    to_uom_id: UUID | None = None
    conversion_factor: Decimal = Field(..., gt=0)


class UOMConversionCreate(UOMConversionBase):
    """Schema for creating a new UOM Conversion"""

    pass


class UOMConversionUpdate(BaseModel):
    """Schema for updating a UOM Conversion (all fields optional)"""

    from_uom: str | None = Field(None, min_length=1, max_length=50)
    to_uom: str | None = Field(None, min_length=1, max_length=50)
    from_uom_id: UUID | None = None
    to_uom_id: UUID | None = None
    conversion_factor: Decimal | None = Field(None, gt=0)


class UOMConversionResponse(BaseModel):
    """Schema for UOM Conversion response"""

    id: UUID
    organization_id: UUID
    item_id: UUID | None = None
    from_uom: str
    to_uom: str
    from_uom_id: UUID | None = None
    to_uom_id: UUID | None = None
    conversion_factor: Decimal
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UOMConversionListResponse(BaseModel):
    """Schema for paginated UOM Conversion list response"""

    uom_conversions: list[UOMConversionResponse]
    pagination: PaginationMeta


class UOMConversionBulkItem(BaseModel):
    """A single UOM conversion row in a bulk upsert request."""

    item_id: UUID | None = None
    from_uom: str = Field(..., min_length=1, max_length=50)
    to_uom: str = Field(..., min_length=1, max_length=50)
    from_uom_id: UUID | None = None
    to_uom_id: UUID | None = None
    conversion_factor: Decimal | None = Field(None, gt=0)
    action: Literal["create", "modify", "delete"] | None = None


class UOMConversionBulkRequest(BaseModel):
    """Bulk upsert request body."""

    conversions: list[UOMConversionBulkItem]


class UOMConversionBulkError(BaseModel):
    row: int
    error: str


class UOMConversionBulkResponse(BaseModel):
    """Bulk upsert response with per-row error reporting."""

    created: int
    updated: int
    deleted: int = 0
    errors: list[UOMConversionBulkError]
