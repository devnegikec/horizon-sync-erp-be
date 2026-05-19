"""Outbound API endpoints for SAP invoice-triggered pick list workflow,
gate verification, and dispatch.

Handles the outbound picking workflow:
- Create pick list from SAP invoice
- List pick lists with filters (status, date range, invoice reference)
- Get pick list detail with progress
- Record pick scans
- Complete pick list
- Cancel pick list

Handles gate verification workflow:
- Start gate verification session
- Record gate scans
- Get session progress
- Verify/complete session

Handles dispatch workflow:
- Create dispatch from verified gate session
- List dispatches with filters
- Get dispatch detail

Requirements: 9.1, 10.1, 11.3, 11.4, 12.1, 12.7, 13.3
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    PICK_LIST_CREATE,
    PICK_LIST_READ,
    PICK_LIST_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.dispatch import (
    CreateDispatchRequest,
    DispatchListResponse,
    DispatchResponse,
)
from app.schemas.gate_verification import (
    GateScanRequest,
    GateScanResult,
    GateSessionProgress,
    GateSessionRequest,
    GateSessionResponse,
)
from app.schemas.outbound import (
    OutboundPickListListResponse,
    OutboundPickListResponse,
    PickListProgress,
    PickScanRequest,
    PickScanResult,
    SAPInvoicePayload,
)
from app.services.gate_verification_service import GateVerificationService
from app.services.outbound_service import OutboundService
from app.services.pick_list_service import (
    PickListService,
    SAPInvoiceItem as ServiceSAPInvoiceItem,
    SAPInvoicePayload as ServiceSAPInvoicePayload,
)

router = APIRouter()


# =============================================================================
# GATE VERIFICATION ENDPOINTS
# =============================================================================
# NOTE: These literal-path routes MUST be registered before /{pick_list_id}
# routes to prevent FastAPI from capturing "gate-sessions" or "dispatches"
# as a UUID path parameter.


@router.post(
    "/gate-sessions",
    response_model=GateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start gate verification session",
    description="Start a gate verification session linked to a completed pick list",
)
async def start_gate_session(
    data: GateSessionRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Start a gate verification session.

    Creates a gate verification session linked to a completed pick list
    with vehicle and driver details. Security personnel use this to verify
    items being loaded onto a vehicle.

    **Request Body:**
    - **pick_list_id**: UUID of the completed pick list
    - **vehicle_number**: Optional vehicle registration number
    - **driver_name**: Optional driver name
    - **driver_contact**: Optional driver contact number

    **Returns:** Created gate verification session

    Requirements: 12.1
    """
    service = GateVerificationService(db)

    result = service.start_session(
        pick_list_id=data.pick_list_id,
        worker_id=current_user.id,
        org_id=current_user.organization_id,
        vehicle_number=data.vehicle_number,
        driver_name=data.driver_name,
        driver_contact=data.driver_contact,
    )

    return GateSessionResponse(**result)


