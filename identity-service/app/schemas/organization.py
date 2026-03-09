"""Organization related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganizationBase(BaseModel):
    """Base organization schema with common fields"""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    website: str | None = Field(None, max_length=255)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    logo_url: str | None = Field(None, max_length=500)
    organization_type: str | None = Field(
        None, pattern="^(enterprise|business|startup|individual)$"
    )
    industry: str | None = Field(None, max_length=100)
    base_currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    status: str | None = Field(None, pattern="^(active|inactive|suspended|trial)$")


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization"""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for partial organization update"""

    name: str | None = Field(None, min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    website: str | None = Field(None, max_length=255)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    logo_url: str | None = Field(None, max_length=500)
    organization_type: str | None = Field(
        None, pattern="^(enterprise|business|startup|individual)$"
    )
    industry: str | None = Field(None, max_length=100)
    base_currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    status: str | None = Field(None, pattern="^(active|inactive|suspended|trial)$")
    is_active: bool | None = None
    settings: dict | None = None
    extra_data: dict | None = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""

    id: UUID
    owner_id: UUID | None = None
    is_active: bool
    status: str
    organization_type: str
    settings: dict | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationListItem(BaseModel):
    """Schema for organization in list response"""

    id: UUID
    name: str
    slug: str
    display_name: str | None = None
    status: str
    organization_type: str
    owner_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class OrganizationListResponse(BaseModel):
    """Schema for paginated organization list response"""

    organizations: list[OrganizationListItem]
    pagination: PaginationMeta
