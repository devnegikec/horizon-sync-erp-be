"""Item Price schemas for request/response validation"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import PaginationMeta


class ItemPriceBase(BaseModel):
    """Base schema for ItemPrice"""

    item_id: UUID = Field(..., description="Item UUID")
    price_list_id: UUID | None = Field(None, description="Price list UUID")
    price: Decimal | None = Field(None, ge=0, description="Item price")
    currency: str | None = Field(None, max_length=10, description="Currency code")
    valid_from: datetime | None = Field(None, description="Valid from date")
    valid_upto: datetime | None = Field(None, description="Valid until date")
    min_qty: int | None = Field(
        None, ge=0, description="Minimum quantity for this price"
    )
    extra_data: dict | None = Field(None, description="Additional data")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        """Validate currency code format"""
        if v is not None:
            v = v.upper().strip()
            if len(v) < 2 or len(v) > 10:
                raise ValueError("Currency code must be between 2 and 10 characters")
        return v

    @field_validator("valid_upto")
    @classmethod
    def validate_date_range(cls, v: datetime | None, info) -> datetime | None:
        """Validate that valid_upto is after valid_from"""
        if v is not None and info.data.get("valid_from") is not None:
            if v <= info.data["valid_from"]:
                raise ValueError("valid_upto must be after valid_from")
        return v


class ItemPriceCreate(ItemPriceBase):
    """Schema for creating an item price"""

    item_id: UUID = Field(..., description="Item UUID (required)")


class ItemPriceUpdate(BaseModel):
    """Schema for updating an item price"""

    price_list_id: UUID | None = Field(None, description="Price list UUID")
    price: Decimal | None = Field(None, ge=0, description="Item price")
    currency: str | None = Field(None, max_length=10, description="Currency code")
    valid_from: datetime | None = Field(None, description="Valid from date")
    valid_upto: datetime | None = Field(None, description="Valid until date")
    min_qty: int | None = Field(
        None, ge=0, description="Minimum quantity for this price"
    )
    extra_data: dict | None = Field(None, description="Additional data")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        """Validate currency code format"""
        if v is not None:
            v = v.upper().strip()
            if len(v) < 2 or len(v) > 10:
                raise ValueError("Currency code must be between 2 and 10 characters")
        return v

    @field_validator("valid_upto")
    @classmethod
    def validate_date_range(cls, v: datetime | None, info) -> datetime | None:
        """Validate that valid_upto is after valid_from"""
        if v is not None and info.data.get("valid_from") is not None:
            if v <= info.data["valid_from"]:
                raise ValueError("valid_upto must be after valid_from")
        return v


class ItemPriceResponse(ItemPriceBase):
    """Schema for item price response"""

    id: UUID = Field(..., description="Item price UUID")
    organization_id: UUID = Field(..., description="Organization UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional item details (when include_item=True)
    item: dict | None = Field(None, description="Item details")

    model_config = {"from_attributes": True}

    @field_validator("item", mode="before")
    @classmethod
    def serialize_item(cls, v):
        """Convert SQLAlchemy Item object to dict if needed"""
        if v is None:
            return None
        if hasattr(v, "__dict__"):
            # Convert SQLAlchemy object to dict
            item_dict = {}
            for key in [
                "id",
                "item_code",
                "item_name",
                "description",
                "item_type",
                "uom",
            ]:
                if hasattr(v, key):
                    value = getattr(v, key)
                    # Convert UUID to string for JSON serialization
                    if hasattr(value, "hex"):
                        value = str(value)
                    item_dict[key] = value
            return item_dict
        return v


class ItemPriceListItem(BaseModel):
    """Schema for item price in list responses"""

    id: UUID = Field(..., description="Item price UUID")
    item_id: UUID = Field(..., description="Item UUID")
    price_list_id: UUID | None = Field(None, description="Price list UUID")
    price: Decimal | None = Field(None, description="Item price")
    currency: str | None = Field(None, description="Currency code")
    valid_from: datetime | None = Field(None, description="Valid from date")
    valid_upto: datetime | None = Field(None, description="Valid until date")
    min_qty: int | None = Field(None, description="Minimum quantity")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional item details
    item: dict | None = Field(None, description="Item details")

    model_config = {"from_attributes": True}

    @field_validator("item", mode="before")
    @classmethod
    def serialize_item(cls, v):
        """Convert SQLAlchemy Item object to dict if needed"""
        if v is None:
            return None
        if hasattr(v, "__dict__"):
            # Convert SQLAlchemy object to dict
            item_dict = {}
            for key in [
                "id",
                "item_code",
                "item_name",
                "description",
                "item_type",
                "uom",
            ]:
                if hasattr(v, key):
                    value = getattr(v, key)
                    # Convert UUID to string for JSON serialization
                    if hasattr(value, "hex"):
                        value = str(value)
                    item_dict[key] = value
            return item_dict
        return v


class ItemPriceListResponse(BaseModel):
    """Schema for paginated item price list response"""

    item_prices: list[ItemPriceListItem] = Field(..., description="List of item prices")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    model_config = {"from_attributes": True}


class ItemPriceBulkCreate(BaseModel):
    """Schema for bulk creating item prices"""

    item_prices: list[ItemPriceCreate] = Field(
        ..., min_length=1, max_length=100, description="List of item prices to create"
    )


class ItemPriceBulkResponse(BaseModel):
    """Schema for bulk create response"""

    created_count: int = Field(..., description="Number of item prices created")
    item_prices: list[ItemPriceResponse] = Field(..., description="Created item prices")
    errors: list[dict] = Field(
        default_factory=list, description="Any errors encountered"
    )
