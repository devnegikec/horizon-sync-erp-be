"""Pydantic schemas for packing slip endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class CreatePackingSlipRequest(BaseModel):
    """Request schema for creating a packing slip from completed orders."""

    order_ids: list[UUID] = Field(
        ..., min_length=1, description="Completed order UUIDs to pack"
    )


class PackPickListsRequest(BaseModel):
    """Request schema for packing completed pick list(s) into a packing slip."""

    pick_list_ids: list[UUID] = Field(
        ..., min_length=1, description="Completed pick list UUIDs to pack"
    )
    packing_slip_id: UUID | None = Field(
        None,
        description="Optional draft packing slip to append to (creates a new one when omitted)",
    )


class PackingSlipItemResponse(BaseModel):
    """Response schema for a packing slip line item."""

    id: str
    order_id: str | None = None
    pick_list_id: str | None = None
    item_id: str
    item_name: str | None = None
    sku: str | None = None
    qty: float
    uom: str
    per_case_qty: float | None = None
    case_qty: float | None = None
    loose_qty: float | None = None
    batch_no: str | None = None
    bin_location_id: str | None = None
    handling_unit_id: str | None = None
    sort_order: int = 0


class PackingSlipResponse(BaseModel):
    """Response schema for a packing slip."""

    id: str
    organization_id: str
    packing_slip_no: str
    warehouse_id: str
    status: str
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    order_ids: list[str] = []
    items: list[PackingSlipItemResponse] = []


class PackingSlipListItem(BaseModel):
    """List item response for a packing slip."""

    id: str
    packing_slip_no: str
    warehouse_id: str
    status: str
    item_count: int = 0
    order_ids: list[str] = []
    created_at: str | None = None


class PackingSlipStatusCounts(BaseModel):
    """Status distribution for packing slips."""

    total: int = 0
    draft: int = 0
    loading: int = 0
    dispatched: int = 0
    cancelled: int = 0


class PackingSlipListResponse(BaseModel):
    """Paginated list response for packing slips."""

    packing_slips: list[PackingSlipListItem]
    pagination: PaginationMeta
    status_counts: PackingSlipStatusCounts | None = None
