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
        None, description="Filter where from OR to warehouse matches"
    ),
    search: str | None = Query(None, description="Search by ASN order number"),
    sort_by: str = Query("order_date"),
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
