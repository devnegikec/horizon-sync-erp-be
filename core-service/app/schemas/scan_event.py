"""Pydantic schemas for scan event audit trail endpoints.

Handles QR scan event recording and querying across all warehouse contexts
(inbound, pick, gate) for audit trail purposes.

Requirements: 14.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
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
    serial_number: str | None = Field(
        None,
        max_length=75,
        description="Serial number or QR identifier of the scanned item",
    )
    session_id: UUID | None = Field(
        None, description="Optional session ID (inbound or gate session)"
    )
    pick_list_id: UUID | None = Field(
        None, description="Optional pick list ID (for pick or gate context)"
    )
    decoded_payload: dict[str, Any] | None = Field(
        None, description="Optional decoded QR payload data"
    )
    device_type: str | None = Field(
        None,
        max_length=50,
        description="Device type (e.g., 'mobile', 'tablet')",
    )
    os: str | None = Field(
        None,
        max_length=50,
        description="Operating system info",
    )
    product_item_id: UUID | None = Field(
        None, description="Optional product item ID reference"
    )
    ip_address: str | None = Field(
        None,
        max_length=45,
        description="IP address of the scanning device",
    )
    latitude: float | None = Field(None, description="GPS latitude")
    longitude: float | None = Field(None, description="GPS longitude")
    city: str | None = Field(
        None,
        max_length=100,
        description="City from geo-resolution",
    )
    state: str | None = Field(
        None,
        max_length=100,
        description="State from geo-resolution",
    )
    country: str | None = Field(
        None,
        max_length=100,
        description="Country from geo-resolution",
    )


class ScanEventFilters(BaseModel):
    """Query parameters for filtering scan events.

    Requirements: 14.3
    """

    session_id: UUID | None = Field(
        None, description="Filter by session ID (stored in extra_data)"
    )
    worker_id: UUID | None = Field(
        None, description="Filter by worker ID (stored in extra_data)"
    )
    scan_context: str | None = Field(
        None,
        description="Filter by scan context: 'inbound', 'pick', or 'gate'",
    )
    date_from: datetime | None = Field(
        None, description="Start date filter (inclusive)"
    )
    date_to: datetime | None = Field(None, description="End date filter (inclusive)")
    serial_number: str | None = Field(None, description="Filter by serial number")
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
    product_item_id: str | None = None
    serial_number: str | None = None
    scan_timestamp: str | None = None
    device_type: str | None = None
    os: str | None = None
    browser: str | None = None
    ip_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    extra_data: dict[str, Any] | None = None


class PaginatedScanEvents(BaseModel):
    """Paginated list response for scan events.

    Requirements: 14.3
    """

    scan_events: list[ScanEventResponse]
    pagination: PaginationMeta
