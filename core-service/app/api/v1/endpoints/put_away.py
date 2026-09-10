"""Put-away API endpoints for managing put-away lists and items.

Handles:
- Generating a put-away list from a receiving slip
- Listing put-away lists with filters (warehouse_id, status, pagination)
- Getting put-away list detail with items
- Completing a put-away item (updates bin stock)
- Skipping a put-away item with reason

Requirements: 8.1, 8.5, 8.6
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.authorization import (
    WAREHOUSE_CREATE,
    WAREHOUSE_READ,
    WAREHOUSE_UPDATE,
    WMS_SCAN,
)
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.schemas.common import PaginationMeta
from app.schemas.put_away import (
    CompletePutAwayItemRequest,
    GeneratePutAwayRequest,
    PutAwayListBatchResponse,
    PutAwayListItemResponse,
    PutAwayListListResponse,
    PutAwayListResponse,
    PutAwayListSummaryResponse,
    PutAwayStatusCounts,
    SkipPutAwayItemRequest,
)
from app.services.put_away_service import PutAwayService

router = APIRouter()


def _extract_warnings(remarks: str | None) -> list[str] | None:
    """Extract warnings list from remarks JSON field. Returns None if no warnings."""
    if not remarks:
        return None
    try:
        data = json.loads(remarks)
        warnings = data.get("warnings")
        return warnings if isinstance(warnings, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _serial_meta_map(db: Session, batch_numbers: set[str]) -> dict[str, dict]:
    """Resolve manufacturing/expiry dates for serial numbers from QSealParameters."""
    meta: dict[str, dict] = {}
    if not batch_numbers:
        return meta
    try:
        from app.models.qseal import QSealParameters

        rows = (
            db.query(
                QSealParameters.serial_number,
                QSealParameters.manufacturing_date,
                QSealParameters.expiry_date,
            )
            .filter(QSealParameters.serial_number.in_(batch_numbers))
            .all()
        )
        for sn, mfg, exp in rows:
            meta[sn] = {
                "manufacturing_date": str(mfg) if mfg else None,
                "expiry_date": str(exp) if exp else None,
            }
    except Exception:
        pass
    return meta


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


def _resolve_worker_name(worker_id: UUID | None) -> str | None:
    """Resolve a human-readable worker name, falling back to the UUID."""
    if not worker_id:
        return None
    return _resolve_worker_names({worker_id}).get(str(worker_id)) or str(worker_id)


def _resolve_references(
    db: Session, pal_ids: list[UUID]
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """Batch-resolve receiving_slip numbers and worker names.

    Returns (slip_no_map, worker_name_map) keyed by put_away_list id.
    """
    from app.models.receiving_slip import ReceivingSlip

    slip_no_map: dict[UUID, str] = {}
    worker_name_map: dict[UUID, str] = {}

    if not pal_ids:
        return slip_no_map, worker_name_map

    # Batch-fetch slip numbers via outerjoin
    rows = (
        db.query(
            PutAwayList.id,
            PutAwayList.receiving_slip_id,
            PutAwayList.assigned_to,
            ReceivingSlip.slip_number,
        )
        .outerjoin(ReceivingSlip, ReceivingSlip.id == PutAwayList.receiving_slip_id)
        .filter(PutAwayList.id.in_(pal_ids))
        .all()
    )

    worker_ids: set[UUID] = set()
    for pal_id, _slip_id, assigned_to, slip_no in rows:
        if slip_no:
            slip_no_map[pal_id] = slip_no
        if assigned_to:
            worker_ids.add(assigned_to)
            worker_name_map[pal_id] = str(assigned_to)  # fallback

    # Resolve human-readable worker names from the identity database.
    if worker_ids:
        name_by_id = _resolve_worker_names(worker_ids)
        for pal_id, _slip_id, assigned_to, _slip_no in rows:
            if assigned_to and str(assigned_to) in name_by_id:
                worker_name_map[pal_id] = name_by_id[str(assigned_to)]

    return slip_no_map, worker_name_map


def _build_item_response(
    item: PutAwayListItem, serial_meta: dict | None = None
) -> PutAwayListItemResponse:
    """Build a PutAwayListItemResponse from a PutAwayListItem model."""
    bin_location_code = None
    if item.bin_location:
        bin_location_code = item.bin_location.full_path or item.bin_location.code

    # Resolve item name from the Item relationship
    item_name = None
    if item.item:
        item_name = item.item.item_name

    meta = (serial_meta or {}).get(item.batch_number) or {}

    return PutAwayListItemResponse(
        id=str(item.id),
        item_id=str(item.item_id),
        sku=item.sku,
        item_name=item_name,
        batch_number=item.batch_number,
        serial_number=item.batch_number,
        manufacturing_date=meta.get("manufacturing_date"),
        expiry_date=meta.get("expiry_date"),
        quantity=float(item.quantity),
        bin_location_id=str(item.bin_location_id) if item.bin_location_id else None,
        bin_location_code=bin_location_code,
        suggested_bin_code=bin_location_code,
        sort_order=item.sort_order or 0,
        status=item.status,
        notes=item.notes,
        completed_at=item.completed_at.isoformat() if item.completed_at else None,
        created_at=item.created_at.isoformat() if item.created_at else None,
    )


def _build_list_response(
    pal: PutAwayList, counts: dict, slip_no_map: dict, worker_name_map: dict
) -> PutAwayListSummaryResponse:
    """Build a PutAwayListSummaryResponse with resolved references."""
    c = counts.get(pal.id, {"total": 0, "completed": 0, "pending": 0})
    return PutAwayListSummaryResponse(
        id=str(pal.id),
        organization_id=str(pal.organization_id),
        warehouse_id=str(pal.warehouse_id),
        put_away_list_no=pal.put_away_list_no,
        status=pal.status,
        reference_type=pal.reference_type,
        reference_id=str(pal.reference_id) if pal.reference_id else None,
        receiving_slip_id=str(pal.receiving_slip_id) if pal.receiving_slip_id else None,
        receiving_slip_no=slip_no_map.get(pal.id),
        remarks=pal.remarks,
        assigned_to=str(pal.assigned_to) if pal.assigned_to else None,
        worker_id=str(pal.assigned_to) if pal.assigned_to else None,
        worker_name=worker_name_map.get(pal.id),
        total_items=c["total"],
        completed_items=c["completed"],
        pending_items=c["pending"],
        completed_at=pal.completed_at.isoformat() if pal.completed_at else None,
        created_at=pal.created_at.isoformat() if pal.created_at else None,
        updated_at=pal.updated_at.isoformat() if pal.updated_at else None,
    )


def _build_response(db: Session, put_away_list: PutAwayList) -> PutAwayListResponse:
    """Build a PutAwayListResponse with resolved item/bin details."""
    serial_meta = _serial_meta_map(
        db, {it.batch_number for it in put_away_list.items if it.batch_number}
    )
    item_responses = [
        _build_item_response(item, serial_meta) for item in put_away_list.items
    ]
    item_responses.sort(key=lambda x: x.sort_order)

    total_qty = sum(int(it.quantity) for it in put_away_list.items)
    completed_qty = sum(
        int(it.quantity) for it in put_away_list.items if it.status == "completed"
    )
    pending_qty = sum(
        int(it.quantity) for it in put_away_list.items if it.status == "pending"
    )

    slip_no = None
    if put_away_list.receiving_slip and put_away_list.receiving_slip.slip_number:
        slip_no = put_away_list.receiving_slip.slip_number

    return PutAwayListResponse(
        id=str(put_away_list.id),
        organization_id=str(put_away_list.organization_id),
        warehouse_id=str(put_away_list.warehouse_id),
        put_away_list_no=put_away_list.put_away_list_no,
        status=put_away_list.status,
        reference_type=put_away_list.reference_type,
        reference_id=str(put_away_list.reference_id)
        if put_away_list.reference_id
        else None,
        receiving_slip_id=str(put_away_list.receiving_slip_id)
        if put_away_list.receiving_slip_id
        else None,
        receiving_slip_no=slip_no,
        total_items=total_qty,
        completed_items=completed_qty,
        pending_items=pending_qty,
        remarks=put_away_list.remarks,
        warnings=_extract_warnings(put_away_list.remarks),
        assigned_to=str(put_away_list.assigned_to)
        if put_away_list.assigned_to
        else None,
        worker_id=str(put_away_list.assigned_to) if put_away_list.assigned_to else None,
        worker_name=_resolve_worker_name(put_away_list.assigned_to),
        completed_at=put_away_list.completed_at.isoformat()
        if put_away_list.completed_at
        else None,
        created_at=put_away_list.created_at.isoformat()
        if put_away_list.created_at
        else None,
        updated_at=put_away_list.updated_at.isoformat()
        if put_away_list.updated_at
        else None,
        items=item_responses,
    )


@router.post(
    "/generate-from-slip/{slip_id}",
    response_model=PutAwayListResponse | PutAwayListBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate put-away list from receiving slip",
    description=(
        "Generate one or more put-away lists with bin assignments from an "
        "approved receiving slip. Pass ``worker_ids`` to split the work into "
        "one list per worker."
    ),
)
async def generate_put_away_from_slip(
    slip_id: UUID,
    data: GeneratePutAwayRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Generate a put-away list from an approved receiving slip.

    The receiving slip must be in `pending_putaway` status. This endpoint
    creates a PutAwayList with items assigned to bins respecting location
    allocations (exclusive → preferred → unallocated), runs volumetric
    optimization, sorts by optimal traversal order, and optionally assigns
    a worker task.

    **Path Parameters:**
    - **slip_id**: UUID of the receiving slip (must be pending_putaway)

    **Request Body (optional):**
    - **worker_id**: Optional UUID of the worker to assign the put-away task to

    **Returns:** The created PutAwayList with items assigned to bins

    Requirements: 8.1, 8.2, 8.3, 8.4, 20.3, 20.4, 20.5, 20.6
    """
    worker_id = data.worker_id if data else None
    worker_ids = data.worker_ids if data else None
    mode = data.mode if data else None
    service = PutAwayService(db)

    if worker_ids:
        lists = service.generate_from_slip_for_workers(
            slip_id=slip_id,
            org_id=current_user.organization_id,
            worker_ids=worker_ids,
            mode=mode,
        )
        return PutAwayListBatchResponse(
            put_away_lists=[_build_response(db, pal) for pal in lists]
        )

    put_away_list = service.generate_from_slip(
        slip_id=slip_id,
        org_id=current_user.organization_id,
        worker_id=worker_id,
        mode=mode,
    )
    return _build_response(db, put_away_list)


