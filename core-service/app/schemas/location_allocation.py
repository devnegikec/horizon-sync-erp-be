"""Pydantic schemas for location allocation endpoints"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ===========================================
# REQUEST SCHEMAS
# ===========================================


class CreateAllocationRequest(BaseModel):
    """Schema for creating a location allocation"""

    location_id: UUID = Field(..., description="Location UUID (bin, level, or bay)")
    item_group_id: UUID = Field(..., description="Item group UUID to allocate")
    allocation_type: str = Field(
        default="preferred",
        description="Allocation type: 'exclusive' or 'preferred'",
    )
    priority: int = Field(
        default=0,
        description="Priority for put-away ordering (higher = more preferred)",
    )


class UpdateAllocationRequest(BaseModel):
    """Schema for updating a location allocation (all fields optional)"""

    allocation_type: Optional[str] = Field(
        None, description="New allocation type: 'exclusive' or 'preferred'"
    )
    priority: Optional[int] = Field(
        None, description="New priority for put-away ordering"
    )


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class LocationAllocationResponse(BaseModel):
    """Response schema for a location allocation record"""

    id: UUID
    organization_id: UUID
    location_id: UUID
    item_group_id: UUID
    priority: int = 0
    allocation_type: str = "preferred"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAllocations(BaseModel):
    """Paginated response for location allocations list"""

    allocations: list[LocationAllocationResponse]
    pagination: PaginationMeta
