"""Inbound API endpoints for scan sessions and receiving slips.

Handles the inbound receiving workflow:
- Start/end scan sessions for dock workers
- Record QR scans with duplicate detection
- Generate receiving slips from closed sessions
- Approve/reject receiving slips
- Flag line items as SHORT or DAMAGED

Requirements: 5.1, 5.6, 6.1, 7.2
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_CREATE, WAREHOUSE_READ, WAREHOUSE_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.inbound import (
    ApproveSlipRequest,
    FlaggedItemResponse,
    FlagLineItemRequest,
    ReceivingSlipResponse,
    RecordScanRequest,
    RejectSlipRequest,
    ScanResult,
    SessionResponse,
    SessionSummary,
    StartSessionRequest,
)
from app.services.inbound_service import InboundService

router = APIRouter()


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start inbound scan session",
    description="Start a new inbound scan session for a dock worker",
)
async def start_session(
    data: StartSessionRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Start a new inbound scan session.

    Creates a scan session with status OPEN for the current worker.

    **Request Body:**
    - **warehouse_id**: Warehouse UUID where receiving occurs
    - **dock_location**: Optional dock location identifier

    **Returns:** Created scan session details

    Requirements: 5.1
    """
    service = InboundService(db)
    result = service.start_session(
        worker_id=current_user.id,
        organization_id=current_user.organization_id,
        warehouse_id=data.warehouse_id,
        dock_location=data.dock_location,
    )
    return SessionResponse(**result)


@router.post(
    "/sessions/{session_id}/scan",
    response_model=ScanResult,
    status_code=status.HTTP_201_CREATED,
    summary="Record QR scan",
    description="Record a QR code scan within an open session",
)
async def record_scan(
    session_id: UUID,
    data: RecordScanRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Record a QR scan within an open session.

    Decodes the QR payload, checks for duplicates, and records the scan.

    **Path Parameters:**
    - **session_id**: UUID of the active scan session

    **Request Body:**
    - **qr_data**: Raw QR code payload string (JSON)
    - **device_type**: Optional device type
    - **os**: Optional operating system info

    **Returns:** Scan result with decoded payload info

    Requirements: 5.2, 5.3, 5.4
    """
    service = InboundService(db)
    result = service.record_scan(
        session_id=session_id,
        qr_data=data.qr_data,
        worker_id=current_user.id,
        organization_id=current_user.organization_id,
        device_type=data.device_type,
        os=data.os,
    )
    return ScanResult(**result)


@router.post(
    "/sessions/{session_id}/end",
    response_model=ReceivingSlipResponse,
    summary="End scan session",
    description="End a scan session and generate a receiving slip",
)
async def end_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    End a scan session and generate a receiving slip.

    Closes the session and generates a receiving slip from the scanned items,
    grouped by SKU and batch number.

    **Path Parameters:**
    - **session_id**: UUID of the scan session to close

    **Returns:** Generated receiving slip details

    Requirements: 5.5, 6.1
    """
    service = InboundService(db)
    result = service.end_session(
        session_id=session_id,
        worker_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    return ReceivingSlipResponse(**result)


@router.get(
    "/sessions/{session_id}/summary",
    response_model=SessionSummary,
    summary="Get session summary",
    description="Get a summary of a scan session with per-SKU/batch aggregation",
)
async def get_session_summary(
    session_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get a summary of a scan session.

    Returns total boxes scanned, per-SKU quantities, and per-batch breakdown.

    **Path Parameters:**
    - **session_id**: UUID of the scan session

    **Returns:** Session summary with aggregated data

    Requirements: 5.3, 5.6
    """
    service = InboundService(db)
    result = service.get_session_summary(
        session_id=session_id,
        organization_id=current_user.organization_id,
    )
    return SessionSummary(**result)


@router.get(
    "/receiving-slips/{slip_id}",
    response_model=ReceivingSlipResponse,
    summary="Get receiving slip",
    description="Get receiving slip details by ID",
)
async def get_receiving_slip(
    slip_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get receiving slip details.

    **Path Parameters:**
    - **slip_id**: UUID of the receiving slip

    **Returns:** Receiving slip details with line items

    Requirements: 6.1, 7.2
    """
    service = InboundService(db)
    slip = service.slip_repo.get_by_id(slip_id, current_user.organization_id)
    if slip is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(
            message="Receiving slip not found",
            entity_type="ReceivingSlip",
            entity_id=str(slip_id),
        )
    result = service._slip_to_dict(slip)
    return ReceivingSlipResponse(**result)


@router.post(
    "/receiving-slips/{slip_id}/approve",
    response_model=ReceivingSlipResponse,
    summary="Approve receiving slip",
    description="Approve a receiving slip, transitioning it to PENDING_PUTAWAY and triggering put-away list generation",
)
async def approve_slip(
    slip_id: UUID,
    data: ApproveSlipRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Approve a receiving slip.

    Transitions the slip from PENDING_REVIEW to PENDING_PUTAWAY, generates
    a put-away list with bin assignments respecting allocations and routing,
    and optionally creates a worker task if worker_id is provided.

    **Path Parameters:**
    - **slip_id**: UUID of the receiving slip to approve

    **Request Body (optional):**
    - **worker_id**: Optional UUID of the worker to assign the put-away task to

    **Returns:** Updated receiving slip details

    Requirements: 7.1, 7.3, 8.1
    """
    worker_id = data.worker_id if data else None
    service = InboundService(db)
    result = service.approve_slip(
        slip_id=slip_id,
        organization_id=current_user.organization_id,
        worker_id=worker_id,
    )
    return ReceivingSlipResponse(**result)


@router.post(
    "/receiving-slips/{slip_id}/reject",
    response_model=ReceivingSlipResponse,
    summary="Reject receiving slip",
    description="Reject a receiving slip with a reason",
)
async def reject_slip(
    slip_id: UUID,
    data: RejectSlipRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Reject a receiving slip with a reason.

    Transitions the slip from PENDING_REVIEW to REJECTED.

    **Path Parameters:**
    - **slip_id**: UUID of the receiving slip to reject

    **Request Body:**
    - **reason**: Reason for rejection

    **Returns:** Updated receiving slip details

    Requirements: 7.4
    """
    service = InboundService(db)
    result = service.reject_slip(
        slip_id=slip_id,
        reason=data.reason,
        organization_id=current_user.organization_id,
    )
    return ReceivingSlipResponse(**result)


@router.post(
    "/receiving-slips/{slip_id}/items/{item_id}/flag",
    response_model=FlaggedItemResponse,
    summary="Flag line item",
    description="Flag a receiving slip line item as SHORT or DAMAGED",
)
async def flag_line_item(
    slip_id: UUID,
    item_id: UUID,
    data: FlagLineItemRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Flag a receiving slip line item.

    Marks a line item as SHORT or DAMAGED with optional notes.

    **Path Parameters:**
    - **slip_id**: UUID of the receiving slip
    - **item_id**: UUID of the line item to flag

    **Request Body:**
    - **flag**: Flag value ('short' or 'damaged')
    - **notes**: Optional notes about the discrepancy

    **Returns:** Updated line item details

    Requirements: 7.5
    """
    service = InboundService(db)
    result = service.flag_line_item(
        slip_id=slip_id,
        item_id=item_id,
        flag=data.flag,
        notes=data.notes,
        organization_id=current_user.organization_id,
    )
    return FlaggedItemResponse(**result)
