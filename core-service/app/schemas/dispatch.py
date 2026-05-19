"""Pydantic schemas for dispatch record endpoints.

Handles the dispatch workflow:
- Create dispatch from verified gate session
- List dispatches with filters (date range, vehicle, invoice reference)
- Get dispatch detail

Requirements: 13.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


# ===========================================
# REQUEST SCHEMAS
# ===========================================


class CreateDispatchRequest(BaseModel):
    """Request schema for creating a dispatch record from a verified gate session.

    Requirements: 13.1
    """

    gate_session_id: UUID = Field(
        ..., description="UUID of the verified gate verification session"
    )


class DispatchFilters(BaseModel):
    """Query parameters for filtering dispatch records.

    Requirements: 13.3
    """

    date_from: Optional[datetime] = Field(
        None, description="Filter dispatches from this date (inclusive)"
    )
    date_to: Optional[datetime] = Field(
        None, description="Filter dispatches up to this date (inclusive)"
    )
    vehicle_number: Optional[str] = Field(
        None, description="Filter by vehicle number (partial match)"
    )
    invoice_reference: Optional[str] = Field(
        None, description="Filter by invoice reference (partial match)"
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class DispatchResponse(BaseModel):
    """Response schema for a dispatch record.

    Requirements: 13.1, 13.3
    """

    id: str
    organization_id: str
    dispatch_number: str
    pick_list_id: str
    gate_session_id: str
    invoice_reference: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    dispatched_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DispatchListResponse(BaseModel):
    """Paginated list response for dispatch records.

    Requirements: 13.3
    """

    dispatches: list[DispatchResponse]
    pagination: PaginationMeta
