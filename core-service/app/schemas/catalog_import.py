"""Catalog import (product/item) Pydantic schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CatalogImportRow(BaseModel):
    """A single row of catalog import data."""

    name: str | None = Field(None, max_length=255)
    sku: str | None = Field(None, max_length=100)
    gtin: str | None = Field(None, max_length=20)
    description: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    uom: str | None = Field(None, max_length=50)
    item_code: str | None = Field(None, max_length=100)
    item_group_id: UUID | None = None
    has_batch_no: bool = False
    has_serial_no: bool = False
    variant_of: UUID | None = None
    variant_attributes: dict | None = None
    item_id: UUID | None = None
    action: Literal["create", "modify", "delete"] | None = None


class CatalogImportRequest(BaseModel):
    """Bulk catalog import request."""

    mode: Literal["product_only", "product_with_items", "item_with_auto_product"]
    rows: list[CatalogImportRow] = Field(..., min_length=1, max_length=10000)


class CatalogImportError(BaseModel):
    row: int
    error: str


class CatalogImportResponse(BaseModel):
    created: int
    updated: int
    deleted: int = 0
    errors: list[CatalogImportError]
