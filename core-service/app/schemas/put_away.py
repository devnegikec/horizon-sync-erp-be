"""Pydantic schemas for put-away list endpoints.

Handles:
- Generating put-away lists from receiving slips
- Listing put-away lists with filters
- Getting put-away list detail with items
- Completing a put-away item
- Skipping a put-away item with reason

Requirements: 8.1, 8.5, 8.6
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class GeneratePutAwayRequest(BaseModel):
    """Schema for generating a put-away list from a receiving slip."""

    worker_id: UUID | None = Field(
        None, description="Optional worker UUID to assign the put-away task to"
    )


class CompletePutAwayItemRequest(BaseModel):
    """Schema for completing a put-away item.

    Optionally override the bin location where stock should be placed.
    When not provided, the pre-assigned bin_location_id from the put-away
    item is used.
    """

    bin_id: UUID | None = Field(
        None, description="Optional override bin location ID for put-away"
    )


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
    sku: str | None = None
    batch_number: str | None = None
    quantity: float
    bin_location_id: str | None = None
    bin_location_code: str | None = None
    sort_order: int = 0
    status: str
    notes: str | None = None
    completed_at: str | None = None
    created_at: str | None = None


class PutAwayListResponse(BaseModel):
    """Response schema for a put-away list."""

    id: str
    organization_id: str
    warehouse_id: str
    put_away_list_no: str
    status: str
    reference_type: str | None = None
    reference_id: str | None = None
    receiving_slip_id: str | None = None
    remarks: str | None = None
    warnings: list[str] | None = None
    assigned_to: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    items: list[PutAwayListItemResponse] = []


class PutAwayListSummaryResponse(BaseModel):
    """Summary response for put-away list in list view (without items)."""

    id: str
    organization_id: str
    warehouse_id: str
    put_away_list_no: str
    status: str
    reference_type: str | None = None
    reference_id: str | None = None
    receiving_slip_id: str | None = None
    remarks: str | None = None
    assigned_to: str | None = None
    total_items: int = 0
    completed_items: int = 0
    pending_items: int = 0
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PutAwayListListResponse(BaseModel):
    """Paginated list of put-away lists."""

    put_away_lists: list[PutAwayListSummaryResponse]
    pagination: PaginationMeta
