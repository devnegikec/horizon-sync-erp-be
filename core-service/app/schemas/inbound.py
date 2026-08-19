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


class EndSessionRejection(BaseModel):
    """A single item rejection submitted when ending a scan session."""

    serial_number: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Serial number (QR identifier) of the rejected unit",
    )
    reason: str | None = Field(
        None, max_length=1000, description="Reason for rejection"
    )


class EndSessionRequest(BaseModel):
    """Optional request body for ending a scan session.

    Rejections are applied before the receiving slip is finalized, so rejected
    items never enter stock or put-away.
    """

    rejections: list[EndSessionRejection] = Field(
        default_factory=list,
        description="Items to mark as rejected on the receiving slip",
    )


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
    asn_order_id: str | None = None
    asn_order_no: str | None = None
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


# ------------------------------------------------------------------
# ASN Linking
# ------------------------------------------------------------------


class LinkAsnToSessionRequest(BaseModel):
    """Link a scan session to an ASN order."""

    asn_order_id: UUID = Field(..., description="ASN order UUID to link")


class StartSessionWithAsnRequest(StartSessionRequest):
    """Start a new inbound scan session optionally linked to an ASN."""

    asn_order_id: UUID | None = Field(
        None, description="Optional ASN order UUID to link the session to"
    )


# ------------------------------------------------------------------
# Item Rejection
# ------------------------------------------------------------------


class RejectSlipItemRequest(BaseModel):
    """Request to reject a specific receiving slip line item."""

    reason: str = Field(
        ..., min_length=1, max_length=1000, description="Reason for rejecting this item"
    )
    notes: str | None = Field(
        None, max_length=1000, description="Optional additional notes"
    )


class ItemStatusUpdateRequest(BaseModel):
    """Per-item status update in a bulk request."""

    item_id: UUID
    status: str = Field(
        ..., description="New status: 'rejected', 'ok', 'short', or 'damaged'"
    )
    reason: str | None = Field(
        None, max_length=1000, description="Reason (used when status is 'rejected')"
    )
    notes: str | None = Field(
        None, max_length=1000, description="Optional additional notes"
    )


class BulkItemStatusUpdateRequest(BaseModel):
    """Bulk update of receiving-slip line item statuses in a single request."""

    items: list[ItemStatusUpdateRequest] = Field(..., min_length=1)


class RejectedItemResponse(BaseModel):
    """Response for a rejected receiving slip line item."""

    id: str
    slip_id: str
    sku: str
    batch_number: str | None = None
    quantity: int
    box_count: int
    flag: str
    rejection_reason: str | None = None
    notes: str | None = None
    rejected_at: str | None = None


class FloatingItemSummary(BaseModel):
    """Summary of a floating (rejected) receiving slip item."""

    slip_item_id: str
    slip_id: str
    slip_number: str
    sku: str
    batch_number: str | None = None
    quantity: int
    rejection_reason: str | None = None
    rejected_at: str | None = None
    warehouse_id: str
    asn_order_no: str | None = None


class FloatingItemsListResponse(BaseModel):
    """Paginated list of floating items across all slips."""

    floating_items: list[FloatingItemSummary]
    total: int
    page: int
    page_size: int


class ResolveFloatingItemRequest(BaseModel):
    """Request to resolve a floating (rejected) item."""

    action: str = Field(
        ..., description="Resolution action: accept, return_to_sender, dispose"
    )
    notes: str | None = Field(
        None, max_length=1000, description="Optional notes about the resolution"
    )


# ------------------------------------------------------------------
# ASN Receiving Summary (Mismatch View)
# ------------------------------------------------------------------


class AsnLineItemReceivingSummary(BaseModel):
    """Per-line-item comparison of ASN expected vs actually received."""

    asn_item_id: str
    item_id: str
    sku: str | None = None
    item_name: str | None = None
    expected_qty: int
    accepted_qty: int
    rejected_qty: int
    pending_qty: int
    over_qty: int
    status: str  # matched, partial, over, not_received


class LinkedReceivingSlipSummary(BaseModel):
    """Summary of a receiving slip linked to an ASN."""

    slip_id: str
    slip_number: str
    status: str
    created_at: str | None = None
    total_accepted_qty: int
    total_rejected_qty: int
    total_items: int


class AsnReceivingSummaryResponse(BaseModel):
    """Full ASN receiving summary with mismatch details."""

    asn_order_id: str
    asn_order_no: str
    asn_status: str
    expected_total_qty: int
    accepted_total_qty: int
    rejected_total_qty: int
    pending_total_qty: int
    over_total_qty: int
    total_line_items: int
    matched_items: int
    partial_items: int
    not_received_items: int
    over_items: int
    linked_slips: list[LinkedReceivingSlipSummary]
    line_items: list[AsnLineItemReceivingSummary]


# ------------------------------------------------------------------
# Extended Session / Slip Responses with ASN info
# ------------------------------------------------------------------


class SessionResponseWithAsn(SessionResponse):
    """Session response including optional ASN link."""

    asn_order_id: str | None = None
    asn_order_no: str | None = None


class ReceivingSlipResponseWithAsn(ReceivingSlipResponse):
    """Receiving slip response including optional ASN link."""

    asn_order_id: str | None = None
    asn_order_no: str | None = None
