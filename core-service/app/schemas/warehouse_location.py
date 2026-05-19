"""Pydantic schemas for warehouse location layout and capacity endpoints"""

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


class CreateLocationRequest(BaseModel):
    """Schema for creating a new warehouse location node"""

    warehouse_id: UUID
    parent_location_id: Optional[UUID] = None
    location_type: str = Field(
        ..., description="Location type: zone, aisle, bay, level, or bin"
    )
    code: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    capacity: Decimal = Field(default=Decimal("0"), ge=0)
    capacity_uom: Optional[str] = Field(None, max_length=50)
    position_x: Decimal = Field(default=Decimal("0"))
    position_y: Decimal = Field(default=Decimal("0"))


class UpdateLocationRequest(BaseModel):
    """Schema for updating an existing warehouse location node (all fields optional)"""

    name: Optional[str] = Field(None, max_length=255)
    capacity: Optional[Decimal] = Field(None, ge=0)
    capacity_uom: Optional[str] = Field(None, max_length=50)
    position_x: Optional[Decimal] = None
    position_y: Optional[Decimal] = None


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class LocationResponse(BaseModel):
    """Full response schema for a warehouse location"""

    id: UUID
    organization_id: UUID
    warehouse_id: UUID
    parent_location_id: Optional[UUID] = None
    location_type: str
    code: str
    full_path: Optional[str] = None
    name: Optional[str] = None
    capacity: Decimal = Decimal("0")
    total_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    capacity_uom: Optional[str] = None
    position_x: Decimal = Decimal("0")
    position_y: Decimal = Decimal("0")
    is_active: bool = True
    version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationTree(BaseModel):
    """Recursive tree structure for warehouse location hierarchy"""

    id: UUID
    warehouse_id: UUID
    parent_location_id: Optional[UUID] = None
    location_type: str
    code: str
    full_path: Optional[str] = None
    name: Optional[str] = None
    capacity: Decimal = Decimal("0")
    total_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    capacity_uom: Optional[str] = None
    position_x: Decimal = Decimal("0")
    position_y: Decimal = Decimal("0")
    is_active: bool = True
    children: list[LocationTree] = []

    model_config = ConfigDict(from_attributes=True)


# Rebuild model for recursive reference
LocationTree.model_rebuild()


class LocationSummary(BaseModel):
    """Summary statistics for a location subtree"""

    total_bins: int = 0
    occupied_bins: int = 0
    total_capacity: Decimal = Decimal("0")
    used_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    item_count: int = 0


class CapacitySummary(BaseModel):
    """Capacity summary for a specific location node"""

    location_id: UUID
    total_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    used_capacity: Decimal = Decimal("0")
    utilization_percentage: Decimal = Decimal("0")


# ===========================================
# FILTER AND PAGINATION SCHEMAS
# ===========================================


class LocationFilters(BaseModel):
    """Query filters for listing warehouse locations"""

    location_type: Optional[str] = None
    parent_location_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    has_stock: Optional[bool] = None
    search: Optional[str] = None


class PaginatedLocations(BaseModel):
    """Paginated response for warehouse locations list"""

    locations: list[LocationResponse]
    pagination: PaginationMeta