@router.post(
    "/gate-sessions/{session_id}/scan",
    response_model=GateScanResult,
    status_code=status.HTTP_201_CREATED,
    summary="Record a gate scan",
    description="Record a QR code scan at the gate and validate against the pick list",
)
async def record_gate_scan(
    session_id: UUID,
    data: GateScanRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Record a gate scan.

    Decodes the QR payload and validates the scanned item against the
    associated pick list. Marks the item as VERIFIED if it belongs to
    the pick list, or UNAUTHORIZED if it doesn't.

    **Path Parameters:**
    - **session_id**: UUID of the gate verification session

    **Request Body:**
    - **qr_data**: Raw QR code payload string (JSON)

    **Returns:** Scan result with verification status

    Requirements: 12.2, 12.3, 12.4
    """
    service = GateVerificationService(db)

    result = service.record_gate_scan(
        session_id=session_id,
        qr_payload=data.qr_data,
        worker_id=current_user.id,
        org_id=current_user.organization_id,
        device_type=data.device_type,
        os=data.os,
    )

    return GateScanResult(**result)


@router.get(
    "/gate-sessions/{session_id}/progress",
    response_model=GateSessionProgress,
    summary="Get gate session progress",
    description="Get the progress of a gate verification session",
)
async def get_gate_session_progress(
    session_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    Get gate session progress.

    Returns the count of scanned items vs expected items from the
    pick list, along with verified and unauthorized counts.

    **Path Parameters:**
    - **session_id**: UUID of the gate verification session

    **Returns:** Session progress with scanned vs expected counts

    Requirements: 12.7
    """
    service = GateVerificationService(db)

    result = service.get_session_progress(
        session_id=session_id,
        org_id=current_user.organization_id,
    )

    return GateSessionProgress(**result)


@router.post(
    "/gate-sessions/{session_id}/verify",
    response_model=GateSessionResponse,
    summary="Verify gate session",
    description="Mark a gate session as verified when all items are scanned",
)
async def verify_gate_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Verify/complete a gate session.

    Validates that all expected items from the pick list have been
    scanned and verified, then transitions the session to VERIFIED status.

    **Path Parameters:**
    - **session_id**: UUID of the gate verification session

    **Returns:** Updated gate session with verified status

    Requirements: 12.5
    """
    service = GateVerificationService(db)

    result = service.verify_session(
        session_id=session_id,
        org_id=current_user.organization_id,
    )

    return GateSessionResponse(**result)


# =============================================================================
# DISPATCH ENDPOINTS
# =============================================================================


@router.post(
    "/dispatches",
    response_model=DispatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create dispatch from verified gate session",
    description="Create a dispatch record from a verified gate verification session",
)
async def create_dispatch(
    data: CreateDispatchRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a dispatch record.

    Creates a dispatch record from a verified gate session, decrements
    warehouse stock levels for all dispatched items, and generates a
    unique dispatch number.

    **Request Body:**
    - **gate_session_id**: UUID of the verified gate verification session

    **Returns:** Created dispatch record

    Requirements: 13.1, 13.4, 13.5
    """
    service = OutboundService(db)

    result = service.create_dispatch(
        gate_session_id=data.gate_session_id,
        org_id=current_user.organization_id,
    )

    return DispatchResponse(**result)


@router.get(
    "/dispatches",
    response_model=DispatchListResponse,
    summary="List dispatch records",
    description="List dispatch records with optional filters",
)
async def list_dispatches(
    date_from: datetime | None = Query(
        None, description="Filter dispatches from this date (inclusive)"
    ),
    date_to: datetime | None = Query(
        None, description="Filter dispatches up to this date (inclusive)"
    ),
    vehicle_number: str | None = Query(
        None, description="Filter by vehicle number (partial match)"
    ),
    invoice_reference: str | None = Query(
        None, description="Filter by invoice reference (partial match)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    List dispatch records with filters and pagination.

    Supports filtering by date range, vehicle number, and invoice reference.

    **Query Parameters:**
    - **date_from**: Filter dispatches from this date (inclusive)
    - **date_to**: Filter dispatches up to this date (inclusive)
    - **vehicle_number**: Filter by vehicle number (partial match)
    - **invoice_reference**: Filter by invoice reference (partial match)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    **Returns:** Paginated list of dispatch records

    Requirements: 13.3
    """
    service = OutboundService(db)

    result = service.list_dispatches(
        org_id=current_user.organization_id,
        date_from=date_from,
        date_to=date_to,
        vehicle_number=vehicle_number,
        invoice_reference=invoice_reference,
        page=page,
        page_size=page_size,
    )

    return DispatchListResponse(**result)


@router.get(
    "/dispatches/{dispatch_id}",
    response_model=DispatchResponse,
    summary="Get dispatch detail",
    description="Get a single dispatch record by ID",
)
async def get_dispatch_detail(
    dispatch_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    Get dispatch record detail.

    Returns the full dispatch record including pick list reference,
    gate session reference, vehicle details, and timestamps.

    **Path Parameters:**
    - **dispatch_id**: UUID of the dispatch record

    **Returns:** Dispatch record detail

    Requirements: 13.3
    """
    service = OutboundService(db)

    result = service.get_dispatch(
        dispatch_id=dispatch_id,
        org_id=current_user.organization_id,
    )

    return DispatchResponse(**result)


# =============================================================================
# PICK LIST ENDPOINTS
# =============================================================================


def _compute_progress(pick_list) -> PickListProgress:
    """Compute progress information for a pick list.

    Requirements: 11.4
    """
    total_items = len(pick_list.items) if pick_list.items else 0
    picked_items = 0
    total_qty = Decimal("0")
    picked_qty = Decimal("0")

    for item in pick_list.items or []:
        item_qty = Decimal(str(item.qty))
        item_picked = Decimal(str(item.picked_qty or 0))
        total_qty += item_qty
        picked_qty += item_picked
        if item_picked >= item_qty:
            picked_items += 1

    remaining_items = total_items - picked_items
    remaining_qty = total_qty - picked_qty
    completion_percentage = (
        float(picked_qty / total_qty * 100) if total_qty > 0 else 0.0
    )

    return PickListProgress(
        total_items=total_items,
        picked_items=picked_items,
        remaining_items=remaining_items,
        total_qty=float(total_qty),
        picked_qty=float(picked_qty),
        remaining_qty=float(remaining_qty),
        completion_percentage=round(completion_percentage, 2),
    )


def _pick_list_to_response(pl) -> OutboundPickListResponse:
    """Convert a PickList model to an OutboundPickListResponse."""
    progress = _compute_progress(pl)

    items = []
    for item in pl.items or []:
        items.append(
            {
                "id": str(item.id),
                "item_id": str(item.item_id),
                "warehouse_id": str(item.warehouse_id),
                "qty": float(item.qty),
                "picked_qty": float(item.picked_qty or 0),
                "uom": item.uom,
                "batch_no": item.batch_no,
                "bin_location_id": str(item.bin_location_id)
                if item.bin_location_id
                else None,
                "sort_order": item.sort_order or 0,
            }
        )

    return OutboundPickListResponse(
        id=str(pl.id),
        organization_id=str(pl.organization_id),
        pick_list_no=pl.pick_list_no,
        warehouse_id=str(pl.warehouse_id),
        status=pl.status.value if pl.status else "draft",
        pick_date=pl.pick_date.isoformat() if pl.pick_date else None,
        reference_type=pl.reference_type,
        invoice_reference=pl.invoice_reference,
        completed_at=pl.completed_at.isoformat() if pl.completed_at else None,
        created_at=pl.created_at.isoformat() if pl.created_at else None,
        updated_at=pl.updated_at.isoformat() if pl.updated_at else None,
        items=items,
        progress=progress,
    )


@router.post(
    "/from-invoice",
    response_model=OutboundPickListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create pick list from SAP invoice",
    description="Create a new pick list triggered by a SAP sales invoice",
)
async def create_from_invoice(
    data: SAPInvoicePayload,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a pick list from a SAP sales invoice.

    Parses the invoice payload, creates a pick list with status OPEN (draft),
    and populates items from invoice lines.

    **Request Body:**
    - **invoice_reference**: SAP invoice reference number
    - **warehouse_id**: Target warehouse UUID
    - **items**: List of invoice line items (item_id, sku, quantity, uom)

    **Returns:** Created pick list with items and progress

    Requirements: 9.1, 9.2, 9.5
    """
    service = PickListService(db)

    # Convert schema to service dataclass
    invoice_payload = ServiceSAPInvoicePayload(
        invoice_reference=data.invoice_reference,
        warehouse_id=data.warehouse_id,
        items=[
            ServiceSAPInvoiceItem(
                item_id=item.item_id,
                sku=item.sku,
                quantity=item.quantity,
                uom=item.uom,
            )
            for item in data.items
        ],
    )

    pick_list = service.create_from_invoice(
        invoice_data=invoice_payload,
        org_id=current_user.organization_id,
        worker_id=current_user.id,
    )

    return _pick_list_to_response(pick_list)


@router.get(
    "",
    response_model=OutboundPickListListResponse,
    summary="List outbound pick lists",
    description="List pick lists with optional filters for status, warehouse, and invoice reference",
)
async def list_pick_lists(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: draft, in_progress, completed, cancelled",
    ),
    warehouse_id: UUID | None = Query(
        None, description="Filter by warehouse ID"
    ),
    invoice_reference: str | None = Query(
        None, description="Filter by SAP invoice reference"
    ),
    sort_by: str = Query(
        "created_at", description="Sort field: created_at, pick_list_no, status"
    ),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    List outbound pick lists with filters and pagination.

    Supports filtering by status, warehouse, and invoice reference.
    Includes progress information for each pick list.

    **Query Parameters:**
    - **status**: Filter by pick list status
    - **warehouse_id**: Filter by warehouse UUID
    - **invoice_reference**: Filter by SAP invoice reference
    - **sort_by**: Sort field (default: created_at)
    - **sort_order**: Sort direction (default: desc)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    **Returns:** Paginated list of pick lists with progress

    Requirements: 11.3, 11.4
    """
    service = PickListService(db)

    pick_lists_data, pagination = service.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        warehouse_id=warehouse_id,
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # For the list view, we need to fetch full pick list objects to compute progress
    # The service returns dicts from _to_list_item, so we need to get full objects
    from app.models.pick_list import PickList

    result_items = []
    for pl_data in pick_lists_data:
        pl_id = pl_data["id"]
        # Fetch the full pick list with items for progress computation
        pl = (
            db.query(PickList)
            .filter(
                PickList.id == pl_id,
                PickList.organization_id == current_user.organization_id,
            )
            .first()
        )

        if pl:
            # Apply invoice_reference filter if specified
            if invoice_reference and pl.invoice_reference != invoice_reference:
                continue

            progress = _compute_progress(pl)
            result_items.append(
                {
                    "id": str(pl.id),
                    "organization_id": str(pl.organization_id),
                    "pick_list_no": pl.pick_list_no,
                    "warehouse_id": str(pl.warehouse_id),
                    "status": pl.status.value if pl.status else "draft",
                    "invoice_reference": pl.invoice_reference,
                    "pick_date": pl.pick_date.isoformat() if pl.pick_date else None,
                    "completed_at": pl.completed_at.isoformat()
                    if pl.completed_at
                    else None,
                    "created_at": pl.created_at.isoformat()
                    if pl.created_at
                    else None,
                    "progress": progress,
                }
            )

    return OutboundPickListListResponse(
        pick_lists=result_items,
        pagination=pagination,
    )


@router.get(
    "/{pick_list_id}",
    response_model=OutboundPickListResponse,
    summary="Get pick list detail",
    description="Get detailed pick list information including items and progress",
)
async def get_pick_list_detail(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """
    Get pick list detail with items and progress.

    Returns the full pick list with all items and progress information
    (total items, picked items, remaining items).

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Returns:** Pick list detail with items and progress

    Requirements: 11.4
    """
    service = PickListService(db)

    # Use the repository to get the full model object
    from app.models.pick_list import PickList

    pl = (
        db.query(PickList)
        .filter(
            PickList.id == pick_list_id,
            PickList.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not pl:
        from app.core.exceptions import ResourceNotFoundException

        raise ResourceNotFoundException(f"Pick list {pick_list_id} not found")

    return _pick_list_to_response(pl)


@router.post(
    "/{pick_list_id}/scan",
    response_model=PickScanResult,
    status_code=status.HTTP_201_CREATED,
    summary="Record pick scan",
    description="Record a QR code scan against a pick list",
)
async def record_pick_scan(
    pick_list_id: UUID,
    data: PickScanRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Record a QR code scan against a pick list.

    Decodes the QR payload, matches the SKU against pick list items,
    increments picked_qty, and transitions the pick list to IN_PROGRESS
    on the first scan.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Request Body:**
    - **qr_data**: Raw QR code payload string (JSON)

    **Returns:** Scan result with updated quantities

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.2
    """
    service = PickListService(db)

    result = service.record_pick_scan(
        pick_list_id=pick_list_id,
        qr_data=data.qr_data,
        worker_id=current_user.id,
        org_id=current_user.organization_id,
    )

    return PickScanResult(**result)


@router.post(
    "/{pick_list_id}/complete",
    response_model=OutboundPickListResponse,
    summary="Complete pick list",
    description="Mark a pick list as completed when all items are fully picked",
)
async def complete_pick_list(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Complete a pick list.

    Validates that all items have been fully picked and transitions
    the pick list status to COMPLETED.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Returns:** Updated pick list with completed status

    Requirements: 10.6, 10.7
    """
    service = PickListService(db)

    pick_list = service.complete_pick_list(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
    )

    return _pick_list_to_response(pick_list)


@router.post(
    "/{pick_list_id}/cancel",
    response_model=OutboundPickListResponse,
    summary="Cancel pick list",
    description="Cancel a pick list and release any reserved stock",
)
async def cancel_pick_list(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Cancel a pick list.

    Releases any reserved stock back to available inventory and
    transitions the pick list status to CANCELLED.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Returns:** Updated pick list with cancelled status

    Requirements: 11.1, 11.5
    """
    service = PickListService(db)

    pick_list = service.cancel_pick_list(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
    )

    return _pick_list_to_response(pick_list)
