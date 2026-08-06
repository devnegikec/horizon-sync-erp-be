"""Pydantic schemas for inbound scan session and receiving slip endpoints.

Requirements: 5.1, 5.6, 6.1, 7.2
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class StartSessionRequest(BaseModel):
    """Schema for starting a new inbound scan session."""

    warehouse_id: UUID = Field(..., description="Warehouse UUID where receiving occurs")
    dock_location: str | None = Field(
        None, max_length=255, description="Optional dock location identifier"
    )


class RecordScanRequest(BaseModel):
    """Schema for recording a QR scan within a session."""

    qr_data: str = Field(
        ..., min_length=1, description="Raw QR code payload string (JSON)"
    )
    device_type: str | None = Field(
        None, max_length=50, description="Device type (e.g., 'mobile', 'tablet')"
    )
    os: str | None = Field(None, max_length=50, description="Operating system info")


class RejectSlipRequest(BaseModel):
    """Schema for rejecting a receiving slip with a reason."""

    reason: str = Field(
        ..., min_length=1, max_length=1000, description="Reason for rejection"
    )


class FlagLineItemRequest(BaseModel):
    """Schema for flagging a receiving slip line item."""

    flag: str = Field(..., description="Flag value: 'short' or 'damaged'")
    notes: str | None = Field(
        None, max_length=1000, description="Optional notes about the discrepancy"
    )


class ApproveSlipRequest(BaseModel):
    """Schema for approving a receiving slip with optional worker assignment."""

    worker_id: UUID | None = Field(
        None, description="Optional worker UUID to assign the put-away task to"
    )


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class SessionResponse(BaseModel):
    """Response schema for a scan session."""

    id: str
    organization_id: str
    session_type: str
    worker_id: str
    warehouse_id: str
    dock_location: str | None = None
    status: str
    total_boxes_scanned: int = 0
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str | None = None


class ScanResult(BaseModel):
    """Response schema for a recorded scan."""

    scan_item_id: str
    session_id: str
    qr_identifier: str
    sku: str
    raw_quantity: int
    batch_number: str
    packaging_unit_id: UUID | None = None
    scanned_at: str | None = None
    total_boxes_scanned: int = 0


class BatchBreakdown(BaseModel):
    """Batch breakdown within a SKU summary."""

    batch_number: str
    quantity: int
    box_count: int


class SKUBreakdown(BaseModel):
    """Per-SKU breakdown in session summary."""

    sku: str
    total_quantity: int
    total_boxes: int
    batches: list[BatchBreakdown]


class SessionSummary(BaseModel):
    """Response schema for session summary with per-SKU/batch aggregation."""

    session_id: str
    status: str
    session_type: str
    warehouse_id: str
    worker_id: str
    dock_location: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    total_boxes: int
    total_quantity: int
    items: list[SKUBreakdown]


class QSealParentInfo(BaseModel):
    """QSeal parent info attached to a receiving slip item."""

    id: str
    serial_number: str | None = None
    name: str | None = None
    qseal_type: str | None = None
    capacity: int | None = None


class ReceivingSlipItemData(BaseModel):
    """Individual line item inside a QSeal group — merged child detail + slip item."""

    id: str
    serial_number: str | None = None
    sku: str
    batch_number: str | None = None
    manufacturing_date: str | None = None
    expiry_date: str | None = None
    quantity: int
    box_count: int
    flag: str
    notes: str | None = None


class ReceivingSlipItemGroup(BaseModel):
    """A group of receiving slip items under the same QSeal parent."""

    parent_qseal: QSealParentInfo | None = None
    product_name: str | None = None
    items: list[ReceivingSlipItemData] = []


class ReceivingSlipResponse(BaseModel):
    """Response schema for a receiving slip."""

    id: str
    organization_id: str
    slip_number: str
    session_id: str
    warehouse_id: str
    status: str
    total_boxes: int
    total_items: int
    rejection_reason: str | None = None
    notes: str | None = None
    groups: list[ReceivingSlipItemGroup] = []
    created_at: str | None = None
    updated_at: str | None = None


class FlaggedItemResponse(BaseModel):
    """Response schema for a flagged receiving slip line item."""

    id: str
    slip_id: str
    sku: str
    batch_number: str | None = None
    quantity: int
    box_count: int
    flag: str
    notes: str | None = None


class ReceivingSlipPagination(BaseModel):
    """Pagination metadata for receiving slip list."""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ReceivingSlipListResponse(BaseModel):
    """Paginated list of receiving slips."""

    receiving_slips: list[ReceivingSlipResponse]
    pagination: ReceivingSlipPagination


# ------------------------------------------------------------------
# Two-Step Inbound: Assign Bin
# ------------------------------------------------------------------


class AssignBinRequest(BaseModel):
    """Request to assign a bin to a receiving slip item (put-away step)."""

    bin_location_id: UUID = Field(..., description="Bin location UUID from scanned QR")
    quantity: int | None = Field(
        None,
        gt=0,
        description="Quantity to put in bin (defaults to full slip item quantity)",
    )


class AssignBinResponse(BaseModel):
    """Response after assigning a bin to a slip item."""

    slip_item_id: str
    sku: str
    batch_number: str | None = None
    quantity: int
    bin_location_id: str
    bin_full_path: str | None = None
    put_away_status: str
    put_away_at: str | None = None