@router.get(
    "",
    response_model=PutAwayListListResponse,
    summary="List put-away lists",
    description="List put-away lists with optional filters for warehouse, status, and pagination",
)
async def list_put_away_lists(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse ID"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (pending, completed)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List put-away lists with filters.

    **Query Parameters:**
    - **warehouse_id**: Optional UUID to filter by warehouse
    - **status**: Optional status filter (pending, completed)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)

    **Returns:** Paginated list of put-away lists with summary info

    Requirements: 8.5
    """
    query = db.query(PutAwayList).filter(
        PutAwayList.organization_id == current_user.organization_id
    )

    if warehouse_id:
        query = query.filter(PutAwayList.warehouse_id == warehouse_id)

    if status_filter:
        query = query.filter(PutAwayList.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size
    put_away_lists = (
        query.order_by(PutAwayList.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Build summary responses — aggregate item quantities and counts
    pal_ids = [pal.id for pal in put_away_lists]
    item_counts = {}
    if pal_ids:
        # Per-status row counts (completed_items, pending_items)
        status_rows = (
            db.query(
                PutAwayListItem.put_away_list_id,
                PutAwayListItem.status,
                func.count(PutAwayListItem.id),
            )
            .filter(PutAwayListItem.put_away_list_id.in_(pal_ids))
            .group_by(PutAwayListItem.put_away_list_id, PutAwayListItem.status)
            .all()
        )
        for list_id, status, cnt in status_rows:
            item_counts.setdefault(list_id, {"total": 0, "completed": 0, "pending": 0})
            item_counts[list_id][status] = cnt

        # Total quantity (sum of all item quantities)
        qty_rows = (
            db.query(
                PutAwayListItem.put_away_list_id,
                func.sum(PutAwayListItem.quantity),
            )
            .filter(PutAwayListItem.put_away_list_id.in_(pal_ids))
            .group_by(PutAwayListItem.put_away_list_id)
            .all()
        )
        for list_id, total_qty in qty_rows:
            if list_id not in item_counts:
                item_counts[list_id] = {"total": 0, "completed": 0, "pending": 0}
            item_counts[list_id]["total"] = int(total_qty) if total_qty else 0

    # Resolve receiving slip numbers and worker names
    slip_no_map, worker_name_map = _resolve_references(db, pal_ids)

    summaries = [
        _build_list_response(pal, item_counts, slip_no_map, worker_name_map)
        for pal in put_away_lists
    ]

    # Status distribution scoped to the same warehouse filter, but not the
    # status filter itself, so every bucket is always populated.
    counts_query = db.query(PutAwayList.status, func.count(PutAwayList.id)).filter(
        PutAwayList.organization_id == current_user.organization_id
    )
    if warehouse_id:
        counts_query = counts_query.filter(PutAwayList.warehouse_id == warehouse_id)
    counts_raw = {
        "total": 0,
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
    }
    for status_value, count in counts_query.group_by(PutAwayList.status).all():
        key = str(status_value)
        if key in counts_raw:
            counts_raw[key] = count
        counts_raw["total"] += count

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return PutAwayListListResponse(
        put_away_lists=summaries,
        pagination=pagination,
        status_counts=PutAwayStatusCounts(**counts_raw),
    )


@router.get(
    "/{put_away_list_id}",
    response_model=PutAwayListResponse,
    summary="Get put-away list detail",
    description="Get a put-away list with all its items",
)
async def get_put_away_list(
    put_away_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get put-away list detail with items.

    **Path Parameters:**
    - **put_away_list_id**: UUID of the put-away list

    **Returns:** Put-away list details with all items including bin location info

    Requirements: 8.5
    """
    put_away_list = (
        db.query(PutAwayList)
        .filter(
            PutAwayList.id == put_away_list_id,
            PutAwayList.organization_id == current_user.organization_id,
        )
        .first()
    )

    if put_away_list is None:
        raise NotFoundError(
            message="Put-away list not found",
            entity_type="PutAwayList",
            entity_id=str(put_away_list_id),
        )

    return _build_response(db, put_away_list)


