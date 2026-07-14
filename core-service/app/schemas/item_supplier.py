"""ItemSupplier related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ItemSupplierBase(BaseModel):
    """Base item supplier schema with common fields"""

    item_id: UUID
    supplier_id: UUID
    supplier_part_no: str | None = Field(None, max_length=100)
    lead_time_days: int | None = None
    is_default: bool | None = None
    extra_data: dict | None = None


class ItemSupplierCreate(ItemSupplierBase):
    """Schema for creating an item supplier"""

    pass


class ItemSupplierUpdate(BaseModel):
    """Schema for updating an item supplier (all fields optional)"""

    supplier_part_no: str | None = Field(None, max_length=100)
    lead_time_days: int | None = None
    is_default: bool | None = None
    extra_data: dict | None = None


class ItemSupplierResponse(BaseModel):
    """Schema for item supplier response"""

    id: UUID
    organization_id: UUID
    item_id: UUID
    supplier_id: UUID
    supplier_part_no: str | None = None
    lead_time_days: int | None = None
    is_default: bool | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemSupplierListItem(BaseModel):
    """Schema for item supplier in list response"""

    id: UUID
    item_id: UUID
    supplier_id: UUID
    supplier_part_no: str | None = None
    lead_time_days: int | None = None
    is_default: bool | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemSupplierListResponse(BaseModel):
    """Schema for paginated item supplier list response"""

    item_suppliers: list[ItemSupplierListItem]
    pagination: PaginationMeta
