"""Product (shared catalog core) Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ProductBase(BaseModel):
    """Common product fields."""

    name: str = Field(..., min_length=1, max_length=255)
    sku: str | None = Field(None, max_length=100)
    gtin: str | None = Field(None, max_length=20)
    description: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_type: str | None = Field(None, max_length=20)
    images: list[str] | None = None
    tags: list[str] | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sku: str | None = Field(None, max_length=100)
    gtin: str | None = Field(None, max_length=20)
    description: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_type: str | None = Field(None, max_length=20)
    images: list[str] | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    sku: str | None = None
    gtin: str | None = None
    description: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    product_type: str | None = None
    images: list[str] | None = None
    tags: list[str] | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    products: list[ProductResponse]
    pagination: PaginationMeta