@router.post(
    "/{put_away_list_id}/items/{item_id}/complete",
    response_model=PutAwayListItemResponse,
    summary="Complete a put-away item",
    description="Mark a put-away item as completed, updating bin stock",
)
async def complete_put_away_item(
    put_away_list_id: UUID,
    item_id: UUID,
    data: CompletePutAwayItemRequest = CompletePutAwayItemRequest(),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE, WMS_SCAN)),
    db: Session = Depends(get_db),
):
    """
    Complete a put-away item.

    Marks the item as COMPLETED, adds stock to the specified or
    pre-assigned bin, and triggers capacity rollup. When all items
    are done, the put-away list and receiving slip statuses are updated.

    **Path Parameters:**
    - **put_away_list_id**: UUID of the put-away list
    - **item_id**: UUID of the put-away list item to complete

    **Request Body (optional):**
    - **bin_id**: Override bin location ID for put-away. When omitted,
      the pre-assigned bin from the put-away item is used.

    **Returns:** Updated put-away list item

    Requirements: 8.5, 8.6
    """
    # Validate the item belongs to the specified put-away list
    put_away_item = (
        db.query(PutAwayListItem)
        .filter(
            PutAwayListItem.id == item_id,
            PutAwayListItem.put_away_list_id == put_away_list_id,
            PutAwayListItem.organization_id == current_user.organization_id,
        )
        .first()
    )

    if put_away_item is None:
        raise NotFoundError(
            message="Put-away list item not found",
            entity_type="PutAwayListItem",
            entity_id=str(item_id),
        )

    service = PutAwayService(db)
    completed_item = service.complete_item(
        put_away_item_id=item_id,
        worker_id=current_user.id,
        org_id=current_user.organization_id,
        bin_id_override=data.bin_id,
    )

    bin_location_code = None
    if completed_item.bin_location:
        bin_location_code = (
            completed_item.bin_location.full_path or completed_item.bin_location.code
        )

    return PutAwayListItemResponse(
        id=str(completed_item.id),
        item_id=str(completed_item.item_id),
        sku=completed_item.sku,
        batch_number=completed_item.batch_number,
        quantity=float(completed_item.quantity),
        bin_location_id=str(completed_item.bin_location_id)
        if completed_item.bin_location_id
        else None,
        bin_location_code=bin_location_code,
        sort_order=completed_item.sort_order or 0,
        status=completed_item.status,
        notes=completed_item.notes,
        completed_at=completed_item.completed_at.isoformat()
        if completed_item.completed_at
        else None,
        created_at=completed_item.created_at.isoformat()
        if completed_item.created_at
        else None,
    )


