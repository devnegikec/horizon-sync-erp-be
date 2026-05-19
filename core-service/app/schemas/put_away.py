"""Pydantic schemas for put-away list endpoints.

Handles:
- Listing put-away lists with filters
- Getting put-away list detail with items
- Completing a put-away item
- Skipping a put-away item with reason

Requirements: 8.5, 8.6
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class CompletePutAwayItemRequest(BaseModel):
    """Schema for completing a put-away item (no body needed, worker from auth)."""

    pass


class SkipPutAwayItemRequest(BaseModel):
    """Schema for skipping a put-away item with a reason."""

    reason: str = Field(
        ..., min_length=1, max_length=1000, description="Reason for skipping the item"
    )


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class PutAwayListItemResponse(BaseModel):
    """Response schema for a put-away list item."""

    id: str
    item_id: str
    sku: Optional[str] = None
    batch_number: Optional[str] = None
    quantity: float
    bin_location_id: Optional[str] = None
    bin_location_code: Optional[str] = None
    sort_order: int = 0
    status: str
    notes: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None


class PutAwayListResponse(BaseModel):
    """Response schema for a put-away list."""

    id: str
    organization_id: str
    warehouse_id: str
    put_away_list_no: str
    status: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    receiving_slip_id: Optional[str] = None
    remarks: Optional[str] = None
    assigned_to: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    items: list[PutAwayListItemResponse] = []


class PutAwayListSummaryResponse(BaseModel):
    """Summary response for put-away list in list view (without items)."""

    id: str
    organization_id: str
    warehouse_id: str
    put_away_list_no: str
    status: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    receiving_slip_id: Optional[str] = None
    remarks: Optional[str] = None
    assigned_to: Optional[str] = None
    total_items: int = 0
    completed_items: int = 0
    pending_items: int = 0
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PutAwayListListResponse(BaseModel):
    """Paginated list of put-away lists."""

    put_away_lists: list[PutAwayListSummaryResponse]
    pagination: PaginationMeta
