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

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.authorization import (
    PICK_LIST_CREATE,
    PICK_LIST_READ,
    PICK_LIST_UPDATE,
)
from app.models.base import PickListStatus
from app.core.exceptions import ValidationError
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.dispatch import (
    CreateDispatchRequest,
    DispatchListResponse,
    DispatchResponse,
)
from app.schemas.erp_sync import (
    ErpSyncFlushResponse,
    ErpSyncListResponse,
    ErpSyncMessageResponse,
)
from app.schemas.gate_verification import (
    GateScanRequest,
    GateScanResult,
    GateSessionProgress,
    GateSessionRequest,
    GateSessionResponse,
)
from app.schemas.outbound import (
    AssignHandlingUnitRequest,
    AssignWorkerRequest,
    CreatePickListFromOrderRequest,
    HandlingUnitAssignmentResponse,
    OutboundOrderItemResponse,
    OutboundOrderListItem,
    OutboundOrderListResponse,
    OutboundOrderResponse,
    OutboundOrderStatusCounts,
    OutboundPickListListResponse,
    OutboundPickListResponse,
    OutboundPickListStatusCounts,
    PickListProgress,
    PickScanRequest,
    PickScanResult,
    SAPInvoicePayload,
    StageScanRequest,
    StageTransferRequest,
    UpdatePriorityRequest,
)
from app.services.gate_verification_service import GateVerificationService
from app.services.order_import_service import OrderImportService
from app.services.outbound_order_service import OutboundOrderService
from app.services.outbound_service import OutboundService
from app.services.pick_idempotency_service import (
    OPERATION_CANCEL,
    OPERATION_COMPLETE,
    OPERATION_SCAN,
    PickIdempotencyService,
)
from app.services.pick_list_service import (
    PickListService,
)
from app.services.pick_list_service import (
    SAPInvoiceItem as ServiceSAPInvoiceItem,
)
from app.services.pick_list_service import (
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
    - **pick_list_id**: UUID of the completed pick list (preferred)
    - **pick_list_no**: Pick list number e.g. "PL-2026-00008" (alternative)
    - **vehicle_number**: Optional vehicle registration number
    - **driver_name**: Optional driver name
    - **driver_contact**: Optional driver contact number

    **Returns:** Created gate verification session

    Requirements: 12.1
    """
    from app.models.pick_list import PickList

    pick_list_id = data.pick_list_id

    # Resolve pick_list_no to UUID if pick_list_id wasn't provided
    if pick_list_id is None and data.pick_list_no:
        pick_list = (
            db.query(PickList)
            .filter(
                PickList.pick_list_no == data.pick_list_no.strip(),
                PickList.organization_id == current_user.organization_id,
            )
            .first()
        )
        if pick_list is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pick list not found: {data.pick_list_no}",
            )
        pick_list_id = pick_list.id

    if pick_list_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either pick_list_id (UUID) or pick_list_no must be provided",
        )

    service = GateVerificationService(db)

    result = service.start_session(
        pick_list_id=pick_list_id,
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


def _resolve_pick_serials(items, db) -> dict[str, list[dict]]:
    """Resolve per-unit serials for each pick list item from its serial_nos.

    ``batch_no`` holds the packing-slip batch number (matches the uploaded
    PDF), while ``serial_nos`` holds the individual bin-stock serials assigned
    during bin resolution. Here we only enrich the serials with Mfg/Exp from
    QSealParameters.
    """
    result: dict[str, list[dict]] = {}
    if not items:
        return result

    all_serials: set[str] = set()
    for item in items:
        serials: list[dict] = []
        for sn in item.serial_nos or []:
            if sn:
                all_serials.add(sn)
                serials.append(
                    {
                        "serial_number": sn,
                        "manufacturing_date": None,
                        "expiry_date": None,
                    }
                )
        result[str(item.id)] = serials

    if all_serials and db:
        try:
            from app.models.qseal import QSealParameters

            qrows = (
                db.query(
                    QSealParameters.serial_number,
                    QSealParameters.manufacturing_date,
                    QSealParameters.expiry_date,
                )
                .filter(QSealParameters.serial_number.in_(all_serials))
                .all()
            )
            qmeta = {
                sn: {
                    "manufacturing_date": str(m) if m else None,
                    "expiry_date": str(e) if e else None,
                }
                for sn, m, e in qrows
            }
            for item in items:
                for s in result[str(item.id)]:
                    meta = qmeta.get(s["serial_number"]) or {}
                    s["manufacturing_date"] = meta.get("manufacturing_date")
                    s["expiry_date"] = meta.get("expiry_date")
        except Exception:
            pass

    return result


def _identity_engine():
    """Return a read-only engine to the identity database, or None if unset."""
    from sqlalchemy import create_engine

    from app.config import settings

    if not settings.identity_database_url:
        return None
    return create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)


def _resolve_worker_names(user_ids: set[UUID]) -> dict[str, str]:
    """Batch-resolve worker UUIDs to names from the identity database."""
    if not user_ids:
        return {}
    engine = _identity_engine()
    if engine is None:
        return {}
    try:
        uid_list = [str(u) for u in user_ids]
        placeholders = ", ".join(f":w{i}" for i in range(len(uid_list)))
        params = {f"w{i}": uid_list[i] for i in range(len(uid_list))}
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id::text, display_name, first_name, last_name "
                    f"FROM users WHERE id::text IN ({placeholders})"
                ),
                params,
            ).fetchall()
        name_by_id: dict[str, str] = {}
        for uid, display_name, first_name, last_name in rows:
            name = display_name or f"{first_name or ''} {last_name or ''}".strip()
            if name:
                name_by_id[uid] = name
        return name_by_id
    except Exception:
        return {}
    finally:
        engine.dispose()


def _resolve_worker_name(worker_id, db=None) -> str | None:
    """Resolve a human-readable worker name for a pick list's assigned worker.

    Workers live in the identity database's ``users`` table
    (user_type=warehouse_worker). Falls back to the core ``users`` table when
    the identity database is unavailable, then to the raw UUID.
    """
    if not worker_id:
        return None

    name = _resolve_worker_names({worker_id}).get(str(worker_id))
    if name:
        return name

    if db is not None:
        try:
            row = db.execute(
                text(
                    "SELECT display_name, first_name, last_name "
                    "FROM users WHERE id=:id"
                ),
                {"id": worker_id},
            ).fetchone()
            if row:
                display_name, first_name, last_name = row
                return display_name or f"{first_name} {last_name}".strip() or str(worker_id)
        except Exception:
            pass
    return str(worker_id)


def _pick_list_aging(pl, db) -> dict:
    """Compute task-aging status (ALT-011) using the org's aging threshold."""
    threshold = 120
    if db is not None:
        try:
            from app.services.pick_settings_service import PickConfigResolver

            threshold = PickConfigResolver.from_org(db, pl.organization_id).get_int(
                "aging_threshold_minutes"
            )
        except Exception:
            pass
    return PickListService.aging_info(pl, threshold)


def _pick_list_to_response(pl, db=None) -> OutboundPickListResponse:
    """Convert a PickList model to an OutboundPickListResponse."""
    progress = _compute_progress(pl)

    # Batch-fetch item names and SKUs
    item_ids = [item.item_id for item in (pl.items or [])]
    item_map: dict[str, dict] = {}
    bin_map: dict[str, str] = {}
    if item_ids and db:
        from app.models.item import Item
        rows = db.query(Item.id, Item.item_name, Item.item_code, Item.sku).filter(
            Item.id.in_(item_ids)
        ).all()
        item_map = {
            str(r.id): {
                "item_name": r.item_name,
                "item_code": r.item_code,
                "sku": r.sku or r.item_code,
            }
            for r in rows
        }

    # Batch-fetch bin full paths
    bin_ids = [item.bin_location_id for item in (pl.items or []) if item.bin_location_id]
    if bin_ids and db:
        from app.models.warehouse_location import WarehouseLocation
        rows = db.query(WarehouseLocation.id, WarehouseLocation.full_path).filter(
            WarehouseLocation.id.in_(bin_ids)
        ).all()
        bin_map = {str(r.id): r.full_path for r in rows}

    # Resolve per-unit serials for each item line
    serials_by_item = _resolve_pick_serials(pl.items or [], db)

    items = []
    for item in pl.items or []:
        info = item_map.get(str(item.item_id), {})
        items.append(
            {
                "id": str(item.id),
                "item_id": str(item.item_id),
                "item_name": info.get("item_name"),
                "sku": info.get("sku"),
                "warehouse_id": str(item.warehouse_id),
                "qty": float(item.qty),
                "picked_qty": float(item.picked_qty or 0),
                "uom": item.uom,
                "per_case_qty": float(item.per_case_qty)
                if item.per_case_qty is not None
                else None,
                "case_qty": float(item.case_qty)
                if item.case_qty is not None
                else None,
                "loose_qty": float(item.loose_qty)
                if item.loose_qty is not None
                else None,
                "batch_no": item.batch_no,
                "bin_location_id": str(item.bin_location_id)
                if item.bin_location_id
                else None,
                "bin_location_path": bin_map.get(str(item.bin_location_id))
                if item.bin_location_id
                else None,
                "handling_unit_id": str(item.handling_unit_id)
                if item.handling_unit_id
                else None,
                "sort_order": item.sort_order or 0,
                "serials": [
                    {**s, "sku": info.get("sku")}
                    for s in serials_by_item.get(str(item.id), [])
                ],
            }
        )

    worker_name = _resolve_worker_name(pl.assigned_to, db)
    aging = _pick_list_aging(pl, db)

    return OutboundPickListResponse(
        id=str(pl.id),
        organization_id=str(pl.organization_id),
        pick_list_no=pl.pick_list_no,
        warehouse_id=str(pl.warehouse_id),
        status=pl.status.value if pl.status else "draft",
        pick_date=pl.pick_date.isoformat() if pl.pick_date else None,
        reference_type=pl.reference_type,
        reference_id=str(pl.reference_id) if pl.reference_id else None,
        invoice_reference=pl.invoice_reference,
        assigned_to=str(pl.assigned_to) if pl.assigned_to else None,
        worker_name=worker_name,
        completed_at=pl.completed_at.isoformat() if pl.completed_at else None,
        accepted_at=pl.accepted_at.isoformat() if pl.accepted_at else None,
        accepted_by=str(pl.accepted_by) if pl.accepted_by else None,
        created_at=pl.created_at.isoformat() if pl.created_at else None,
        updated_at=pl.updated_at.isoformat() if pl.updated_at else None,
        priority=pl.priority or 0,
        dispatch_cutoff=pl.dispatch_cutoff.isoformat() if pl.dispatch_cutoff else None,
        wave=pl.wave,
        route=pl.route,
        sla_minutes=pl.sla_minutes,
        age_minutes=aging["age_minutes"],
        is_aging=aging["is_aging"],
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
                per_case_qty=item.per_case_qty,
                case_qty=item.case_qty,
                loose_qty=item.loose_qty,
                batch_no=item.batch_no,
            )
            for item in data.items
        ],
    )

    pick_list = service.create_from_invoice(
        invoice_data=invoice_payload,
        org_id=current_user.organization_id,
        worker_id=current_user.id,
        assigned_to=data.assigned_to,
    )

    return _pick_list_to_response(pick_list, db)


