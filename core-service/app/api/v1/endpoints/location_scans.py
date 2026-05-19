"""Location Scans API endpoints for QR-based time tracking.

Manages QR code scans at physical bin locations for worker time tracking:
- Record start/finish scans at locations
- Get time tracking summaries with filters

Requirements: 17.6
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import PICK_LIST_CREATE, PICK_LIST_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.location_scan import (
    LocationScanRequest,
    LocationScanResponse,
    TimeSummary,
)
from app.services.qr_scan_service import QRScanService

router = APIRouter()


@router.post(
    "",
    response_model=LocationScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a location scan",
    description="Record a start or finish QR scan at a physical bin location",
)
async def record_location_scan(
    data: LocationScanRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Record a location scan for time tracking.

    On a 'start' scan, creates a new record with the scan timestamp.
    On a 'finish' scan, validates that a preceding start scan exists
    for the same task and location, then calculates elapsed_seconds.

    **Request Body:**
    - **worker_id**: UUID of the worker performing the scan
    - **task_id**: UUID of the worker_task this scan belongs to
    - **location_code**: Location code being scanned (e.g., Z01-A03-B02-L04-B01)
    - **scan_type**: 'start' or 'finish'
    - **scanned_at**: Optional explicit timestamp (defaults to server time)

    **Returns:** Created location scan record

    Requirements: 17.1, 17.2, 17.3, 17.4
    """
    service = QRScanService(db)

    result = service.record_location_scan(
        worker_id=data.worker_id,
        task_id=data.task_id,
        location_code=data.location_code,
        scan_type=data.scan_type,
        org_id=current_user.organization_id,
        scanned_at=data.scanned_at,
    )

    return LocationScanResponse(**result)


@router.get(
    "/summary",
    response_model=TimeSummary,
    summary="Get time tracking summary",
    description="Get aggregated time tracking data with optional filters",
)
async def get_time_summary(
    worker_id: UUID | None = Query(None, description="Filter by worker UUID"),
    task_id: UUID | None = Query(None, description="Filter by worker_task UUID"),
    location_code: str | None = Query(None, description="Filter by location code"),
    date_from: date | None = Query(
        None, description="Start date for the date range filter"
    ),
    date_to: date | None = Query(
        None, description="End date for the date range filter"
    ),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    Get time tracking summary.

    Returns aggregated elapsed_seconds from finish scans, grouped by
    location. Supports filtering by worker, task, location, and date range.

    **Query Parameters:**
    - **worker_id**: Filter by worker UUID
    - **task_id**: Filter by worker_task UUID
    - **location_code**: Filter by location code
    - **date_from**: Start date for the date range filter
    - **date_to**: End date for the date range filter

    **Returns:** Aggregated time tracking summary with per-location breakdown

    Requirements: 17.6
    """
    service = QRScanService(db)

    result = service.get_time_summary(
        org_id=current_user.organization_id,
        worker_id=worker_id,
        task_id=task_id,
        location_code=location_code,
        date_from=date_from,
        date_to=date_to,
    )

    return TimeSummary(**result)
