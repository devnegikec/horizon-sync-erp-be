"""Pydantic schemas for ProductSKU, VariantAttribute, VariantAttributeValue"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Variant Attribute ─────────────────────────────────────────────────────────

class VariantAttributeCreateRequest(BaseModel):
    name: str = Field(..., max_length=50, examples=["Capacity", "Size", "Color"])
    unit: str | None = Field(None, max_length=20, examples=["Litre", "mm"])


class VariantAttributeUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=50)
    unit: str | None = Field(None, max_length=20)


class VariantAttributeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    unit: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class VariantAttributeListResponse(BaseModel):
    attributes: list[VariantAttributeResponse]
    pagination: dict[str, Any]


# ── Variant Attribute Value ───────────────────────────────────────────────────

class VariantAttributeValueCreateRequest(BaseModel):
    value: str = Field(..., max_length=50, examples=["1", "Small", "White"])
    display_value: str | None = Field(None, max_length=50, examples=["1 Litre", "Small", "White"])
    sort_order: int = Field(default=0)


class VariantAttributeValueUpdateRequest(BaseModel):
    value: str | None = Field(None, max_length=50)
    display_value: str | None = Field(None, max_length=50)
    sort_order: int | None = None


class VariantAttributeValueResponse(BaseModel):
    id: UUID
    attribute_id: UUID
    value: str
    display_value: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}


class VariantAttributeWithValuesResponse(VariantAttributeResponse):
    """Attribute with its values nested — used in SKU detail responses."""
    values: list[VariantAttributeValueResponse] = []


# ── ProductSKU ────────────────────────────────────────────────────────────────

class SKUAttributeValueInput(BaseModel):
    """Used when creating/updating a SKU — specify which attribute value to link."""
    attribute_value_id: UUID


class ProductSKUCreateRequest(BaseModel):
    product_id: UUID
    sku_code: str = Field(..., max_length=100, examples=["PRESSCOOK-1L", "PANTS-RED-L"])
    name: str | None = Field(None, max_length=100, examples=["1 Litre", "Large Red"])
    gtin: str | None = Field(None, max_length=20)
    mrp: float = Field(...)
    sr_number_type: str | None = Field(None, max_length=50)
    image_url: str | None = None
    warranty_period_months: int | None = None
    # Which attribute values define this variant
    # e.g. [{"attribute_value_id": "<1L-value-uuid>"}]
    # Fan SKU with 2 attributes: two entries here
    attribute_values: list[SKUAttributeValueInput] = Field(default=[])


class ProductSKUUpdateRequest(BaseModel):
    sku_code: str | None = Field(None, max_length=100)
    name: str | None = Field(None, max_length=100)
    gtin: str | None = Field(None, max_length=20)
    mrp: Decimal | None = None
    sr_number_type: str | None = None
    image_url: str | None = None
    warranty_period_months: int | None = None
    is_active: bool | None = None
    attribute_values: list[SKUAttributeValueInput] | None = None


class SKUAttributeValueResponse(BaseModel):
    id: UUID
    attribute_value_id: UUID
    attribute_name: str   # from attribute_value.attribute.name
    value: str            # from attribute_value.value
    display_value: str    # from attribute_value.display_value or value

    model_config = {"from_attributes": True}


class ProductSKUResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    sku_code: str
    name: str | None = None
    gtin: str | None = None
    mrp: Decimal | None = None
    sr_number_type: str | None = None
    image_url: str | None = None
    warranty_period_months: int | None = None
    is_active: bool
    attribute_values: list[SKUAttributeValueResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductSKUListResponse(BaseModel):
    skus: list[ProductSKUResponse]
    pagination: dict[str, Any]