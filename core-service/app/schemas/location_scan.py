"""Pydantic schemas for location scan (QR time tracking) endpoints.

Handles QR-based time tracking at physical bin locations:
- Record start/finish scans at locations
- Get time tracking summaries with filters

Requirements: 17.6
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ===========================================
# REQUEST SCHEMAS
# ===========================================


class LocationScanRequest(BaseModel):
    """Request schema for recording a location scan.

    Requirements: 17.1
    """

    worker_id: UUID = Field(
        ..., description="UUID of the worker performing the scan"
    )
    task_id: UUID = Field(
        ..., description="UUID of the worker_task this scan belongs to"
    )
    location_code: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Location code being scanned (e.g., Z01-A03-B02-L04-B01)",
    )
    scan_type: str = Field(
        ...,
        description="Scan type: 'start' or 'finish'",
        pattern="^(start|finish)$",
    )
    scanned_at: Optional[datetime] = Field(
        None,
        description="Explicit scan timestamp (defaults to server time if omitted)",
    )


class TimeSummaryFilters(BaseModel):
    """Query parameters for time tracking summary.

    Requirements: 17.6
    """

    worker_id: Optional[UUID] = Field(
        None, description="Filter by worker UUID"
    )
    task_id: Optional[UUID] = Field(
        None, description="Filter by worker_task UUID"
    )
    location_code: Optional[str] = Field(
        None, description="Filter by location code"
    )
    date_from: Optional[date] = Field(
        None, description="Start date for the date range filter"
    )
    date_to: Optional[date] = Field(
        None, description="End date for the date range filter"
    )


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class LocationScanResponse(BaseModel):
    """Response schema for a recorded location scan.

    Requirements: 17.5
    """

    id: str
    organization_id: str
    worker_task_id: str
    location_code: str
    scan_type: str
    scanned_at: Optional[str] = None
    elapsed_seconds: Optional[int] = None
    created_at: Optional[str] = None


class LocationTimeSummaryItem(BaseModel):
    """Time summary for a specific location."""

    location_code: str
    total_elapsed_seconds: int
    scan_count: int
    avg_elapsed_seconds: float


class TimeSummary(BaseModel):
    """Aggregated time tracking summary response.

    Requirements: 17.6
    """

    total_elapsed_seconds: int
    total_scans: int
    avg_elapsed_seconds: float
    by_location: list[LocationTimeSummaryItem]
    records: list[LocationScanResponse]
