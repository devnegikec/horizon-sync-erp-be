"""Pydantic schemas for warehouse location layout and capacity endpoints"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class CreateLocationRequest(BaseModel):
    """Schema for creating a new warehouse location node"""

    warehouse_id: UUID
    parent_location_id: UUID | None = None
    location_type: str = Field(
        ..., description="Location type: zone, aisle, bay, level, or bin"
    )
    code: str = Field(..., min_length=1, max_length=50)
    name: str | None = Field(None, max_length=255)
    capacity: Decimal = Field(default=Decimal("0"), ge=0)
    capacity_uom: str | None = Field(None, max_length=50)
    position_x: Decimal = Field(default=Decimal("0"))
    position_y: Decimal = Field(default=Decimal("0"))


class UpdateLocationRequest(BaseModel):
    """Schema for updating an existing warehouse location node (all fields optional)"""

    name: str | None = Field(None, max_length=255)
    capacity: Decimal | None = Field(None, ge=0)
    capacity_uom: str | None = Field(None, max_length=50)
    position_x: Decimal | None = None
    position_y: Decimal | None = None


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class LocationResponse(BaseModel):
    """Full response schema for a warehouse location"""

    id: UUID
    organization_id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None = None
    location_type: str
    code: str
    full_path: str | None = None
    name: str | None = None
    capacity: Decimal = Decimal("0")
    total_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    capacity_uom: str | None = None
    position_x: Decimal = Decimal("0")
    position_y: Decimal = Decimal("0")
    is_active: bool = True
    version: int = 1
    qr_code: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationTree(BaseModel):
    """Recursive tree structure for warehouse location hierarchy"""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None = None
    location_type: str
    code: str
    full_path: str | None = None
    name: str | None = None
    capacity: Decimal = Decimal("0")
    total_capacity: Decimal = Decimal("0")
    available_capacity: Decimal = Decimal("0")
    capacity_uom: str | None = None
    position_x: Decimal = Decimal("0")
    position_y: Decimal = Decimal("0")
    is_active: bool = True
    qr_code: str | None = None
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

    location_type: str | None = None
    parent_location_id: UUID | None = None
    is_active: bool | None = None
    has_stock: bool | None = None
    search: str | None = None


class PaginatedLocations(BaseModel):
    """Paginated response for warehouse locations list"""

    locations: list[LocationResponse]
    pagination: PaginationMeta


# ===========================================
# QR CODE SCHEMAS
# ===========================================


class LocationQRPayload(BaseModel):
    """QR code payload for a bin location.

    Encoded as JSON in the QR image. Mobile app scans this to identify
    the exact bin during inbound/outbound operations.
    """

    type: str = "location"
    org_id: UUID
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    location_id: UUID
    full_path: str
    location_type: str
    location_code: str
    qr_code: str | None = None  # 5-char short code for quick lookup
    bin_code: str | None = None  # Alias for qr_code for mobile app compatibility
