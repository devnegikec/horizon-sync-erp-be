"""Supplier related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class SupplierBase(BaseModel):
    """Base supplier schema with common fields"""

    supplier_name: str = Field(..., min_length=1, max_length=255)
    supplier_code: str = Field(..., min_length=1, max_length=50)

    # Contact
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)

    # Address
    address: str | None = None
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    # Tax
    tax_number: str | None = Field(None, max_length=50)

    # Status
    status: str = Field(default="active")

    # Payment Terms (days)
    payment_terms: int = Field(default=30, ge=0)

    # Extra
    tags: list | dict | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None


class SupplierCreate(SupplierBase):
    """Schema for creating a new supplier"""

    pass


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier (all fields optional)"""

    supplier_name: str | None = Field(None, min_length=1, max_length=255)

    # Contact
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)

    # Address
    address: str | None = None
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    # Tax
    tax_number: str | None = Field(None, max_length=50)

    # Status
    status: str | None = None

    # Payment Terms
    payment_terms: int | None = Field(None, ge=0)

    # Extra
    tags: list | dict | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None


class SupplierResponse(BaseModel):
    """Schema for supplier response"""

    id: UUID
    organization_id: UUID
    supplier_name: str
    supplier_code: str

    # Contact
    email: str | None = None
    phone: str | None = None

    # Address
    address: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Tax
    tax_number: str | None = None

    # Status
    status: str

    # Payment Terms
    payment_terms: int

    # Extra
    tags: list | dict | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierListItem(BaseModel):
    """Schema for supplier in list response (lighter version)"""

    id: UUID
    supplier_name: str
    supplier_code: str
    email: str | None = None
    city: str | None = None
    status: str
    payment_terms: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierListResponse(BaseModel):
    """Schema for paginated supplier list response"""

    suppliers: list[SupplierListItem]
    pagination: PaginationMeta
