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

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    INBOUND_EXCEPTION_CREATE,
    INBOUND_EXCEPTION_DISPOSE,
    INBOUND_EXCEPTION_READ,
    RECEIVING_SLIP_CREATE,
    WAREHOUSE_READ,
    WAREHOUSE_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.inbound import (
    ApproveSlipRequest,
    AssignBinRequest,
    AssignBinResponse,
    BulkItemStatusUpdateRequest,
    EndSessionRequest,
    FlaggedItemResponse,
    FlagLineItemRequest,
    InboundExceptionClassifyRequest,
    InboundExceptionDispositionRequest,
    InboundExceptionReasonResponse,
    InboundExceptionResponse,
    InboundShortBalanceResponse,
    LinkAsnToSessionRequest,
    ReceivingSlipListResponse,
    ReceivingSlipResponse,
    RecordScanRequest,
    RejectedItemResponse,
    RejectSlipItemRequest,
    RejectSlipRequest,
    RemoveScansRequest,
    RemoveScansResponse,
    ResolveFloatingItemRequest,
    ScanResult,
    SessionResponse,
    SessionSummary,
    StartSessionWithAsnRequest,
)
from app.services.inbound_exception_service import InboundExceptionService
from app.services.inbound_service import InboundService
from app.services.inbound_short_balance_service import InboundShortBalanceService

