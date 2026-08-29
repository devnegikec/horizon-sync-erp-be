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


class PickScanRequest(BaseModel):
    """Request schema for recording a pick scan against a pick list.

    Requirements: 10.1; WF-012 / ALT-001 / EX-003 (wrong-bin hard stop)
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


class PickListFilters(BaseModel):
    """Query parameters for filtering pick lists.

    Requirements: 11.3
    """

    status: str | None = Field(
        None,
        description="Filter by status: draft, in_progress, completed, cancelled",
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
    invoice_reference: str | None = None
    assigned_to: str | None = None
    worker_name: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
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
    progress: PickListProgress | None = None


class OutboundPickListListResponse(BaseModel):
    """Paginated list response for outbound pick lists.

    Requirements: 11.3
    """

    pick_lists: list[OutboundPickListListItem]
    pagination: PaginationMeta