@router.post(
    "/{put_away_list_id}/items/{item_id}/skip",
    response_model=PutAwayListItemResponse,
    summary="Skip a put-away item",
    description="Skip a put-away item with a reason",
)
async def skip_put_away_item(
    put_away_list_id: UUID,
    item_id: UUID,
    data: SkipPutAwayItemRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE, WMS_SCAN)),
    db: Session = Depends(get_db),
):
    """
    Skip a put-away item with a reason.

    Marks the item as SKIPPED with the provided reason.
    When all items are done (completed or skipped), the
    put-away list and receiving slip statuses are updated.

    **Path Parameters:**
    - **put_away_list_id**: UUID of the put-away list
    - **item_id**: UUID of the put-away list item to skip

    **Request Body:**
    - **reason**: Reason for skipping the item

    **Returns:** Updated put-away list item

    Requirements: 8.5, 8.6
    """
    # Validate the item belongs to the specified put-away list
    put_away_item = (
        db.query(PutAwayListItem)
        .filter(
            PutAwayListItem.id == item_id,
            PutAwayListItem.put_away_list_id == put_away_list_id,
            PutAwayListItem.organization_id == current_user.organization_id,
        )
        .first()
    )

    if put_away_item is None:
        raise NotFoundError(
            message="Put-away list item not found",
            entity_type="PutAwayListItem",
            entity_id=str(item_id),
        )

    service = PutAwayService(db)
    skipped_item = service.skip_item(
        put_away_item_id=item_id,
        reason=data.reason,
        org_id=current_user.organization_id,
    )

    bin_location_code = None
    if skipped_item.bin_location:
        bin_location_code = (
            skipped_item.bin_location.full_path or skipped_item.bin_location.code
        )

    return PutAwayListItemResponse(
        id=str(skipped_item.id),
        item_id=str(skipped_item.item_id),
        sku=skipped_item.sku,
        batch_number=skipped_item.batch_number,
        quantity=float(skipped_item.quantity),
        bin_location_id=str(skipped_item.bin_location_id)
        if skipped_item.bin_location_id
        else None,
        bin_location_code=bin_location_code,
        sort_order=skipped_item.sort_order or 0,
        status=skipped_item.status,
        notes=skipped_item.notes,
        completed_at=skipped_item.completed_at.isoformat()
        if skipped_item.completed_at
        else None,
        created_at=skipped_item.created_at.isoformat()
        if skipped_item.created_at
        else None,
    )
