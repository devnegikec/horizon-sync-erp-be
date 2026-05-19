"""Pydantic schemas for bin stock endpoints"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ===========================================
# REQUEST SCHEMAS
# ===========================================


class AddStockRequest(BaseModel):
    """Schema for adding stock to a bin"""

    bin_id: UUID = Field(..., description="Bin location UUID")
    item_id: UUID = Field(..., description="Item UUID")
    quantity: Decimal = Field(..., gt=0, description="Quantity to add (must be positive)")
    batch_number: Optional[str] = Field(None, max_length=100, description="Optional batch number")


class RemoveStockRequest(BaseModel):
    """Schema for removing stock from a bin"""

    bin_id: UUID = Field(..., description="Bin location UUID")
    item_id: UUID = Field(..., description="Item UUID")
    quantity: Decimal = Field(..., gt=0, description="Quantity to remove (must be positive)")
    batch_number: Optional[str] = Field(None, max_length=100, description="Optional batch number")


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
    batch_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BinStockInfoResponse(BaseModel):
    """Response schema for bin stock info (includes bin details)"""

    bin_location_id: UUID
    bin_code: Optional[str] = None
    bin_name: Optional[str] = None
    warehouse_id: UUID
    item_id: UUID
    quantity_on_hand: Decimal = Decimal("0")
    batch_number: Optional[str] = None
    bin_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    is_active: bool = True
    created_at: datetime


class BinStockListResponse(BaseModel):
    """Response schema for listing bin stock levels"""

    bin_stock_levels: list[BinStockLevelResponse]


class BinStockForItemResponse(BaseModel):
    """Response schema for listing all bins containing a specific item"""

    bins: list[BinStockInfoResponse]
