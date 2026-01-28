"""ItemPrice related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ItemPriceBase(BaseModel):
    """Base item price schema with common fields"""

    item_id: UUID
    price_list_id: UUID | None = None
    price: Decimal | None = None
    currency: str | None = Field(None, max_length=10)
    valid_from: datetime | None = None
    valid_upto: datetime | None = None
    min_qty: int | None = None
    extra_data: dict | None = None


class ItemPriceCreate(ItemPriceBase):
    """Schema for creating an item price"""

    pass


class ItemPriceUpdate(BaseModel):
    """Schema for updating an item price (all fields optional)"""

    price_list_id: UUID | None = None
    price: Decimal | None = None
    currency: str | None = Field(None, max_length=10)
    valid_from: datetime | None = None
    valid_upto: datetime | None = None
    min_qty: int | None = None
    extra_data: dict | None = None


class ItemPriceResponse(BaseModel):
    """Schema for item price response"""

    id: UUID
    organization_id: UUID
    item_id: UUID
    price_list_id: UUID | None = None
    price: Decimal | None = None
    currency: str | None = None
    valid_from: datetime | None = None
    valid_upto: datetime | None = None
    min_qty: int | None = None
    extra_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemPriceListItem(BaseModel):
    """Schema for item price in list response"""

    id: UUID
    item_id: UUID
    price_list_id: UUID | None = None
    price: Decimal | None = None
    currency: str | None = None
    valid_from: datetime | None = None
    valid_upto: datetime | None = None
    min_qty: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemPriceListResponse(BaseModel):
    """Schema for paginated item price list response"""

    item_prices: list[ItemPriceListItem]
    pagination: PaginationMeta