router = APIRouter()


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start inbound scan session",
    description="Start a new inbound scan session for a dock worker",
)
async def start_session(
    data: StartSessionWithAsnRequest,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Start a new inbound scan session.

    Creates a scan session with status OPEN for the current worker.

    **Request Body:**
    - **warehouse_id**: Warehouse UUID where receiving occurs
    - **dock_location**: Optional dock location identifier
    - **asn_order_id**: Optional ASN order UUID to link the session to

    **Returns:** Created scan session details

    Requirements: 5.1
    """
    service = InboundService(db)
    result = service.start_session(
        worker_id=current_user.id,
        organization_id=current_user.organization_id,
        warehouse_id=data.warehouse_id,
        dock_location=data.dock_location,
        asn_order_id=data.asn_order_id,
    )
    return SessionResponse(**result)


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=SessionResponse,
    summary="Cancel inbound scan session",
    description="Cancel an open scan session without generating a receiving slip",
)
async def cancel_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Cancel an open inbound scan session.

    Discards any scanned items and releases the linked ASN so a fresh
    session can be started. No receiving slip is generated.

    **Path Parameters:**
    - **session_id**: UUID of the open scan session to cancel

    **Returns:** Cancelled session details
    """
    service = InboundService(db)
    result = service.cancel_session(
        session_id=session_id,
        organization_id=current_user.organization_id,
    )
    return SessionResponse(**result)


@router.post(
    "/sessions/{session_id}/remove-scan",
    response_model=RemoveScansResponse,
    summary="Remove scanned items",
    description="Remove one or more scanned items from an open session (e.g. a wrong parent QR)",
)
async def remove_scans(
    session_id: UUID,
    data: RemoveScansRequest,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Remove previously scanned items from an open session.

    Deletes the matching ScanSessionItem rows plus their dual-axis tracking
    and exception records, reversing any HOLD stock they entered.

    **Path Parameters:**
    - **session_id**: UUID of the open scan session

    **Request Body:**
    - **qr_identifiers**: Serial numbers (QR identifiers) of the items to remove
    """
    service = InboundService(db)
    result = service.remove_scan_items(
        session_id=session_id,
        organization_id=current_user.organization_id,
        qr_identifiers=data.qr_identifiers,
    )
    return RemoveScansResponse(**result)


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
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
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
    import logging

    logging.getLogger(__name__).warning(
        "SCAN DEBUG qr_data=%r len=%d", data.qr_data, len(data.qr_data)
    )
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
    data: EndSessionRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """
    End a scan session and generate a receiving slip.

    Closes the session and generates a receiving slip from the scanned items,
    grouped by SKU and batch number. Any rejections supplied in the request
    body are applied before the slip is finalized.

    **Path Parameters:**
    - **session_id**: UUID of the scan session to close

    **Returns:** Generated receiving slip details

    Requirements: 5.5, 6.1
    """
    service = InboundService(db)
    rejections = (
        [r.model_dump() for r in data.rejections] if data and data.rejections else None
    )
    exceptions = (
        [e.model_dump() for e in data.exceptions] if data and data.exceptions else None
    )
    result = service.end_session(
        session_id=session_id,
        worker_id=current_user.id,
        organization_id=current_user.organization_id,
        rejections=rejections,
        exceptions=exceptions,
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
    "/receiving-slips",
    response_model=ReceivingSlipListResponse,
    summary="List receiving slips",
    description="List receiving slips with optional filters for warehouse, session, and status",
)
async def list_receiving_slips(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse UUID"),
    session_id: UUID | None = Query(None, description="Filter by scan session UUID"),
    status: str | None = Query(
        None,
        description="Filter by status: pending_review, pending_putaway, putaway_complete, rejected",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List receiving slips with optional filters.

    **Query Parameters:**
    - **warehouse_id**: Filter by warehouse UUID
    - **session_id**: Filter by scan session UUID
    - **status**: Filter by status (pending_review, pending_putaway, putaway_complete, rejected)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20)

    **Returns:** Paginated list of receiving slips with line items
    """
    from app.schemas.inbound import ReceivingSlipPagination

    service = InboundService(db)
    filters: dict = {}
    if warehouse_id:
        filters["warehouse_id"] = warehouse_id
    if session_id:
        filters["session_id"] = session_id
    if status:
        filters["status"] = status

    slips, total = service.slip_repo.list_slips(
        org_id=current_user.organization_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    slip_responses = [
        ReceivingSlipResponse(**service._slip_to_dict(slip)) for slip in slips
    ]

    return ReceivingSlipListResponse(
        receiving_slips=slip_responses,
        pagination=ReceivingSlipPagination(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


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


# ------------------------------------------------------------------
# Inbound exception & hold / quarantine framework
# ------------------------------------------------------------------


@router.get(
    "/exception-reasons",
    response_model=list[InboundExceptionReasonResponse],
    summary="List inbound exception reason codes",
)
async def list_exception_reasons(
    current_user: CurrentUser = Depends(require_permission(INBOUND_EXCEPTION_READ)),
    db: Session = Depends(get_db),
):
    service = InboundExceptionService(db)
    return [
        InboundExceptionReasonResponse(
            code=reason.code,
            name=reason.name,
            category=reason.category,
            default_destination=reason.default_destination,
            requires_approval=reason.requires_approval,
        )
        for reason in service.list_reasons(current_user.organization_id)
    ]


@router.post(
    "/receiving-slips/{slip_id}/items/{item_id}/exception",
    response_model=InboundExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Classify inbound exception",
)
async def classify_inbound_exception(
    slip_id: UUID,
    item_id: UUID,
    data: InboundExceptionClassifyRequest,
    current_user: CurrentUser = Depends(require_permission(INBOUND_EXCEPTION_CREATE)),
    db: Session = Depends(get_db),
):
    service = InboundExceptionService(db)
    exception = service.classify_slip_item(
        slip_id=slip_id,
        slip_item_id=item_id,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        classification=data.classification,
        reason_code=data.reason_code,
        destination=data.destination,
        note=data.note,
    )
    return InboundExceptionResponse(**service.serialize(exception))


@router.get(
    "/exceptions",
    response_model=list[InboundExceptionResponse],
    summary="List inbound exception and hold/quarantine queue",
)
async def list_inbound_exceptions(
    warehouse_id: UUID | None = Query(None),
    destination: str | None = Query(None),
    exception_status: str | None = Query(None, alias="status"),
    current_user: CurrentUser = Depends(require_permission(INBOUND_EXCEPTION_READ)),
    db: Session = Depends(get_db),
):
    service = InboundExceptionService(db)
    return [
        InboundExceptionResponse(**service.serialize(exception))
        for exception in service.list_exceptions(
            current_user.organization_id,
            warehouse_id=warehouse_id,
            destination=destination,
            status=exception_status,
        )
    ]


@router.get(
    "/asn-orders/{asn_order_id}/short-balances",
    response_model=list[InboundShortBalanceResponse],
    summary="List current ASN short balances linked to receiving slips",
)
async def list_inbound_short_balances(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    balances = InboundShortBalanceService(db).list_for_asn(
        asn_order_id, current_user.organization_id
    )
    return [
        InboundShortBalanceResponse(
            id=str(balance.id),
            asn_order_id=str(balance.asn_order_id),
            asn_order_item_id=str(balance.asn_order_item_id),
            receiving_slip_id=str(balance.receiving_slip_id)
            if balance.receiving_slip_id
            else None,
            item_id=str(balance.item_id) if balance.item_id else None,
            sku=balance.sku,
            expected_qty=float(balance.expected_qty),
            received_qty=float(balance.received_qty),
            short_qty=float(balance.short_qty),
            status=balance.status,
            updated_at=balance.updated_at.isoformat() if balance.updated_at else None,
        )
        for balance in balances
    ]


@router.post(
    "/exceptions/{exception_id}/evidence",
    response_model=InboundExceptionResponse,
    summary="Upload optional inbound exception photo or evidence",
)
async def upload_inbound_exception_evidence(
    exception_id: UUID,
    file: UploadFile = File(
        ..., description="JPEG, PNG, WEBP, or PDF evidence (max 10 MB)"
    ),
    current_user: CurrentUser = Depends(require_permission(INBOUND_EXCEPTION_CREATE)),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    service = InboundExceptionService(db)
    service.add_evidence(
        exception_id=exception_id,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        filename=file.filename or "evidence",
        content_type=file.content_type or "application/octet-stream",
        data=contents,
    )
    exception = service.get_exception(exception_id, current_user.organization_id)
    return InboundExceptionResponse(**service.serialize(exception))


@router.post(
    "/exceptions/{exception_id}/disposition",
    response_model=InboundExceptionResponse,
    summary="Manager disposition for held or quarantined inbound stock",
)
async def dispose_inbound_exception(
    exception_id: UUID,
    data: InboundExceptionDispositionRequest,
    current_user: CurrentUser = Depends(require_permission(INBOUND_EXCEPTION_DISPOSE)),
    db: Session = Depends(get_db),
):
    service = InboundExceptionService(db)
    exception = service.get_exception(exception_id, current_user.organization_id)
    service.assert_manager(current_user, exception.warehouse_id)
    exception = service.dispose(
        exception_id=exception_id,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action=data.action,
        note=data.note,
        item_id=data.item_id,
    )
    return InboundExceptionResponse(**service.serialize(exception))


# ------------------------------------------------------------------
# Two-Step Inbound: Assign Bin (Phase 2)
# ------------------------------------------------------------------


@router.post(
    "/receiving-slips/{slip_id}/items/{item_id}/assign-bin",
    response_model=AssignBinResponse,
    summary="Assign bin to receiving slip item",
    description="Worker scans bin QR and assigns it to a receiving slip item. Adds stock to bin.",
)
async def assign_bin_to_slip_item(
    slip_id: UUID,
    item_id: UUID,
    body: AssignBinRequest,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """Two-step inbound: assign a bin to a receiving slip item and add stock.

    Called after the worker scans a bin QR during put-away.
    Adds stock to the bin and updates the slip item's put-away status.
    When all items on a slip are put away, the slip auto-completes.
    """
    from datetime import UTC, datetime

    from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem
    from app.models.warehouse_location import WarehouseLocation
    from app.services.bin_stock_service import BinStockService

    # Find the slip item
    item = (
        db.query(ReceivingSlipItem)
        .filter(
            ReceivingSlipItem.id == item_id,
            ReceivingSlipItem.slip_id == slip_id,
            ReceivingSlipItem.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Slip item not found"
        )

    if item.put_away_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already assigned to a bin",
        )

    # Validate bin
    bin_location = (
        db.query(WarehouseLocation)
        .filter(
            WarehouseLocation.id == body.bin_location_id,
            WarehouseLocation.organization_id == current_user.organization_id,
            WarehouseLocation.is_active == True,
        )
        .first()
    )
    if not bin_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bin not found"
        )

    if bin_location.location_type != "bin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location is type '{bin_location.location_type}', not 'bin'",
        )

    # Find item by SKU for stock update
    from app.models.item import Item

    db_item = (
        db.query(Item)
        .filter(
            Item.sku == item.sku,
            Item.organization_id == current_user.organization_id,
            Item.deleted_at.is_(None),
        )
        .first()
    )
    if not db_item:
        db_item = (
            db.query(Item)
            .filter(
                Item.item_code == item.sku,
                Item.organization_id == current_user.organization_id,
                Item.deleted_at.is_(None),
            )
            .first()
        )
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item not found for SKU: {item.sku}",
        )

    # Add stock to bin
    qty = body.quantity if body.quantity else item.quantity
    bin_stock_svc = BinStockService(db)
    bin_stock_svc.add_stock(
        bin_id=body.bin_location_id,
        item_id=db_item.id,
        quantity=qty,
        org_id=current_user.organization_id,
        batch_number=item.batch_number,
    )

    # Update slip item
    item.bin_location_id = body.bin_location_id
    item.put_away_status = "completed"
    item.put_away_at = datetime.now(UTC)
    item.put_away_by = current_user.id

    # Check if all items on slip are completed
    pending = (
        db.query(ReceivingSlipItem)
        .filter(
            ReceivingSlipItem.slip_id == slip_id,
            ReceivingSlipItem.put_away_status == "pending",
            ReceivingSlipItem.flag == "ok",
        )
        .count()
    )
    if pending == 0:
        slip = db.query(ReceivingSlip).filter(ReceivingSlip.id == slip_id).first()
        if slip:
            slip.status = "putaway_complete"

    db.commit()

    return AssignBinResponse(
        slip_item_id=str(item.id),
        sku=item.sku,
        batch_number=item.batch_number,
        quantity=qty,
        bin_location_id=str(body.bin_location_id),
        bin_full_path=bin_location.full_path or bin_location.code,
        put_away_status="completed",
        put_away_at=item.put_away_at.isoformat() if item.put_away_at else None,
    )


# ------------------------------------------------------------------
# FIFO Bin Suggestions for Picking (Phase 3)
# ------------------------------------------------------------------


@router.get(
    "/receiving-slips/{slip_id}/items/{item_id}/fifo-bins",
    summary="Get FIFO bin suggestions for a slip item",
    description="Returns bins sorted by FIFO (oldest stock first) for put-away reference.",
)
async def get_fifo_bins_for_slip_item(
    slip_id: UUID,
    item_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Get bins containing this item, sorted by stock age (FIFO).

    Used to suggest which bins already have this SKU — helps worker
    consolidate stock or know where existing inventory is.
    """
    from datetime import UTC, datetime

    from app.models.bin_stock_level import BinStockLevel
    from app.models.item import Item
    from app.models.receiving_slip import ReceivingSlipItem
    from app.models.warehouse_location import WarehouseLocation

    item = (
        db.query(ReceivingSlipItem)
        .filter(ReceivingSlipItem.id == item_id, ReceivingSlipItem.slip_id == slip_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Slip item not found"
        )

    # Find item by SKU
    db_item = (
        db.query(Item)
        .filter(
            Item.sku == item.sku,
            Item.organization_id == current_user.organization_id,
            Item.deleted_at.is_(None),
        )
        .first()
    ) or (
        db.query(Item)
        .filter(
            Item.item_code == item.sku,
            Item.organization_id == current_user.organization_id,
            Item.deleted_at.is_(None),
        )
        .first()
    )
    if not db_item:
        return {"sku": item.sku, "bins": [], "message": "Item not found in catalog"}

    now = datetime.now(UTC)
    bins = (
        db.query(BinStockLevel, WarehouseLocation)
        .join(WarehouseLocation, BinStockLevel.bin_location_id == WarehouseLocation.id)
        .filter(
            BinStockLevel.item_id == db_item.id,
            BinStockLevel.organization_id == current_user.organization_id,
            BinStockLevel.quantity_on_hand > 0,
            WarehouseLocation.is_pickable.is_(True),
        )
        .order_by(BinStockLevel.created_at.asc())
        .all()
    )

    return {
        "sku": item.sku,
        "bins": [
            {
                "bin_id": str(stock.bin_location_id),
                "bin_path": loc.full_path or loc.code,
                "batch_number": stock.batch_number,
                "quantity_on_hand": int(stock.quantity_on_hand),
                "stock_age_days": (now - stock.created_at).days
                if stock.created_at
                else None,
            }
            for stock, loc in bins
        ],
    }


# ------------------------------------------------------------------
# ASN Linking
# ------------------------------------------------------------------


@router.post(
    "/sessions/{session_id}/link-asn",
    response_model=SessionResponse,
    summary="Link scan session to ASN",
    description="Link an existing open scan session to an ASN order",
)
async def link_asn_to_session(
    session_id: UUID,
    data: LinkAsnToSessionRequest,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Link an existing scan session to an ASN order.

    **Path Parameters:**
    - **session_id**: UUID of the active scan session

    **Request Body:**
    - **asn_order_id**: UUID of the ASN order to link

    **Returns:** Updated session details
    """
    from app.models.asn_order import AsnOrder

    service = InboundService(db)

    # Validate ASN exists
    asn = (
        db.query(AsnOrder)
        .filter(
            AsnOrder.id == data.asn_order_id,
            AsnOrder.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not asn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ASN order not found"
        )

    updated = service.session_repo.set_asn_order(session_id, data.asn_order_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan session not found"
        )

    return SessionResponse(**service._session_to_dict(updated))


# ------------------------------------------------------------------
# Item-Level Rejection (Floating Mode)
# ------------------------------------------------------------------


@router.post(
    "/receiving-slips/{slip_id}/items/{item_id}/reject",
    response_model=RejectedItemResponse,
    summary="Reject individual slip item",
    description="Reject a specific receiving slip line item. Item enters floating mode — no stock update, no put-away.",
)
async def reject_slip_item(
    slip_id: UUID,
    item_id: UUID,
    data: RejectSlipItemRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Reject an individual receiving slip line item.

    The rejected item enters "floating mode":
    - Recorded on the slip but excluded from put-away
    - Does not update stock levels
    - Does not count toward ASN delivered_qty

    **Path Parameters:**
    - **slip_id**: UUID of the receiving slip
    - **item_id**: UUID of the line item to reject

    **Request Body:**
    - **reason**: Reason for rejection
    - **notes**: Optional additional notes

    **Returns:** Updated line item details
    """
    service = InboundService(db)
    result = service.reject_slip_item(
        slip_id=slip_id,
        item_id=item_id,
        reason=data.reason,
        organization_id=current_user.organization_id,
        rejected_by=current_user.id,
        notes=data.notes,
    )
    return RejectedItemResponse(**result)


@router.post(
    "/receiving-slips/{slip_id}/items/status",
    summary="Bulk update receiving slip item statuses",
    description="Update multiple receiving slip line items in one request. "
    "Each item carries a status ('rejected', 'ok', 'short', or 'damaged').",
)
async def update_slip_items_status(
    slip_id: UUID,
    data: BulkItemStatusUpdateRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """Bulk update item statuses on a receiving slip.

    Request body:
        { "items": [ { "item_id": "...", "status": "rejected", "reason": "..." } ] }
    """
    service = InboundService(db)
    results = service.update_items_status(
        slip_id=slip_id,
        items=data.items,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return {"items": results}


# ------------------------------------------------------------------
# Floating Items (Rejected Items Across All Slips)
# ------------------------------------------------------------------


@router.get(
    "/floating-items",
    summary="List floating items",
    description="List all rejected (floating) items across all receiving slips",
)
async def list_floating_items(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    List all rejected (floating) items that need resolution.

    Floating items are receiving slip line items with flag='rejected'.
    They need to be resolved via accept, return_to_sender, or dispose.

    **Query Parameters:**
    - **warehouse_id**: Optional filter by warehouse
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20)

    **Returns:** Paginated list of floating items
    """
    from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem
    from app.schemas.inbound import FloatingItemsListResponse, FloatingItemSummary

    query = (
        db.query(ReceivingSlipItem, ReceivingSlip)
        .join(ReceivingSlip, ReceivingSlipItem.slip_id == ReceivingSlip.id)
        .filter(
            ReceivingSlipItem.organization_id == current_user.organization_id,
            ReceivingSlipItem.flag == "rejected",
        )
    )

    if warehouse_id:
        query = query.filter(ReceivingSlip.warehouse_id == warehouse_id)

    total = query.count()
    offset = (page - 1) * page_size
    rows = (
        query.order_by(ReceivingSlipItem.rejected_at.desc().nulls_last())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for item, slip in rows:
        asn_no = None
        if slip.asn_order and hasattr(slip, "asn_order"):
            asn_no = slip.asn_order.asn_order_no

        items.append(
            FloatingItemSummary(
                slip_item_id=str(item.id),
                slip_id=str(slip.id),
                slip_number=slip.slip_number,
                sku=item.sku,
                batch_number=item.batch_number,
                quantity=item.quantity,
                rejection_reason=item.rejection_reason,
                rejected_at=item.rejected_at.isoformat() if item.rejected_at else None,
                warehouse_id=str(slip.warehouse_id),
                asn_order_no=asn_no,
            )
        )

    return FloatingItemsListResponse(
        floating_items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/floating-items/{item_id}/resolve",
    summary="Resolve a floating item",
    description="Resolve a rejected (floating) item: accept, return_to_sender, or dispose",
)
async def resolve_floating_item(
    item_id: UUID,
    data: ResolveFloatingItemRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Resolve a floating (rejected) receiving slip item.

    **Path Parameters:**
    - **item_id**: UUID of the floating item (ReceivingSlipItem.id)

    **Request Body:**
    - **action**: Resolution action - 'accept', 'return_to_sender', or 'dispose'
    - **notes**: Optional notes about the resolution

    **Returns:** Updated item details
    """
    from datetime import UTC, datetime

    from app.models.receiving_slip import ReceivingSlipItem
    from app.schemas.inbound import RejectedItemResponse

    valid_actions = ("accept", "return_to_sender", "dispose")
    if data.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
        )

    item = (
        db.query(ReceivingSlipItem)
        .filter(
            ReceivingSlipItem.id == item_id,
            ReceivingSlipItem.organization_id == current_user.organization_id,
            ReceivingSlipItem.flag == "rejected",
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floating item not found or already resolved",
        )

    if data.action == "accept":
        # Move from rejected to accepted (ready for put-away if slip is pending_putaway)
        item.flag = "ok"
        item.notes = (
            f"{item.notes or ''}\nResolved: accepted. {data.notes or ''}".strip()
        )
    elif data.action == "return_to_sender":
        item.flag = "rejected"
        item.notes = f"{item.notes or ''}\nResolved: return_to_sender. {data.notes or ''}".strip()
        item.put_away_status = "returned"
    elif data.action == "dispose":
        item.flag = "rejected"
        item.notes = (
            f"{item.notes or ''}\nResolved: disposed. {data.notes or ''}".strip()
        )
        item.put_away_status = "disposed"

    item.rejected_at = datetime.now(UTC)
    db.commit()
    db.refresh(item)

    return RejectedItemResponse(
        id=str(item.id),
        slip_id=str(item.slip_id),
        sku=item.sku,
        batch_number=item.batch_number,
        quantity=item.quantity,
        box_count=item.box_count,
        flag=item.flag,
        rejection_reason=item.rejection_reason,
        notes=item.notes,
        rejected_at=item.rejected_at.isoformat() if item.rejected_at else None,
    )
