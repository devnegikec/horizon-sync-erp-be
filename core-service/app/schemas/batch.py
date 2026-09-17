"""Batch related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class BatchBase(BaseModel):
    """Base batch schema with common fields"""

    batch_no: str = Field(..., min_length=1, max_length=100)
    item_id: UUID

    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None

    supplier_id: UUID | None = None
    supplier_batch_no: str | None = Field(None, max_length=100)

    status: str = Field(default="active")  # active, expired, consumed

    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    description: str | None = None
    extra_data: dict | None = None


class BatchCreate(BatchBase):
    """Schema for creating a new batch"""

    pass


class BatchUpdate(BaseModel):
    """Schema for updating a batch (all fields optional)"""

    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None

    supplier_id: UUID | None = None
    supplier_batch_no: str | None = Field(None, max_length=100)

    status: str | None = None

    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    description: str | None = None
    extra_data: dict | None = None


class BatchResponse(BaseModel):
    """Schema for batch response"""

    id: UUID
    organization_id: UUID
    batch_no: str
    item_id: UUID

    manufacturing_date: datetime | None = None
    expiry_date: datetime | None = None

    supplier_id: UUID | None = None
    supplier_batch_no: str | None = None

    status: str | None = None

    reference_type: str | None = None
    reference_id: UUID | None = None
    description: str | None = None
    extra_data: dict | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchListItem(BaseModel):
    """Schema for batch in list response"""

    id: UUID
    batch_no: str
    item_id: UUID
    sku: str | None = None
    product_name: str | None = None
    expiry_date: datetime | None = None
    status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchListResponse(BaseModel):
    """Schema for paginated batch list response"""

    batches: list[BatchListItem]
    pagination: PaginationMeta