@router.post(
    "/import",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Import orders from PDF/CSV and create outbound orders",
    description="Upload a PDF packing slip or CSV order file to create outbound orders",
)
async def import_orders(
    file: UploadFile = File(..., description="PDF or CSV order file"),
    warehouse_id: UUID = Query(..., description="Target warehouse UUID"),
    order_type: str = Query("sap", description="Order type: 'sap' or 'asn'"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Import orders from a PDF or CSV file and create outbound orders.

    Supported formats:
    - **PDF**: Packing slips / invoice PDFs with machine-readable text
    - **CSV**: Structured order data with columns for invoice, SKU, quantity, etc.

    The service extracts invoice references, line items, and quantities,
    then creates an outbound order for each order found in the file. Pick
    lists are generated later from a confirmed order.

    **Query Parameters:**
    - **warehouse_id**: Target warehouse UUID for all created orders
    - **order_type**: 'sap' (default) or 'asn'

    **Request Body:** Multipart file upload (PDF or CSV)

    **Returns:**
    - orders_created: Number of outbound orders created
    - total_items: Total items across all orders
    - errors: Any parsing or creation errors encountered
    """
    if not file.filename:
        raise ValidationError("No file provided")

    content = await file.read()
    if not content:
        raise ValidationError("Uploaded file is empty")

    service = OrderImportService(db)
    result = service.import_file(
        file_content=content,
        filename=file.filename,
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        order_type=order_type,
    )

    return {
        "orders_created": result.orders_created,
        "total_items": result.total_items,
        "errors": result.errors,
        "orders_parsed": len(result.parsed_orders),
    }


# =============================================================================
# OUTBOUND ORDER ENDPOINTS
# =============================================================================
# NOTE: literal-path routes ("/orders") must be registered before /{pick_list_id}
# routes. They use a distinct first path segment so UUID capture is unaffected.


def _order_item_map(db, item_ids) -> dict[str, dict]:
    """Batch-fetch item display fields for a set of item UUIDs."""
    if not item_ids or db is None:
        return {}
    from app.models.item import Item

    rows = db.query(Item.id, Item.item_name, Item.item_code, Item.sku).filter(
        Item.id.in_(item_ids)
    ).all()
    return {
        str(r.id): {
            "item_name": r.item_name,
            "item_code": r.item_code,
            "sku": r.sku or r.item_code,
        }
        for r in rows
    }


def _order_pick_list_map(db, order_ids) -> dict[str, list[str]]:
    """Batch-fetch pick list IDs referencing each outbound order."""
    if not order_ids or db is None:
        return {}
    from app.models.pick_list import PickList

    rows = (
        db.query(PickList.id, PickList.reference_id)
        .filter(PickList.reference_id.in_(order_ids))
        .all()
    )
    result: dict[str, list[str]] = {}
    for pick_id, order_id in rows:
        result.setdefault(str(order_id), []).append(str(pick_id))
    return result


def _order_item_counts(db, order_ids) -> dict[str, tuple[int, int]]:
    """Return {order_id: (total_items, in_stock_items)} via one aggregate query.

    Avoids loading the full line-item rows for list serialization.
    """
    if not order_ids or db is None:
        return {}
    from sqlalchemy import case, func

    from app.models.base import OutboundOrderItemStockStatus
    from app.models.outbound_order import OutboundOrderItem

    rows = (
        db.query(
            OutboundOrderItem.outbound_order_id,
            func.count(OutboundOrderItem.id),
            func.sum(
                case(
                    (
                        OutboundOrderItem.stock_status
                        == OutboundOrderItemStockStatus.IN_STOCK,
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        .filter(OutboundOrderItem.outbound_order_id.in_(order_ids))
        .group_by(OutboundOrderItem.outbound_order_id)
        .all()
    )
    return {
        str(r[0]): (int(r[1] or 0), int(r[2] or 0))
        for r in rows
    }


def _order_to_list_item(
    order, item_counts: dict[str, tuple[int, int]]
) -> OutboundOrderListItem:
    """Convert an OutboundOrder to a lightweight list item (no line items)."""
    total_items, in_stock = item_counts.get(str(order.id), (0, 0))
    return OutboundOrderListItem(
        id=str(order.id),
        organization_id=str(order.organization_id),
        order_no=order.order_no,
        order_type=order.order_type.value,
        warehouse_id=str(order.warehouse_id),
        status=order.status.value,
        invoice_reference=order.invoice_reference,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
        item_count=total_items,
        in_stock_count=in_stock,
        out_of_stock_count=total_items - in_stock,
    )


def _order_to_response(
    order,
    db,
    item_map: dict[str, dict] | None = None,
    pick_list_ids: list[str] | None = None,
) -> OutboundOrderResponse:
    """Convert an OutboundOrder model to an OutboundOrderResponse.

    ``item_map`` and ``pick_list_ids`` may be pre-computed by the caller to
    avoid N+1 queries when serializing a list of orders.
    """
    if item_map is None:
        item_map = _order_item_map(db, [item.item_id for item in (order.items or [])])

    items = []
    for item in order.items or []:
        info = item_map.get(str(item.item_id), {})
        items.append(
            OutboundOrderItemResponse(
                id=str(item.id),
                item_id=str(item.item_id),
                item_name=info.get("item_name"),
                sku=item.sku or info.get("sku"),
                qty=float(item.qty),
                uom=item.uom,
                per_case_qty=float(item.per_case_qty)
                if item.per_case_qty is not None
                else None,
                case_qty=float(item.case_qty) if item.case_qty is not None else None,
                loose_qty=float(item.loose_qty)
                if item.loose_qty is not None
                else None,
                batch_no=item.batch_no,
                stock_status=item.stock_status.value,
                available_qty=float(item.available_qty)
                if item.available_qty is not None
                else None,
            )
        )

    if pick_list_ids is None:
        from app.models.pick_list import PickList

        pick_list_ids = [
            str(r[0])
            for r in db.query(PickList.id)
            .filter(PickList.reference_id == order.id)
            .all()
        ]

    return OutboundOrderResponse(
        id=str(order.id),
        organization_id=str(order.organization_id),
        order_no=order.order_no,
        order_type=order.order_type.value,
        warehouse_id=str(order.warehouse_id),
        status=order.status.value,
        invoice_reference=order.invoice_reference,
        source_filename=order.source_filename,
        remarks=order.remarks,
        reference_type=order.reference_type,
        reference_id=str(order.reference_id) if order.reference_id else None,
        reference_no=order.reference_no,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
        pick_list_ids=pick_list_ids,
        items=items,
    )


@router.get(
    "/orders",
    response_model=OutboundOrderListResponse,
    summary="List outbound orders",
    description="List outbound orders (ASN/SAP) with optional filters",
)
async def list_orders(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse ID"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by order status"
    ),
    order_type: str | None = Query(
        None, alias="order_type", description="Filter by order type: asn or sap"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    service = OutboundOrderService(db)
    orders, pagination = service.list_orders(
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        status=status_filter,
        order_type=order_type,
        page=page,
        page_size=page_size,
    )

    # Lightweight list: don't serialize per-order line items. Item counts and
    # stock availability are aggregated with a single query; full line-item
    # detail is fetched on demand via GET /outbound/orders/{order_id}.
    item_counts = _order_item_counts(db, [order.id for order in orders])

    status_counts = service.get_status_counts(
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        order_type=order_type,
    )

    return OutboundOrderListResponse(
        orders=[_order_to_list_item(order, item_counts) for order in orders],
        pagination=pagination,
        status_counts=OutboundOrderStatusCounts(**status_counts),
    )


@router.post(
    "/orders",
    response_model=OutboundOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an outbound order manually",
    description="Create a draft outbound order from an invoice-style payload",
)
async def create_order(
    data: SAPInvoicePayload,
    order_type: str = Query("sap", description="Order type: 'sap' or 'asn'"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    service = OutboundOrderService(db)
    order = service.create_order(
        org_id=current_user.organization_id,
        warehouse_id=data.warehouse_id,
        order_type=order_type,
        invoice_reference=data.invoice_reference,
        items=[
            {
                "item_id": item.item_id,
                "sku": item.sku,
                "quantity": item.quantity,
                "uom": item.uom,
                "per_case_qty": item.per_case_qty,
                "case_qty": item.case_qty,
                "loose_qty": item.loose_qty,
                "batch_no": item.batch_no,
            }
            for item in data.items
        ],
        created_by=current_user.id,
    )
    return _order_to_response(order, db)


@router.get(
    "/orders/{order_id}",
    response_model=OutboundOrderResponse,
    summary="Get outbound order detail",
    description="Get an outbound order with its line items and stock status",
)
async def get_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    order = OutboundOrderService(db).get_order(order_id, current_user.organization_id)
    return _order_to_response(order, db)


@router.post(
    "/orders/{order_id}/confirm",
    response_model=OutboundOrderResponse,
    summary="Confirm an outbound order",
    description="Confirm an outbound order after reviewing line stock availability",
)
async def confirm_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    order = OutboundOrderService(db).confirm_order(
        order_id, current_user.organization_id
    )
    return _order_to_response(order, db)


@router.post(
    "/orders/{order_id}/generate-pick-lists",
    response_model=list[OutboundPickListResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate pick lists from an outbound order",
    description=(
        "Generate one or more pick lists from a confirmed order. Pass worker_ids "
        "to split the order lines into one pick list per worker."
    ),
)
async def generate_pick_lists_from_order(
    order_id: UUID,
    data: CreatePickListFromOrderRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    service = OutboundOrderService(db)
    pick_lists = service.create_pick_lists_from_order(
        order_id=order_id,
        org_id=current_user.organization_id,
        worker_ids=data.worker_ids,
        mode=data.mode,
        exclude_out_of_stock=data.exclude_out_of_stock,
    )
    return [_pick_list_to_response(pl, db) for pl in pick_lists]


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
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse ID"),
    invoice_reference: str | None = Query(
        None, description="Filter by SAP invoice reference"
    ),
    sort_by: str = Query(
        "created_at",
        description="Sort field: created_at, pick_list_no, status, priority",
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

    status_counts = service.get_status_counts(
        organization_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        invoice_reference=invoice_reference,
    )

    # For the list view, we need to fetch full pick list objects to compute progress
    # The service returns dicts from _to_list_item, so we need to get full objects
    from app.models.pick_list import PickList

    # Batch-resolve worker names from the identity database.
    assigned_ids = {
        pl_data.get("assigned_to")
        for pl_data in pick_lists_data
        if pl_data.get("assigned_to")
    }
    worker_name_map = _resolve_worker_names(assigned_ids)

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
            aging = _pick_list_aging(pl, db)
            result_items.append(
                {
                    "id": str(pl.id),
                    "organization_id": str(pl.organization_id),
                    "pick_list_no": pl.pick_list_no,
                    "warehouse_id": str(pl.warehouse_id),
                    "status": pl.status.value if pl.status else "draft",
                    "invoice_reference": pl.invoice_reference,
                    "assigned_to": str(pl.assigned_to) if pl.assigned_to else None,
                    "worker_name": (
                        worker_name_map.get(str(pl.assigned_to)) or str(pl.assigned_to)
                    ) if pl.assigned_to else None,
                    "pick_date": pl.pick_date.isoformat() if pl.pick_date else None,
                    "completed_at": pl.completed_at.isoformat()
                    if pl.completed_at
                    else None,
                    "created_at": pl.created_at.isoformat() if pl.created_at else None,
                    "priority": pl.priority or 0,
                    "dispatch_cutoff": pl.dispatch_cutoff.isoformat()
                    if pl.dispatch_cutoff
                    else None,
                    "wave": pl.wave,
                    "route": pl.route,
                    "age_minutes": aging["age_minutes"],
                    "is_aging": aging["is_aging"],
                    "progress": progress,
                }
            )

    return OutboundPickListListResponse(
        pick_lists=result_items,
        pagination=pagination,
        status_counts=OutboundPickListStatusCounts(**status_counts),
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
    PickListService(db)

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

    return _pick_list_to_response(pl, db)


@router.post(
    "/{pick_list_id}/assign",
    response_model=OutboundPickListResponse,
    summary="Assign or reassign a worker to a pick list",
    description="Assign a warehouse worker to a pick list. Call again to reassign.",
)
async def assign_pick_list_worker(
    pick_list_id: UUID,
    data: AssignWorkerRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Assign (or reassign) a worker to a pick list.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Request Body:**
    - **worker_id**: UUID of the warehouse worker to assign

    **Returns:** Updated pick list with the assigned worker
    """
    service = PickListService(db)

    pick_list = service.assign_worker(
        pick_list_id=pick_list_id,
        worker_id=data.worker_id,
        org_id=current_user.organization_id,
    )

    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/accept",
    response_model=OutboundPickListResponse,
    summary="Accept a pick task",
    description="Record the worker accepting the pick task and start the timer (WF-010)",
)
async def accept_pick_list(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Accept a pick task (WF-010).

    Records ``accepted_at``/``accepted_by`` (idempotent on the first accept)
    and moves a ``draft`` pick list to ``in_progress``.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list to accept

    **Returns:** Updated pick list with the accept timestamp

    Requirements: WF-010
    """
    service = PickListService(db)
    pick_list = service.accept_task(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
        worker_id=current_user.id,
    )
    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/confirm",
    response_model=OutboundPickListResponse,
    summary="Confirm a pick list",
    description="Move a draft pick list to confirmed status",
)
async def confirm_pick_list(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    pick_list = PickListService(db).confirm_pick_list(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
    )
    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/mark-ready",
    response_model=OutboundPickListResponse,
    summary="Mark pick list ready for dispatch",
    description="Move a pick-complete pick list to ready_for_dispatch",
)
async def mark_pick_list_ready(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    pick_list = PickListService(db).transition_status(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
        target=PickListStatus.READY_FOR_DISPATCH,
        allowed_from=(
            PickListStatus.PICK_COMPLETE,
            PickListStatus.COMPLETED,
            PickListStatus.READY_FOR_DISPATCH,
        ),
    )
    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/mark-in-transit",
    response_model=OutboundPickListResponse,
    summary="Mark pick list in transit",
    description="Move a ready-for-dispatch pick list to in_transit",
)
async def mark_pick_list_in_transit(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    pick_list = PickListService(db).transition_status(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
        target=PickListStatus.IN_TRANSIT,
        allowed_from=(
            PickListStatus.READY_FOR_DISPATCH,
            PickListStatus.IN_TRANSIT,
        ),
    )
    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/mark-delivered",
    response_model=OutboundPickListResponse,
    summary="Mark pick list delivered",
    description="Move an in-transit pick list to delivered",
)
async def mark_pick_list_delivered(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    pick_list = PickListService(db).transition_status(
        pick_list_id=pick_list_id,
        org_id=current_user.organization_id,
        target=PickListStatus.DELIVERED,
        allowed_from=(PickListStatus.IN_TRANSIT, PickListStatus.DELIVERED),
    )
    return _pick_list_to_response(pick_list, db)


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
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
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

    **Headers:**
    - **Idempotency-Key** (optional): replay guard. When omitted, a
      deterministic key is derived from the task + scan payload.

    **Returns:** Scan result with updated quantities

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.2; NFR-003, EX-017
    """
    service = PickListService(db)
    idempotency = PickIdempotencyService(db)
    org_id = current_user.organization_id

    key = idempotency_key or PickIdempotencyService.derive_key(
        OPERATION_SCAN,
        pick_list_id,
        f"{data.qr_data}|bin={data.bin_location_id}|reason={data.reason_code}",
    )
    replay = idempotency.get_replay(org_id, OPERATION_SCAN, key)
    if replay is not None:
        return PickScanResult(**replay)

    result = service.record_pick_scan(
        pick_list_id=pick_list_id,
        qr_data=data.qr_data,
        worker_id=current_user.id,
        org_id=org_id,
        bin_location_id=data.bin_location_id,
        reason_code=data.reason_code,
        reason_quantity=data.reason_quantity,
    )

    response = PickScanResult(**result)
    idempotency.record(
        org_id,
        OPERATION_SCAN,
        key,
        pick_list_id,
        PickIdempotencyService.request_hash(
            f"{data.qr_data}|bin={data.bin_location_id}|reason={data.reason_code}"
        ),
        response.model_dump(mode="json"),
    )
    return response


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
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Complete a pick list.

    Validates that all items have been fully picked and transitions
    the pick list status to COMPLETED.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Headers:**
    - **Idempotency-Key** (optional): replay guard. When omitted, a
      deterministic key is derived from the task.

    **Returns:** Updated pick list with completed status

    Requirements: 10.6, 10.7; NFR-003, EX-017
    """
    service = PickListService(db)
    idempotency = PickIdempotencyService(db)
    org_id = current_user.organization_id

    key = idempotency_key or PickIdempotencyService.derive_key(
        OPERATION_COMPLETE, pick_list_id
    )
    replay = idempotency.get_replay(org_id, OPERATION_COMPLETE, key)
    if replay is not None:
        return OutboundPickListResponse(**replay)

    pick_list = service.complete_pick_list(
        pick_list_id=pick_list_id,
        org_id=org_id,
    )

    response = _pick_list_to_response(pick_list, db)
    idempotency.record(
        org_id,
        OPERATION_COMPLETE,
        key,
        pick_list_id,
        None,
        response.model_dump(mode="json"),
    )
    return response


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
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Cancel a pick list.

    Releases any reserved stock back to available inventory and
    transitions the pick list status to CANCELLED.

    **Path Parameters:**
    - **pick_list_id**: UUID of the pick list

    **Headers:**
    - **Idempotency-Key** (optional): replay guard. When omitted, a
      deterministic key is derived from the task.

    **Returns:** Updated pick list with cancelled status

    Requirements: 11.1, 11.5; NFR-003, EX-017
    """
    service = PickListService(db)
    idempotency = PickIdempotencyService(db)
    org_id = current_user.organization_id

    key = idempotency_key or PickIdempotencyService.derive_key(
        OPERATION_CANCEL, pick_list_id
    )
    replay = idempotency.get_replay(org_id, OPERATION_CANCEL, key)
    if replay is not None:
        return OutboundPickListResponse(**replay)

    pick_list = service.cancel_pick_list(
        pick_list_id=pick_list_id,
        org_id=org_id,
    )

    response = _pick_list_to_response(pick_list, db)
    idempotency.record(
        org_id,
        OPERATION_CANCEL,
        key,
        pick_list_id,
        None,
        response.model_dump(mode="json"),
    )
    return response


@router.post(
    "/{pick_list_id}/stage-transfer",
    response_model=OutboundPickListResponse,
    summary="Transfer pick list to a staging lane",
    description="Assign a staging lane and move picked stock to in-transit-to-stage",
)
async def stage_transfer_pick_list(
    pick_list_id: UUID,
    data: StageTransferRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Transfer a pick list to a staging lane (WF-019).

    Validates the staging lane, assigns it to the pick list, and transitions
    the picked bin stock ``picked → in_transit_to_stage``.

    Requirements: WF-019, EX-019/020, ALT-008
    """
    service = PickListService(db)
    pick_list = service.stage_transfer(
        pick_list_id=pick_list_id,
        staging_location_id=data.staging_location_id,
        org_id=current_user.organization_id,
    )
    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/stage-scan",
    response_model=OutboundPickListResponse,
    summary="Validate staging lane scan",
    description="Validate the scanned staging lane and mark the pick list staged",
)
async def stage_scan_pick_list(
    pick_list_id: UUID,
    data: StageScanRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Validate a staging lane scan and mark the pick list staged (WF-020).

    Rejects a wrong staging lane with a hard stop (ALT-008).

    Requirements: WF-020, ALT-008
    """
    service = PickListService(db)
    pick_list = service.stage_scan(
        pick_list_id=pick_list_id,
        staging_location_id=data.staging_location_id,
        org_id=current_user.organization_id,
    )
    return _pick_list_to_response(pick_list, db)


@router.post(
    "/{pick_list_id}/items/{pick_list_item_id}/handling-unit",
    response_model=HandlingUnitAssignmentResponse,
    summary="Associate a handling unit with a pick list item",
    description="Link a trolley/carton/pallet handling unit to a pick line (WF-018)",
)
async def assign_handling_unit(
    pick_list_id: UUID,
    pick_list_item_id: UUID,
    data: AssignHandlingUnitRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Associate a handling unit (trolley/carton/pallet) with a pick list item.

    When ``pick.enable_handling_unit`` is enabled, a handling unit already
    assigned to another pick item is rejected.

    Requirements: WF-018
    """
    service = PickListService(db)
    pick_item = service.assign_handling_unit(
        pick_list_item_id=pick_list_item_id,
        handling_unit_id=data.handling_unit_id,
        org_id=current_user.organization_id,
    )
    return HandlingUnitAssignmentResponse(
        pick_list_item_id=str(pick_item.id),
        handling_unit_id=str(pick_item.handling_unit_id),
    )


@router.patch(
    "/{pick_list_id}/priority",
    response_model=OutboundPickListResponse,
    summary="Set task prioritization fields",
    description="Set manual priority, dispatch cutoff, wave, route, or SLA on a pick list (WF-007)",
)
async def update_pick_list_priority(
    pick_list_id: UUID,
    data: UpdatePriorityRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Set task prioritization fields on a pick list (WF-007).

    Only the supplied (non-null) fields are updated. ``priority`` is the
    manual override (higher = more urgent); ``dispatch_cutoff``/``wave``/
    ``route`` mirror SAP-supplied dispatch data; ``sla_minutes`` overrides
    the org aging threshold for this task (ALT-011).

    Requirements: WF-007, ALT-011
    """
    service = PickListService(db)
    pick_list = service.update_priority(
        pick_list_id=pick_list_id,
        data=data.model_dump(exclude_unset=True),
        org_id=current_user.organization_id,
    )
    return _pick_list_to_response(pick_list, db)

