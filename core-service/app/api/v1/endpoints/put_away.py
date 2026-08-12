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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_CREATE, WAREHOUSE_READ
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.schemas.common import PaginationMeta
from app.schemas.put_away import (
    CompletePutAwayItemRequest,
    CompletePutawayByQrRequest,
    GeneratePutAwayRequest,
    PutAwayListItemResponse,
    PutAwayListListResponse,
    PutAwayListResponse,
    PutAwayListSummaryResponse,
    SkipPutAwayItemRequest,
    TrackingItemResponse,
    CompletePutawayResponse,
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


@router.post(
    "/generate-from-slip/{slip_id}",
    response_model=PutAwayListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate put-away list from receiving slip",
    description="Generate a put-away list with bin assignments from an approved receiving slip",
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
    service = PutAwayService(db)
    put_away_list = service.generate_from_slip(
        slip_id=slip_id,
        org_id=current_user.organization_id,
        worker_id=worker_id,
    )

    # Build item responses with bin location codes
    item_responses = []
    for item in put_away_list.items:
        bin_location_code = None
        if item.bin_location:
            bin_location_code = item.bin_location.full_path or item.bin_location.code

        item_responses.append(
            PutAwayListItemResponse(
                id=str(item.id),
                item_id=str(item.item_id),
                sku=item.sku,
                batch_number=item.batch_number,
                quantity=float(item.quantity),
                bin_location_id=str(item.bin_location_id)
                if item.bin_location_id
                else None,
                bin_location_code=bin_location_code,
                sort_order=item.sort_order or 0,
                status=item.status,
                notes=item.notes,
                completed_at=item.completed_at.isoformat()
                if item.completed_at
                else None,
                created_at=item.created_at.isoformat() if item.created_at else None,
            )
        )

    item_responses.sort(key=lambda x: x.sort_order)

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
        remarks=put_away_list.remarks,
        warnings=_extract_warnings(put_away_list.remarks),
        assigned_to=str(put_away_list.assigned_to)
        if put_away_list.assigned_to
        else None,
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

    # Build summary responses — single aggregation query instead of N+1
    pal_ids = [pal.id for pal in put_away_lists]
    item_counts = {}
    if pal_ids:
        rows = (
            db.query(
                PutAwayListItem.put_away_list_id,
                PutAwayListItem.status,
                func.count(PutAwayListItem.id),
            )
            .filter(PutAwayListItem.put_away_list_id.in_(pal_ids))
            .group_by(PutAwayListItem.put_away_list_id, PutAwayListItem.status)
            .all()
        )
        for list_id, status, cnt in rows:
            item_counts.setdefault(list_id, {"total": 0, "completed": 0, "pending": 0})
            item_counts[list_id][status] = cnt
            item_counts[list_id]["total"] += cnt

    summaries = []
    for pal in put_away_lists:
        counts = item_counts.get(pal.id, {"total": 0, "completed": 0, "pending": 0})

        summaries.append(
            PutAwayListSummaryResponse(
                id=str(pal.id),
                organization_id=str(pal.organization_id),
                warehouse_id=str(pal.warehouse_id),
                put_away_list_no=pal.put_away_list_no,
                status=pal.status,
                reference_type=pal.reference_type,
                reference_id=str(pal.reference_id) if pal.reference_id else None,
                receiving_slip_id=str(pal.receiving_slip_id)
                if pal.receiving_slip_id
                else None,
                remarks=pal.remarks,
                assigned_to=str(pal.assigned_to) if pal.assigned_to else None,
                total_items=counts["total"],
                completed_items=counts["completed"],
                pending_items=counts["pending"],
                completed_at=pal.completed_at.isoformat() if pal.completed_at else None,
                created_at=pal.created_at.isoformat() if pal.created_at else None,
                updated_at=pal.updated_at.isoformat() if pal.updated_at else None,
            )
        )

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
    )


@router.get(
    "/available",
    summary="List items available for put-away",
    description="Returns scanned items that are pending put-away (not yet binned, not rejected)",
)
async def list_available_for_putaway(
    warehouse_id: UUID = Query(..., description="Warehouse ID"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Items scanned on the dock, ready for put-away."""
    from app.services.scanned_item_tracking_service import (
        ScannedItemTrackingService,
    )

    svc = ScannedItemTrackingService(db)
    items = svc.get_available_for_putaway(warehouse_id)

    return {
        "items": [
            {
                "qr_identifier": i.qr_identifier,
                "sku": i.sku,
                "item_id": str(i.item_id),
                "batch_number": i.batch_number,
                "quantity": i.quantity,
                "receiving_status": i.receiving_status,
                "scanned_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
        "total": len(items),
    }


@router.post(
    "/direct",
    status_code=status.HTTP_200_OK,
    summary="Direct put-away by QR scan",
    description="Worker scans a QR and puts item directly in a bin — no put-away list needed.",
)
async def direct_putaway(
    body: dict,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Direct put-away: Worker B scans a QR code and puts the item directly in a bin.
    This enables the parallel receiving/put-away workflow.

    Request body:
        qr_identifier: The scanned QR code (required)
        bin_location_id: Target bin UUID (required)

    Returns the updated tracking record.
    """
    from app.services.scanned_item_tracking_service import (
        ScannedItemTrackingService,
    )

    qr = body.get("qr_identifier")
    bin_id = body.get("bin_location_id")

    if not qr:
        raise HTTPException(status_code=400, detail="qr_identifier is required")
    if not bin_id:
        raise HTTPException(status_code=400, detail="bin_location_id is required")

    svc = ScannedItemTrackingService(db)

    # Gate: is this item ready for put-away?
    ok, err = svc.can_put_away(qr)
    if not ok:
        raise HTTPException(status_code=409, detail=err)

    try:
        tracking = svc.complete_putaway(
            qr_identifier=qr,
            bin_location_id=UUID(bin_id),
            putaway_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        "qr_identifier": tracking.qr_identifier,
        "sku": tracking.sku,
        "bin_location_id": str(tracking.bin_location_id),
        "putaway_status": tracking.putaway_status,
        "receiving_status": tracking.receiving_status,
        "stock_entered": tracking.stock_entered,
        "putaway_at": tracking.putaway_at.isoformat() if tracking.putaway_at else None,
    }


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

    # Build item responses with bin location codes
    item_responses = []
    for item in put_away_list.items:
        bin_location_code = None
        if item.bin_location:
            bin_location_code = item.bin_location.full_path or item.bin_location.code

        item_responses.append(
            PutAwayListItemResponse(
                id=str(item.id),
                item_id=str(item.item_id),
                sku=item.sku,
                batch_number=item.batch_number,
                quantity=float(item.quantity),
                bin_location_id=str(item.bin_location_id)
                if item.bin_location_id
                else None,
                bin_location_code=bin_location_code,
                sort_order=item.sort_order or 0,
                status=item.status,
                notes=item.notes,
                completed_at=item.completed_at.isoformat()
                if item.completed_at
                else None,
                created_at=item.created_at.isoformat() if item.created_at else None,
            )
        )

    # Sort items by sort_order
    item_responses.sort(key=lambda x: x.sort_order)

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
        remarks=put_away_list.remarks,
        warnings=_extract_warnings(put_away_list.remarks),
        assigned_to=str(put_away_list.assigned_to)
        if put_away_list.assigned_to
        else None,
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
    "/{put_away_list_id}/items/{item_id}/complete",
    response_model=PutAwayListItemResponse,
    summary="Complete a put-away item",
    description="Mark a put-away item as completed, updating bin stock",
)
async def complete_put_away_item(
    put_away_list_id: UUID,
    item_id: UUID,
    data: CompletePutAwayItemRequest = CompletePutAwayItemRequest(),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
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
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
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


# ================================================================
# DUAL-AXIS: QR-based Put-Away (no slip/list context needed)
# ================================================================


@router.post(
    "/complete",
    summary="Complete put-away by QR (dual-axis)",
    description="Worker scans the same QR from inbound, enters bin, completes put-away",
)
async def complete_putaway_by_qr(
    data: "CompletePutawayByQrRequest",
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """Complete put-away for a tracked item by scanning its QR code."""
    from app.schemas.put_away import CompletePutawayByQrRequest, CompletePutawayResponse
    from app.services.scanned_item_tracking_service import ScannedItemTrackingService

    svc = ScannedItemTrackingService(db)
    try:
        tracking = svc.complete_putaway(
            qr_identifier=data.qr,
            bin_location_id=data.bin_id,
            putaway_by=current_user.id,
        )
        return CompletePutawayResponse(
            id=str(tracking.id),
            qr_identifier=tracking.qr_identifier,
            sku=tracking.sku,
            batch_number=tracking.batch_number,
            quantity=tracking.quantity,
            bin_location_id=str(tracking.bin_location_id)
            if tracking.bin_location_id
            else None,
            putaway_status=tracking.putaway_status,
            stock_entered=tracking.stock_entered,
            completed_at=tracking.putaway_at.isoformat()
            if tracking.putaway_at
            else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/available",
    summary="List items available for put-away",
    description="Returns scanned items with putaway_status='pending' and not rejected",
)
async def list_available_for_putaway(
    warehouse_id: UUID = Query(..., description="Warehouse UUID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """List items pending put-away in a warehouse."""
    from app.schemas.put_away import TrackingItemResponse
    from app.services.scanned_item_tracking_service import ScannedItemTrackingService

    svc = ScannedItemTrackingService(db)
    items = svc.get_available_for_putaway(warehouse_id)

    # Simple pagination
    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]

    result = [
        TrackingItemResponse(
            id=str(t.id),
            qr_identifier=t.qr_identifier,
            sku=t.sku,
            batch_number=t.batch_number,
            quantity=t.quantity,
            receiving_status=t.receiving_status,
            putaway_status=t.putaway_status,
            bin_location_id=str(t.bin_location_id) if t.bin_location_id else None,
            stock_entered=t.stock_entered,
            rejection_reason=t.rejection_reason,
            created_at=t.created_at.isoformat() if t.created_at else None,
            updated_at=t.updated_at.isoformat() if t.updated_at else None,
        )
        for t in page_items
    ]

    return {
        "put_away_items": result,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "has_next": start + page_size < total,
            "has_prev": page > 1,
        },
    }


@router.get(
    "/lookup/{qr}",
    summary="Lookup tracking by QR code",
    description="Find a scanned_item_tracking row by QR identifier for put-away",
)
async def lookup_tracking_by_qr(
    qr: str,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Look up a tracking record by its QR identifier."""
    from app.models.scanned_item_tracking import ScannedItemTracking
    from app.schemas.put_away import TrackingItemResponse

    tracking = (
        db.query(ScannedItemTracking)
        .filter(ScannedItemTracking.qr_identifier == qr)
        .first()
    )

    if not tracking:
        raise HTTPException(
            status_code=404, detail="QR not found in any inbound session"
        )

    return TrackingItemResponse(
        id=str(tracking.id),
        qr_identifier=tracking.qr_identifier,
        sku=tracking.sku,
        batch_number=tracking.batch_number,
        quantity=tracking.quantity,
        receiving_status=tracking.receiving_status,
        putaway_status=tracking.putaway_status,
        bin_location_id=str(tracking.bin_location_id)
        if tracking.bin_location_id
        else None,
        stock_entered=tracking.stock_entered,
        rejection_reason=tracking.rejection_reason,
        created_at=tracking.created_at.isoformat() if tracking.created_at else None,
        updated_at=tracking.updated_at.isoformat() if tracking.updated_at else None,
    )
