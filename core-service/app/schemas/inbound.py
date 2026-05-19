"""Pydantic schemas for inbound scan session and receiving slip endpoints.

Requirements: 5.1, 5.6, 6.1, 7.2
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ===========================================
# REQUEST SCHEMAS
# ===========================================


class StartSessionRequest(BaseModel):
    """Schema for starting a new inbound scan session."""

    warehouse_id: UUID = Field(..., description="Warehouse UUID where receiving occurs")
    dock_location: Optional[str] = Field(
        None, max_length=255, description="Optional dock location identifier"
    )


class RecordScanRequest(BaseModel):
    """Schema for recording a QR scan within a session."""

    qr_data: str = Field(..., min_length=1, description="Raw QR code payload string (JSON)")
    device_type: Optional[str] = Field(
        None, max_length=50, description="Device type (e.g., 'mobile', 'tablet')"
    )
    os: Optional[str] = Field(
        None, max_length=50, description="Operating system info"
    )


class RejectSlipRequest(BaseModel):
    """Schema for rejecting a receiving slip with a reason."""

    reason: str = Field(
        ..., min_length=1, max_length=1000, description="Reason for rejection"
    )


class FlagLineItemRequest(BaseModel):
    """Schema for flagging a receiving slip line item."""

    flag: str = Field(
        ..., description="Flag value: 'short' or 'damaged'"
    )
    notes: Optional[str] = Field(
        None, max_length=1000, description="Optional notes about the discrepancy"
    )


class ApproveSlipRequest(BaseModel):
    """Schema for approving a receiving slip with optional worker assignment."""

    worker_id: Optional[UUID] = Field(
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
    dock_location: Optional[str] = None
    status: str
    total_boxes_scanned: int = 0
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    created_at: Optional[str] = None


class ScanResult(BaseModel):
    """Response schema for a recorded scan."""

    scan_item_id: str
    session_id: str
    qr_identifier: str
    sku: str
    quantity: int
    batch_number: str
    scanned_at: Optional[str] = None
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
    dock_location: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    total_boxes: int
    total_quantity: int
    items: list[SKUBreakdown]


class ReceivingSlipItemResponse(BaseModel):
    """Response schema for a receiving slip line item."""

    id: str
    sku: str
    batch_number: Optional[str] = None
    quantity: int
    box_count: int
    flag: str
    notes: Optional[str] = None


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
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    items: list[ReceivingSlipItemResponse]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FlaggedItemResponse(BaseModel):
    """Response schema for a flagged receiving slip line item."""

    id: str
    slip_id: str
    sku: str
    batch_number: Optional[str] = None
    quantity: int
    box_count: int
    flag: str
    notes: Optional[str] = None
