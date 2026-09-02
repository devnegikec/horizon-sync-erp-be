"""ASN Orders API endpoints"""

import csv
import io
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    ASN_ORDER_CREATE,
    ASN_ORDER_READ,
    ASN_ORDER_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.item import Item
from app.schemas.asn_order import (
    AsnOrderCreate,
    AsnOrderListItem,
    AsnOrderListResponse,
    AsnOrderResponse,
    AsnOrderStatusUpdate,
    AsnOrderUpdate,
)
from app.schemas.common import PaginationMeta
from app.services.asn_order_service import AsnOrderService

router = APIRouter()


@router.post("", response_model=AsnOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_asn_order(
    body: AsnOrderCreate,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    """Create ASN order. Requires asn_order.create."""
    svc = AsnOrderService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return AsnOrderResponse.model_validate(data)


@router.get("", response_model=AsnOrderListResponse)
async def list_asn_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None,
        pattern="^(draft|confirmed|partially_delivered|delivered|closed|cancelled)$",
    ),
    warehouse_id: UUID | None = Query(
        None, description="Filter by target (to) warehouse"
    ),
    source_warehouse_id: UUID | None = Query(
        None, description="Filter by source (from) warehouse"
    ),
    delivery_date_from: date | None = Query(
        None, description="Filter by expected arrival date from (inclusive)"
    ),
    delivery_date_to: date | None = Query(
        None, description="Filter by expected arrival date to (inclusive)"
    ),
    vehicle_no: str | None = Query(None, description="Filter by linked vehicle number"),
    search: str | None = Query(None, description="Search by ASN order number"),
    asn_type: str | None = Query(
        None, pattern="^(purchase|internal_transfer)$", description="Filter by ASN type"
    ),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """List ASN orders. Requires asn_order.read."""
    svc = AsnOrderService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        warehouse_id=warehouse_id,
        source_warehouse_id=source_warehouse_id,
        delivery_date_from=delivery_date_from,
        delivery_date_to=delivery_date_to,
        vehicle_no=vehicle_no,
        search=search,
        asn_type=asn_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return AsnOrderListResponse(
        asn_orders=[AsnOrderListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{asn_order_id}", response_model=AsnOrderResponse)
async def get_asn_order(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Get ASN order by ID. Requires asn_order.read."""
    svc = AsnOrderService(db)
    data = svc.get_by_id(asn_order_id, current_user.organization_id)
    return AsnOrderResponse.model_validate(data)


@router.get("/{asn_order_id}/serials")
async def get_asn_order_serials(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Get unit-level serial lines (received/in-transit) for an ASN. Requires asn_order.read."""
    svc = AsnOrderService(db)
    return svc.get_serial_lines(asn_order_id, current_user.organization_id)


@router.get("/{asn_order_id}/asn-856")
async def export_asn_856(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """EDI-856-style serialized ASN export (SKU + serials + SSCC). Requires asn_order.read."""
    svc = AsnOrderService(db)
    return svc.serialized_asn_856(asn_order_id, current_user.organization_id)


@router.get("/{asn_order_id}/epcis")
async def export_asn_epcis(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """EPCIS 2.0-style event stream for the ASN's serials. Requires asn_order.read."""
    svc = AsnOrderService(db)
    return svc.epcis_events(asn_order_id, current_user.organization_id)


@router.put("/{asn_order_id}", response_model=AsnOrderResponse)
async def update_asn_order(
    asn_order_id: UUID,
    body: AsnOrderUpdate,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update ASN order. Requires asn_order.update."""
    svc = AsnOrderService(db)
    data = svc.update(
        asn_order_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
        current_user.user_type,
        current_user.permissions,
    )
    return AsnOrderResponse.model_validate(data)


@router.delete("/{asn_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asn_order(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete ASN order. Requires asn_order.update."""
    svc = AsnOrderService(db)
    svc.delete(asn_order_id, current_user.organization_id)
    return None


@router.put("/{asn_order_id}/status", response_model=AsnOrderResponse)
async def update_asn_order_status(
    asn_order_id: UUID,
    body: AsnOrderStatusUpdate,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update ASN order status. Requires asn_order.update."""
    svc = AsnOrderService(db)
    data = svc.update_status(
        asn_order_id,
        body.status,
        current_user.organization_id,
        current_user.id,
        current_user.user_type,
        current_user.permissions,
    )
    return AsnOrderResponse.model_validate(data)


@router.post("/{asn_order_id}/confirm", response_model=AsnOrderResponse)
async def confirm_asn_order(
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Confirm an ASN order (approve + auto-create source pick list for transfers). Requires asn_order.update."""
    svc = AsnOrderService(db)
    data = svc.update_status(
        asn_order_id,
        "confirmed",
        current_user.organization_id,
        current_user.id,
        current_user.user_type,
        current_user.permissions,
    )
    return AsnOrderResponse.model_validate(data)


# ── CSV Upload ─────────────────────────────────────────────────────────────────


@router.post(
    "/upload", response_model=AsnOrderResponse, status_code=status.HTTP_201_CREATED
)
async def upload_asn_csv(
    file: UploadFile = File(...),
    warehouse_id_to: UUID | None = Query(
        None, description="Destination warehouse UUID"
    ),
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    """Upload ASN order via CSV file.

    Expected CSV columns: Item Name, Item Code, Quantity, UOM
    Items are matched by item_code within the user's organization.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file has no headers")

    # Normalize headers (case-insensitive, strip whitespace)
    headers = {h.strip().lower(): h.strip() for h in reader.fieldnames}
    required = {"item code", "quantity"}
    missing = required - set(headers.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}. Expected: Item Code, Quantity",
        )

    # Parse rows
    items_payload = []
    org_id = current_user.organization_id
    row_num = 1
    errors = []

    for row in reader:
        row_num += 1
        item_code = (row.get(headers.get("item code", "")) or "").strip()
        qty_str = (row.get(headers.get("quantity", "")) or "0").strip()
        uom = (row.get(headers.get("uom", "")) or "Piece").strip()

        if not item_code:
            errors.append(f"Row {row_num}: empty Item Code")
            continue

        try:
            qty = float(qty_str)
            if qty <= 0:
                errors.append(f"Row {row_num}: Quantity must be > 0")
                continue
        except ValueError:
            errors.append(f"Row {row_num}: invalid Quantity '{qty_str}'")
            continue

        # Look up item by item_code
        item = (
            db.query(Item)
            .filter(
                Item.item_code == item_code,
                Item.organization_id == org_id,
                Item.deleted_at.is_(None),
            )
            .first()
        )
        if not item:
            errors.append(f"Row {row_num}: Item '{item_code}' not found")
            continue

        items_payload.append(
            {
                "item_id": str(item.id),
                "qty": qty,
                "uom": uom,
            }
        )

    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"CSV validation errors: {'; '.join(errors[:10])}",
        )

    if not items_payload:
        raise HTTPException(status_code=400, detail="No valid items found in CSV")

    # Create ASN order
    svc = AsnOrderService(db)
    data = svc.create(
        {
            "order_date": datetime.now(UTC).isoformat(),
            "warehouse_id_to": str(warehouse_id_to) if warehouse_id_to else None,
            "items": items_payload,
            "status": "draft",
            "remarks": f"Imported from {file.filename}",
        },
        org_id,
        current_user.id,
    )
    return AsnOrderResponse.model_validate(data)


# ------------------------------------------------------------------
# ASN Receiving Summary (Mismatch View)
# ------------------------------------------------------------------


@router.get(
    "/{asn_order_id}/receiving-summary",
    summary="Get ASN receiving summary",
    description="Compare ASN expected quantities against actual receipts across all linked receiving slips",
)
async def get_receiving_summary(
    asn_order_id: UUID,
    session_id: UUID | None = Query(
        None,
        description="Optional active inbound session whose scans should be included",
    ),
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """
    Get a mismatch summary comparing ASN expected vs actually received.

    Aggregates finalized receiving slips and, when ``session_id`` is supplied,
    scans from that active inbound session. This lets receiving clients refresh
    the same endpoint after each scan without waiting for a receipt note.

    **Path Parameters:**
    - **asn_order_id**: UUID of the ASN order

    **Returns:**
    - ASN-level summary with totals
    - Per-line-item comparison
    - List of linked receiving slips
    """
    from sqlalchemy import func

    from app.models.inbound_exception import InboundException
    from app.models.scan_session import ScanSession, ScanSessionItem
    from app.repositories.asn_order_repository import AsnOrderRepository
    from app.repositories.receiving_slip_repository import ReceivingSlipRepository
    from app.schemas.inbound import (
        AsnLineItemReceivingSummary,
        AsnReceivingSummaryResponse,
        LinkedReceivingSlipSummary,
    )
    from app.services.asn_reconciliation import compute_asn_reconciliation

    asn_repo = AsnOrderRepository(db)
    slip_repo = ReceivingSlipRepository(db)

    # Get ASN with items
    asn = asn_repo.get_by_id_with_items(asn_order_id, current_user.organization_id)
    if not asn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ASN order not found"
        )

    # Get linked receiving slips
    slips = slip_repo.get_slips_by_asn_order(asn_order_id, current_user.organization_id)

    # Get per-line-item receiving summary
    line_items_data = asn_repo.get_receiving_summary(asn_order_id)

    # Include the in-progress session only when it belongs to the requested
    # ASN and organisation. Finalized sessions are already represented by
    # their receiving slips, so including them here would double-count scans.
    active_session_id = None
    active_scans_by_sku: dict[str, int] = {}
    unresolved_exception_count = 0
    if session_id is not None:
        active_session = (
            db.query(ScanSession)
            .filter(
                ScanSession.id == session_id,
                ScanSession.organization_id == current_user.organization_id,
                ScanSession.asn_order_id == asn_order_id,
                ScanSession.status == "open",
            )
            .first()
        )
        if active_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Open inbound session linked to this ASN was not found",
            )

        active_session_id = str(active_session.id)
        scan_rows = (
            db.query(
                ScanSessionItem.sku,
                func.sum(ScanSessionItem.raw_quantity).label("total_quantity"),
            )
            .filter(ScanSessionItem.session_id == active_session.id)
            .group_by(ScanSessionItem.sku)
            .all()
        )
        active_scans_by_sku = {
            sku: int(quantity) if quantity else 0 for sku, quantity in scan_rows if sku
        }
        unresolved_exception_count = (
            db.query(InboundException)
            .filter(
                InboundException.session_id == active_session.id,
                InboundException.status.in_(["open", "pending_approval"]),
            )
            .count()
        )

    # Build line item summaries with status (pure reconciliation computation)
    summary = compute_asn_reconciliation(
        line_items_data=line_items_data,
        active_scans_by_sku=active_scans_by_sku,
        unresolved_exception_count=unresolved_exception_count,
        include_active_session=active_session_id is not None,
    )
    line_items = [AsnLineItemReceivingSummary(**li) for li in summary["line_items"]]

    # Build linked slip summaries
    linked_slips = []
    for slip in slips:
        accepted_qty = 0
        rejected_qty = 0
        for item in slip.items:
            if item.flag == "rejected":
                rejected_qty += item.quantity
            else:
                accepted_qty += item.quantity

        linked_slips.append(
            LinkedReceivingSlipSummary(
                slip_id=str(slip.id),
                slip_number=slip.slip_number,
                status=slip.status,
                created_at=slip.created_at.isoformat() if slip.created_at else None,
                total_accepted_qty=accepted_qty,
                total_rejected_qty=rejected_qty,
                total_items=len(slip.items),
            )
        )

    return AsnReceivingSummaryResponse(
        asn_order_id=str(asn.id),
        asn_order_no=asn.asn_order_no,
        asn_status=asn.status.value
        if hasattr(asn.status, "value")
        else str(asn.status),
        expected_total_qty=summary["expected_total_qty"],
        scanned_total_qty=summary["scanned_total_qty"],
        accepted_total_qty=summary["accepted_total_qty"],
        rejected_total_qty=summary["rejected_total_qty"],
        short_total_qty=summary["short_total_qty"],
        excess_total_qty=summary["excess_total_qty"],
        damaged_total_qty=summary["damaged_total_qty"],
        hold_total_qty=summary["hold_total_qty"],
        pending_total_qty=summary["pending_total_qty"],
        over_total_qty=summary["over_total_qty"],
        total_line_items=len(line_items_data),
        matched_items=summary["matched_items"],
        partial_items=summary["partial_items"],
        not_received_items=summary["not_received_items"],
        over_items=summary["over_items"],
        reconciliation_status=summary["reconciliation_status"],
        ready_for_receipt_note=summary["ready_for_receipt_note"],
        is_partial_receipt=summary["is_partial_receipt"],
        unresolved_exception_count=unresolved_exception_count,
        active_session_id=active_session_id,
        linked_slips=linked_slips,
        line_items=line_items,
    )
