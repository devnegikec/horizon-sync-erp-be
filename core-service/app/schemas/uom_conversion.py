"""UOM Conversion related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class UOMConversionBase(BaseModel):
    """Base UOM Conversion schema with common fields"""

    item_id: UUID
    from_uom: str = Field(..., min_length=1, max_length=50)
    to_uom: str = Field(..., min_length=1, max_length=50)
    conversion_factor: Decimal = Field(..., gt=0)


class UOMConversionCreate(UOMConversionBase):
    """Schema for creating a new UOM Conversion"""

    pass


class UOMConversionUpdate(BaseModel):
    """Schema for updating a UOM Conversion (all fields optional)"""

    from_uom: str | None = Field(None, min_length=1, max_length=50)
    to_uom: str | None = Field(None, min_length=1, max_length=50)
    conversion_factor: Decimal | None = Field(None, gt=0)


class UOMConversionResponse(BaseModel):
    """Schema for UOM Conversion response"""

    id: UUID
    organization_id: UUID
    item_id: UUID
    from_uom: str
    to_uom: str
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
