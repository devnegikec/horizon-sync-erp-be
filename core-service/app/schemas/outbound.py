"""Pydantic schemas for outbound pick list endpoints.

Handles the outbound workflow triggered by SAP invoices:
- Create pick list from SAP invoice
- List pick lists with filters
- Record pick scans
- Complete/cancel pick lists
- Track pick list progress

Requirements: 9.1, 10.1, 11.3, 11.4
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class SAPInvoiceItem(BaseModel):
    """A single line item from a SAP invoice payload."""

    item_id: UUID = Field(..., description="Item UUID from the items table")
    sku: str = Field(..., min_length=1, max_length=100, description="SKU / item code")
    quantity: Decimal = Field(..., gt=0, description="Quantity to pick")
    uom: str = Field(..., min_length=1, max_length=50, description="Unit of measure")
    per_case_qty: Decimal | None = Field(None, description="Items per case/box")
    case_qty: Decimal | None = Field(None, description="Cases/boxes to pick")
    loose_qty: Decimal | None = Field(None, description="Loose pieces to pick")
    batch_no: str | None = Field(None, max_length=100, description="Batch/serial number")


class SAPInvoicePayload(BaseModel):
    """Request schema for creating a pick list from a SAP sales invoice.

    Requirements: 9.1, 9.2
    """

    invoice_reference: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="SAP invoice reference number",
    )
    warehouse_id: UUID = Field(..., description="Target warehouse for the pick list")
    items: list[SAPInvoiceItem] = Field(
        ..., min_length=1, description="Invoice line items to pick"
    )
    assigned_to: UUID | None = Field(
        None, description="Optional worker UUID to assign the pick list to"
    )


class AssignWorkerRequest(BaseModel):
    """Request schema for assigning/reassigning a worker to a pick list."""

    worker_id: UUID = Field(..., description="Worker UUID to assign")


class CreatePickListFromOrderRequest(BaseModel):
    """Request schema for generating pick lists from a confirmed order.

    Mirrors the inbound put-away generation dialog: select one or more workers
    and the order lines are split into one pick list per worker. Leave
    ``worker_ids`` empty to create a single unassigned pick list.
    """

    worker_ids: list[UUID] = Field(
        default_factory=list, description="Workers to split the pick work across"
    )
    mode: str | None = Field(
        None,
        description=(
            "Generation mode: 'auto' assigns bin locations (FIFO/FEFO), "
            "'manual' leaves bin assignment to the worker. None defaults to "
            "the organization setting (auto unless overridden)."
        ),
    )
    exclude_out_of_stock: bool = Field(
        default=True,
        description=(
            "When true (default), order lines with no available stock are "
            "skipped so the generated pick lists only contain fulfillable "
            "items (partial order)."
        ),
    )


class StageTransferRequest(BaseModel):
    """Request schema for transferring a pick list to a staging lane (WF-019)."""

    staging_location_id: UUID = Field(..., description="Staging lane location UUID")


class StageScanRequest(BaseModel):
    """Request schema for scanning a staging lane (WF-020)."""

    staging_location_id: UUID = Field(..., description="Scanned staging lane UUID")


class AssignHandlingUnitRequest(BaseModel):
    """Request schema for associating a handling unit with a pick item (WF-018)."""

    handling_unit_id: UUID = Field(..., description="Handling unit UUID")


class UpdatePriorityRequest(BaseModel):
    """Request schema for setting task prioritization fields (WF-007)."""

    priority: int | None = Field(
        None, ge=0, description="Manual priority (higher = more urgent)"
    )
    dispatch_cutoff: datetime | None = Field(
        None, description="Dispatch cutoff time (SAP-supplied or manual)"
    )
    wave: str | None = Field(None, max_length=100, description="Wave sequence")
    route: str | None = Field(None, max_length=100, description="Route code")
    sla_minutes: int | None = Field(
        None, gt=0, description="Per-task SLA in minutes (overrides aging threshold)"
    )


class HandlingUnitAssignmentResponse(BaseModel):
    """Response schema for a handling-unit association."""

    pick_list_item_id: str
    handling_unit_id: str


class PickScanRequest(BaseModel):
    """Request schema for recording a pick scan against a pick list.

    Requirements: 10.1; WF-012 / ALT-001 / EX-003 (wrong-bin hard stop),
    EX-007 (damage/hold capture at scan)
    """

    qr_data: str = Field(
        ..., min_length=1, description="Raw QR code payload string (JSON)"
    )
    bin_location_id: UUID | None = Field(
        None,
        description=(
            "Scanned source bin location UUID. Required when "
            "``pick.require_bin_scan`` is enabled; validated against the "
            "item's assigned bin (wrong-bin hard stop)."
        ),
    )
    reason_code: str | None = Field(
        None,
        max_length=80,
        description=(
            "Optional exception reason code reported at scan (e.g. "
            "``damaged``). When set, a pick exception is recorded against the "
            "line (EX-007 / ALT-005)."
        ),
    )
    reason_quantity: Decimal | None = Field(
        None,
        ge=0,
        description="Affected quantity for the scan exception (defaults to scanned qty).",
    )


class PickListFilters(BaseModel):
    """Query parameters for filtering pick lists.

    Requirements: 11.3
    """

    status: str | None = Field(
        None,
        description=(
            "Filter by status: draft, confirmed, pending_picking, in_progress, "
            "pick_complete, ready_for_dispatch, in_transit, delivered, cancelled"
        ),
    )
    warehouse_id: UUID | None = Field(None, description="Filter by warehouse ID")
    invoice_reference: str | None = Field(
        None, description="Filter by SAP invoice reference"
    )
    sort_by: str = Field(
        default="created_at",
        description="Sort field: created_at, pick_list_no, status",
    )
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class PickListProgress(BaseModel):
    """Progress information for a pick list.

    Requirements: 11.4
    """

    total_items: int = Field(..., description="Total number of pick list items")
    picked_items: int = Field(..., description="Number of items fully picked")
    remaining_items: int = Field(
        ..., description="Number of items not yet fully picked"
    )
    total_qty: float = Field(..., description="Total quantity to pick")
    picked_qty: float = Field(..., description="Total quantity already picked")
    remaining_qty: float = Field(..., description="Total quantity remaining")
    completion_percentage: float = Field(
        ..., description="Percentage of completion (0-100)"
    )


class PickSerialDetail(BaseModel):
    """A single serial/unit being picked within a pick list line item."""

    serial_number: str
    sku: str | None = None
    manufacturing_date: str | None = None
    expiry_date: str | None = None


class PickListItemResponse(BaseModel):
    """Response schema for a pick list item."""

    id: str
    item_id: str
    item_name: str | None = None
    sku: str | None = None
    warehouse_id: str
    qty: float
    picked_qty: float
    uom: str
    per_case_qty: float | None = None
    case_qty: float | None = None
    loose_qty: float | None = None
    batch_no: str | None = None
    bin_location_id: str | None = None
    bin_location_path: str | None = None
    handling_unit_id: str | None = None
    sort_order: int = 0
    serials: list[PickSerialDetail] = []


class OutboundPickListResponse(BaseModel):
    """Response schema for a pick list in the outbound workflow.

    Requirements: 11.4
    """

    id: str
    organization_id: str
    pick_list_no: str
    warehouse_id: str
    status: str
    pick_date: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    invoice_reference: str | None = None
    assigned_to: str | None = None
    worker_name: str | None = None
    completed_at: str | None = None
    accepted_at: str | None = None
    accepted_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    priority: int = 0
    dispatch_cutoff: str | None = None
    wave: str | None = None
    route: str | None = None
    sla_minutes: int | None = None
    age_minutes: int = 0
    is_aging: bool = False
    items: list[PickListItemResponse] = []
    progress: PickListProgress | None = None


class PickScanResult(BaseModel):
    """Response schema for a recorded pick scan.

    Requirements: 10.1, 10.3
    """

    pick_list_id: str
    pick_list_status: str
    pick_list_item_id: str
    item_id: str
    sku: str
    serial_no: str | None = None
    scanned_qty: int
    picked_qty: float
    required_qty: float
    remaining_qty: float
    batch: str | None = None


class OutboundPickListListItem(BaseModel):
    """List item response for pick lists in the outbound workflow."""

    id: str
    organization_id: str
    pick_list_no: str
    warehouse_id: str
    status: str
    invoice_reference: str | None = None
    assigned_to: str | None = None
    worker_name: str | None = None
    pick_date: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    priority: int = 0
    dispatch_cutoff: str | None = None
    wave: str | None = None
    route: str | None = None
    age_minutes: int = 0
    is_aging: bool = False
    progress: PickListProgress | None = None


class OutboundPickListStatusCounts(BaseModel):
    """Status distribution for outbound pick lists."""

    total: int = 0
    draft: int = 0
    confirmed: int = 0
    pending_picking: int = 0
    in_progress: int = 0
    pick_complete: int = 0
    completed: int = 0
    ready_for_dispatch: int = 0
    in_transit: int = 0
    delivered: int = 0
    cancelled: int = 0


class OutboundPickListListResponse(BaseModel):
    """Paginated list response for outbound pick lists.

    Requirements: 11.3
    """

    pick_lists: list[OutboundPickListListItem]
    pagination: PaginationMeta
    status_counts: OutboundPickListStatusCounts | None = None


# ===========================================
# OUTBOUND ORDER SCHEMAS
# ===========================================


class OutboundOrderItemResponse(BaseModel):
    """Response schema for an outbound order line item."""

    id: str
    item_id: str
    item_name: str | None = None
    sku: str | None = None
    qty: float
    uom: str
    per_case_qty: float | None = None
    case_qty: float | None = None
    loose_qty: float | None = None
    batch_no: str | None = None
    stock_status: str
    available_qty: float | None = None


class OutboundOrderResponse(BaseModel):
    """Response schema for an outbound order."""

    id: str
    organization_id: str
    order_no: str
    order_type: str
    warehouse_id: str
    status: str
    invoice_reference: str | None = None
    source_filename: str | None = None
    remarks: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    reference_no: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    pick_list_ids: list[str] = []
    items: list[OutboundOrderItemResponse] = []


class OutboundOrderStatusCounts(BaseModel):
    """Status distribution for outbound orders."""

    total: int = 0
    draft: int = 0
    confirmed: int = 0
    pending_picking: int = 0
    completed: int = 0
    cancelled: int = 0


class OutboundOrderListItem(BaseModel):
    """Lightweight list item for an outbound order (no line items).

    Line-item detail is served on demand by ``GET /outbound/orders/{order_id}``.
    """

    id: str
    organization_id: str
    order_no: str
    order_type: str
    warehouse_id: str
    status: str
    invoice_reference: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    item_count: int = 0
    in_stock_count: int = 0
    out_of_stock_count: int = 0


class OutboundOrderListResponse(BaseModel):
    """Paginated list response for outbound orders."""

    orders: list[OutboundOrderListItem]
    pagination: PaginationMeta
    status_counts: OutboundOrderStatusCounts | None = None
