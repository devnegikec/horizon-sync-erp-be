"""Scan Events API endpoints for QR scan audit trail.

Provides query access to the unified scan event audit trail across all
warehouse contexts (inbound, pick, gate). Supports filtering by session_id,
worker_id, date range, scan_context, and serial_number.

Requirements: 14.3
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import PICK_LIST_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.scan_event import (
    PaginatedScanEvents,
    ScanEventCreate,
    ScanEventResponse,
)
from app.services.scan_event_service import ScanEventService

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedScanEvents,
    summary="List scan events",
    description="Query scan events with filters for audit trail. "
    "Supports filtering by session_id, worker_id, date range, scan_context, and serial_number.",
)
async def list_scan_events(
    session_id: UUID | None = Query(
        None, description="Filter by session ID (inbound or gate session)"
    ),
    worker_id: UUID | None = Query(None, description="Filter by worker ID"),
    date_from: datetime | None = Query(
        None, description="Start date filter (inclusive)"
    ),
    date_to: datetime | None = Query(None, description="End date filter (inclusive)"),
    scan_context: str | None = Query(
        None, description="Filter by scan context: 'inbound', 'pick', or 'gate'"
    ),
    serial_number: str | None = Query(None, description="Filter by serial number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    List scan events with filters and pagination.

    Returns scan events for the authenticated user's organization,
    optionally filtered by session_id, worker_id, date range,
    scan_context, and serial_number. Results are ordered by
    scan_timestamp descending (most recent first).

    **Query Parameters:**
    - **session_id**: Filter by session ID (stored in extra_data)
    - **worker_id**: Filter by worker ID (stored in extra_data)
    - **date_from**: Start date filter (inclusive)
    - **date_to**: End date filter (inclusive)
    - **scan_context**: Filter by scan context ('inbound', 'pick', 'gate')
    - **serial_number**: Filter by serial number
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    **Returns:** Paginated list of scan events

    Requirements: 14.3
    """
    service = ScanEventService(db)

    result = service.query_events(
        organization_id=current_user.organization_id,
        session_id=session_id,
        worker_id=worker_id,
        scan_context=scan_context,
        date_from=date_from,
        date_to=date_to,
        serial_number=serial_number,
        page=page,
        page_size=page_size,
    )

    return PaginatedScanEvents(
        scan_events=[ScanEventResponse(**event) for event in result["scan_events"]],
        pagination=result["pagination"],
    )


@router.post(
    "",
    response_model=ScanEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a scan event",
    description="Record a QR scan event with full context (who, when, where, what) "
    "for audit trail purposes.",
)
async def create_scan_event(
    data: ScanEventCreate,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    Record a scan event.

    Creates a scan event record in the qr_scan_events table with full
    context stored in the extra_data JSONB field.

    **Request Body:**
    - **worker_id**: UUID of the worker performing the scan
    - **scan_context**: Context of the scan ('inbound', 'pick', or 'gate')
    - **serial_number**: Optional serial number or QR identifier
    - **session_id**: Optional session ID (inbound or gate session)
    - **pick_list_id**: Optional pick list ID
    - **decoded_payload**: Optional decoded QR payload data
    - **device_type**: Optional device type
    - **os**: Optional operating system info

    **Returns:** Created scan event record

    Requirements: 14.1, 14.2, 14.4
    """
    service = ScanEventService(db)

    result = service.record_event(
        organization_id=current_user.organization_id,
        worker_id=data.worker_id,
        scan_context=data.scan_context,
        serial_number=data.serial_number,
        session_id=data.session_id,
        pick_list_id=data.pick_list_id,
        decoded_payload=data.decoded_payload,
        device_type=data.device_type,
        os=data.os,
        product_item_id=data.product_item_id,
        ip_address=data.ip_address,
        latitude=data.latitude,
        longitude=data.longitude,
        city=data.city,
        state=data.state,
        country=data.country,
    )

    return ScanEventResponse(**result)
