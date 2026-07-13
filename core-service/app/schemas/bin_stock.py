"""Pydantic schemas for bin stock endpoints"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class AddStockRequest(BaseModel):
    """Schema for adding stock to a bin"""

    bin_id: UUID = Field(..., description="Bin location UUID")
    item_id: UUID = Field(..., description="Item UUID")
    quantity: Decimal = Field(
        ..., gt=0, description="Quantity to add (must be positive)"
    )
    batch_number: str | None = Field(
        None, max_length=100, description="Optional batch number"
    )


class RemoveStockRequest(BaseModel):
    """Schema for removing stock from a bin"""

    bin_id: UUID = Field(..., description="Bin location UUID")
    item_id: UUID = Field(..., description="Item UUID")
    quantity: Decimal = Field(
        ..., gt=0, description="Quantity to remove (must be positive)"
    )
    batch_number: str | None = Field(
        None, max_length=100, description="Optional batch number"
    )


class BulkAddStockItem(BaseModel):
    """A single item entry within a bulk add request"""

    item_id: UUID = Field(..., description="Item UUID to add to the bin")
    quantity: Decimal = Field(
        ..., gt=0, description="Quantity to add (must be positive)"
    )
    batch_number: str | None = Field(
        None, max_length=100, description="Optional batch number"
    )


class BulkAddStockRequest(BaseModel):
    """Schema for adding multiple items to a single bin in one API call"""

    bin_id: UUID = Field(
        ..., description="Bin location UUID (all items go to this bin)"
    )
    items: list[BulkAddStockItem] = Field(
        ..., min_length=1, max_length=50, description="List of items to add to the bin"
    )


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class BinStockLevelResponse(BaseModel):
    """Response schema for a bin stock level record"""

    id: UUID
    organization_id: UUID
    bin_location_id: UUID
    item_id: UUID
    quantity_on_hand: Decimal = Decimal("0")
    batch_number: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BinStockInfoResponse(BaseModel):
    """Response schema for bin stock info (includes bin details)"""

    bin_location_id: UUID
    bin_code: str | None = None
    bin_name: str | None = None
    warehouse_id: UUID
    item_id: UUID
    quantity_on_hand: Decimal = Decimal("0")
    batch_number: str | None = None
    bin_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    is_active: bool = True
    created_at: datetime


class BinStockListResponse(BaseModel):
    """Response schema for listing bin stock levels"""

    bin_stock_levels: list[BinStockLevelResponse]


class BulkAddStockItemResult(BaseModel):
    """Result for a single item in a bulk add operation"""

    item_id: UUID
    quantity: Decimal
    batch_number: str | None = None
    status: str  # "added" or "error"
    error: str | None = None
    bin_stock_level: BinStockLevelResponse | None = None


class BulkAddStockResponse(BaseModel):
    """Response schema for bulk add stock operation"""

    bin_id: UUID
    added: int
    errors: int
    items: list[BulkAddStockItemResult]


class BinStockForItemResponse(BaseModel):
    """Response schema for listing all bins containing a specific item"""

    bins: list[BinStockInfoResponse]


class CopyStockRequest(BaseModel):
    """Schema for copying stock from one bin to another"""

    source_bin_id: UUID = Field(..., description="Source bin location UUID")
    target_bin_id: UUID = Field(..., description="Target bin location UUID")
    item_id: UUID = Field(..., description="Item UUID")
    quantity: Decimal = Field(..., gt=0, description="Quantity to copy")
    batch_number: str | None = Field(
        None, max_length=100, description="Optional batch number"
    )


class StockImportRow(BaseModel):
    """Schema for a single stock import row"""

    bin_code: str = Field(..., description="Target bin code")
    sku: str = Field(..., description="Item SKU or code")
    quantity: Decimal = Field(..., gt=0, description="Quantity")
    batch_number: str | None = Field(None, max_length=100)


class StockImportRequest(BaseModel):
    """Schema for importing stock levels"""

    warehouse_id: UUID = Field(..., description="Warehouse UUID")
    rows: list[StockImportRow] = Field(..., min_length=1)
    overwrite_existing: bool = Field(
        default=False, description="Overwrite existing stock for same bin+item+batch"
    )


class StockImportResult(BaseModel):
    """Result of a stock import operation"""

    imported: int
    updated: int
    errors: list[str]


class StockExportFilters(BaseModel):
    """Filters for stock export"""

    warehouse_id: UUID | None = None
    item_id: UUID | None = None
    bin_id: UUID | None = None
