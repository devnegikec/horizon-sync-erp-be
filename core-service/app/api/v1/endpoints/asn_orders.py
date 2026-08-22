"""ASN Orders API endpoints"""

import csv
import io
from datetime import UTC, datetime
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
    search: str | None = Query(None, description="Search by ASN order number"),
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
        search=search,
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
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """
    Get a mismatch summary comparing ASN expected vs actually received.

    Aggregates data from all receiving slips linked to this ASN order.
    Shows per-line-item comparison of expected, accepted, rejected,
    pending, and over-delivered quantities.

    **Path Parameters:**
    - **asn_order_id**: UUID of the ASN order

    **Returns:**
    - ASN-level summary with totals
    - Per-line-item comparison
    - List of linked receiving slips
    """
    from app.repositories.asn_order_repository import AsnOrderRepository
    from app.repositories.receiving_slip_repository import ReceivingSlipRepository
    from app.schemas.inbound import (
        AsnLineItemReceivingSummary,
        AsnReceivingSummaryResponse,
        LinkedReceivingSlipSummary,
    )

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

    # Build line item summaries with status
    line_items = []
    matched = partial = not_received = over = 0
    for li in line_items_data:
        expected = li["expected_qty"]
        accepted = li["accepted_qty"]
        rejected_q = li["rejected_qty"]
        pending_q = li["pending_qty"]
        over_q = li["over_qty"]

        if expected == 0:
            item_status = "not_applicable"
        elif accepted == expected and rejected_q == 0:
            item_status = "matched"
            matched += 1
        elif accepted + rejected_q > expected:
            item_status = "over"
            over += 1
        elif accepted + rejected_q < expected:
            if accepted + rejected_q == 0:
                item_status = "not_received"
                not_received += 1
            else:
                item_status = "partial"
                partial += 1
        else:
            item_status = "matched"
            matched += 1

        line_items.append(
            AsnLineItemReceivingSummary(
                asn_item_id=li["asn_item_id"],
                item_id=li["item_id"],
                sku=li["sku"],
                item_name=li["item_name"],
                expected_qty=expected,
                accepted_qty=accepted,
                rejected_qty=rejected_q,
                pending_qty=pending_q,
                over_qty=over_q,
                status=item_status,
            )
        )

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

    # Compute totals
    expected_total = sum(li["expected_qty"] for li in line_items_data)
    accepted_total = sum(li["accepted_qty"] for li in line_items_data)
    rejected_total = sum(li["rejected_qty"] for li in line_items_data)
    pending_total = sum(li["pending_qty"] for li in line_items_data)
    over_total = sum(li["over_qty"] for li in line_items_data)

    return AsnReceivingSummaryResponse(
        asn_order_id=str(asn.id),
        asn_order_no=asn.asn_order_no,
        asn_status=asn.status.value
        if hasattr(asn.status, "value")
        else str(asn.status),
        expected_total_qty=expected_total,
        accepted_total_qty=accepted_total,
        rejected_total_qty=rejected_total,
        pending_total_qty=pending_total,
        over_total_qty=over_total,
        total_line_items=len(line_items_data),
        matched_items=matched,
        partial_items=partial,
        not_received_items=not_received,
        over_items=over,
        linked_slips=linked_slips,
        line_items=line_items,
    )
