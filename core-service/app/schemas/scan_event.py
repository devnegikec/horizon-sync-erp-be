"""Pydantic schemas for scan event audit trail endpoints.

Handles QR scan event recording and querying across all warehouse contexts
(inbound, pick, gate) for audit trail purposes.

Requirements: 14.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class ScanEventCreate(BaseModel):
    """Request schema for recording a scan event.

    Requirements: 14.1, 14.2, 14.4
    """

    worker_id: UUID = Field(..., description="UUID of the worker performing the scan")
    scan_context: str = Field(
        ...,
        description="Context of the scan: 'inbound', 'pick', or 'gate'",
        pattern="^(inbound|pick|gate)$",
    )
    serial_number: Optional[str] = Field(
        None,
        max_length=75,
        description="Serial number or QR identifier of the scanned item",
    )
    session_id: Optional[UUID] = Field(
        None, description="Optional session ID (inbound or gate session)"
    )
    pick_list_id: Optional[UUID] = Field(
        None, description="Optional pick list ID (for pick or gate context)"
    )
    decoded_payload: Optional[dict[str, Any]] = Field(
        None, description="Optional decoded QR payload data"
    )
    device_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Device type (e.g., 'mobile', 'tablet')",
    )
    os: Optional[str] = Field(
        None,
        max_length=50,
        description="Operating system info",
    )
    product_item_id: Optional[UUID] = Field(
        None, description="Optional product item ID reference"
    )
    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="IP address of the scanning device",
    )
    latitude: Optional[float] = Field(None, description="GPS latitude")
    longitude: Optional[float] = Field(None, description="GPS longitude")
    city: Optional[str] = Field(
        None,
        max_length=100,
        description="City from geo-resolution",
    )
    state: Optional[str] = Field(
        None,
        max_length=100,
        description="State from geo-resolution",
    )
    country: Optional[str] = Field(
        None,
        max_length=100,
        description="Country from geo-resolution",
    )


class ScanEventFilters(BaseModel):
    """Query parameters for filtering scan events.

    Requirements: 14.3
    """

    session_id: Optional[UUID] = Field(
        None, description="Filter by session ID (stored in extra_data)"
    )
    worker_id: Optional[UUID] = Field(
        None, description="Filter by worker ID (stored in extra_data)"
    )
    scan_context: Optional[str] = Field(
        None,
        description="Filter by scan context: 'inbound', 'pick', or 'gate'",
    )
    date_from: Optional[datetime] = Field(
        None, description="Start date filter (inclusive)"
    )
    date_to: Optional[datetime] = Field(None, description="End date filter (inclusive)")
    serial_number: Optional[str] = Field(None, description="Filter by serial number")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class ScanEventResponse(BaseModel):
    """Response schema for a single scan event.

    Requirements: 14.1, 14.2
    """

    id: str
    organization_id: str
    product_item_id: Optional[str] = None
    serial_number: Optional[str] = None
    scan_timestamp: Optional[str] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    ip_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    extra_data: Optional[dict[str, Any]] = None


class PaginatedScanEvents(BaseModel):
    """Paginated list response for scan events.

    Requirements: 14.3
    """

    scan_events: list[ScanEventResponse]
    pagination: PaginationMeta
