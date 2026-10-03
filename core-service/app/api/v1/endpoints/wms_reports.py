"""WMS Reports API endpoints — tabular, filterable operational reports.

Every path below is relative to the global ``/api/v1`` prefix (see
``app/main.py``), so the full route is e.g.
``GET /api/v1/wms/reports/stock-movements`` — calling it without ``/api/v1``
returns 404.

MVP reports:
- GET /wms/reports/stock-movements   — movement ledger (in/out/transfer/adjust)
- GET /wms/reports/inventory-aging   — non-moving / slow-moving stock
- GET /wms/reports/receiving-variance — ASN expected vs received
- GET /wms/reports/bin-capacity      — bin volume/weight utilization

All endpoints scope to the caller's assigned warehouses using the same helper
as the WMS dashboard (system/organization admins see every warehouse).
"""

import csv
import io
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.warehouse_scope import get_user_warehouse_ids
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.item import Item
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.schemas.common import PaginationMeta
from app.schemas.wms_report import (
    BinCapacityReportResponse,
    BinCapacityRow,
    BinCapacitySummary,
    InventoryAgingReportResponse,
    InventoryAgingRow,
    InventoryAgingSummary,
    ReceivingVarianceReportResponse,
    ReceivingVarianceRow,
    ReceivingVarianceSummary,
    StockMovementReportResponse,
    StockMovementRow,
    StockMovementSummary,
)
from app.services.capacity_math import (
    compute_warehouse_bin_counts,
    compute_warehouse_bin_occupancy,
)

router = APIRouter()

MOVEMENT_TYPES = {"in", "out", "transfer", "adjustment"}
FULL_THRESHOLD_PCT = 90.0
MAX_EXPORT_ROWS = 100_000


# ── Helpers ─────────────────────────────────────────────────────────────────


def _tz(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC (matches the WMS dashboard convention)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _paginate(page: int, page_size: int, total: int) -> PaginationMeta:
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


def _resolve_scope(
    db: Session,
    current_user: CurrentUser,
    org_id: UUID,
    warehouse_id: UUID | None = None,
) -> tuple[list[UUID] | None, list[str] | None, list[Warehouse] | None]:
    """Return (warehouse UUIDs, warehouse UUID strings, Warehouse objects).

    Returns (None, None, None) when the caller has no accessible warehouses.
    """
    user_wh_ids = get_user_warehouse_ids(
        db,
        current_user.id,
        org_id,
        current_user.user_type,
        current_user.permissions,
    )
    q = db.query(Warehouse).filter(
        Warehouse.organization_id == org_id,
        Warehouse.is_active == True,
    )
    if warehouse_id:
        q = q.filter(Warehouse.id == warehouse_id)
        if user_wh_ids is not None:
            # Non-global users may only query warehouses assigned to them.
            q = q.filter(Warehouse.id.in_(user_wh_ids))
    elif user_wh_ids is not None:
        q = q.filter(Warehouse.id.in_(user_wh_ids))

    warehouses = q.all()
    if not warehouses:
        return None, None, None
    wh_ids = [w.id for w in warehouses]
    wh_id_strs = [str(w.id) for w in warehouses]
    return wh_ids, wh_id_strs, warehouses


def _csv_response(
    filename: str,
    rows: list,
    model_cls,
) -> StreamingResponse:
    """Serialize Pydantic row models to a downloadable CSV file."""
    fields = list(model_cls.model_fields.keys())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    for r in rows:
        d = r.model_dump(mode="json")
        writer.writerow(["" if d.get(f) is None else d[f] for f in fields])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── 1. Stock movement report ───────────────────────────────────────────────


@router.get("/stock-movements", response_model=StockMovementReportResponse)
async def stock_movements_report(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    item_id: UUID | None = Query(None, description="Filter by item"),
    movement_type: str | None = Query(
        None, description="in | out | transfer | adjustment"
    ),
    date_from: datetime | None = Query(None, description="Movement date from"),
    date_to: datetime | None = Query(None, description="Movement date to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    format: str = Query("json", pattern="^(json|csv)$", description="json or csv"),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
) -> StockMovementReportResponse | StreamingResponse:
    org_id = current_user.organization_id
    _, wh_id_strs, _ = _resolve_scope(db, current_user, org_id, warehouse_id)
    if wh_id_strs is None:
        if format == "csv":
            return _csv_response("stock_movements.csv", [], StockMovementRow)
        return StockMovementReportResponse(
            summary=StockMovementSummary(),
            rows=[],
            pagination=_paginate(page, page_size, 0),
        )

    if movement_type and movement_type not in MOVEMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid movement_type '{movement_type}'. "
            f"Valid values: {', '.join(sorted(MOVEMENT_TYPES))}",
        )

    filters = [
        StockMovement.organization_id == org_id,
        StockMovement.warehouse_id.in_(wh_id_strs),
    ]
    if item_id:
        filters.append(StockMovement.product_id == item_id)
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)
    if date_from:
        filters.append(StockMovement.performed_at >= _tz(date_from))
    if date_to:
        filters.append(StockMovement.performed_at < _tz(date_to))

    # Summary — aggregate qty/value by movement type for the period
    summary_rows = (
        db.query(
            StockMovement.movement_type,
            func.coalesce(func.sum(StockMovement.quantity), 0),
            func.coalesce(
                func.sum(StockMovement.quantity * StockMovement.unit_cost), 0
            ),
        )
        .filter(*filters)
        .group_by(StockMovement.movement_type)
        .all()
    )
    summary = StockMovementSummary()
    for mt, qty, value in summary_rows:
        m = mt.value if hasattr(mt, "value") else str(mt)
        q, v = float(qty or 0), float(value or 0)
        if m == "in":
            summary.total_in_qty, summary.total_in_value = q, v
        elif m == "out":
            summary.total_out_qty, summary.total_out_value = q, v
        elif m == "transfer":
            summary.total_transfer_qty = q
        elif m == "adjustment":
            summary.total_adjustment_qty = q

    total = db.query(func.count(StockMovement.id)).filter(*filters).scalar() or 0

    rows: list[StockMovementRow] = []
    q = (
        db.query(StockMovement, Item, Warehouse)
        .join(Item, Item.id == StockMovement.product_id)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .filter(*filters)
        .order_by(StockMovement.performed_at.desc())
    )
    if format == "csv":
        q = q.limit(MAX_EXPORT_ROWS)
    else:
        q = q.offset((page - 1) * page_size).limit(page_size)
    for sm, item, wh in q.all():
        rows.append(
            StockMovementRow(
                id=sm.id,
                performed_at=sm.performed_at,
                movement_type=sm.movement_type.value if sm.movement_type else None,
                quantity=float(sm.quantity or 0),
                unit_cost=float(sm.unit_cost) if sm.unit_cost is not None else None,
                line_value=float((sm.quantity or 0) * (sm.unit_cost or 0)),
                reference_type=sm.reference_type,
                reference_id=sm.reference_id,
                notes=sm.notes,
                warehouse_id=sm.warehouse_id,
                warehouse_name=wh.name,
                item_id=item.id,
                item_code=item.item_code,
                item_name=item.item_name,
                sku=item.sku,
            )
        )

    if format == "csv":
        return _csv_response("stock_movements.csv", rows, StockMovementRow)

    return StockMovementReportResponse(
        summary=summary,
        rows=rows,
        pagination=_paginate(page, page_size, total),
    )


# ── 2. Inventory aging report ──────────────────────────────────────────────


@router.get("/inventory-aging", response_model=InventoryAgingReportResponse)
async def inventory_aging_report(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    item_id: UUID | None = Query(None, description="Filter by item"),
    days_idle: int = Query(30, ge=1, le=3650, description="Idle threshold in days"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    format: str = Query("json", pattern="^(json|csv)$", description="json or csv"),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
) -> InventoryAgingReportResponse | StreamingResponse:
    org_id = current_user.organization_id
    _, wh_id_strs, _ = _resolve_scope(db, current_user, org_id, warehouse_id)
    if wh_id_strs is None:
        if format == "csv":
            return _csv_response("inventory_aging.csv", [], InventoryAgingRow)
        return InventoryAgingReportResponse(
            summary=InventoryAgingSummary(days_idle=days_idle),
            rows=[],
            pagination=_paginate(page, page_size, 0),
        )

    cutoff = datetime.now(UTC) - timedelta(days=days_idle)

    clauses = [
        "sl.organization_id = :org",
        "COALESCE(sl.quantity_on_hand, 0) > 0",
    ]
    params: dict = {"org": str(org_id), "cutoff": cutoff}

    if wh_id_strs:
        ph = ", ".join(f":wh{i}" for i in range(len(wh_id_strs)))
        clauses.append(f"sl.warehouse_id IN ({ph})")
        for i, wid in enumerate(wh_id_strs):
            params[f"wh{i}"] = wid
    if item_id:
        clauses.append("sl.item_id = :item_id")
        params["item_id"] = str(item_id)

    where_sql = " AND ".join(clauses)
    idle_cond = "(lm.last_moved_at IS NULL OR lm.last_moved_at < :cutoff)"

    base_from = """
        FROM stock_levels sl
        JOIN items i ON i.id = sl.item_id
        JOIN warehouses_extended w ON w.id = sl.warehouse_id
        LEFT JOIN (
            SELECT product_id, warehouse_id,
                   MAX(performed_at) AS last_moved_at,
                   (array_agg(unit_cost ORDER BY performed_at DESC)
                    FILTER (WHERE unit_cost IS NOT NULL))[1] AS last_unit_cost
            FROM stock_movements
            WHERE organization_id = :org
            GROUP BY product_id, warehouse_id
        ) lm ON lm.product_id = sl.item_id AND lm.warehouse_id = sl.warehouse_id
    """

    summ_row = db.execute(
        text(
            "SELECT COUNT(*)::int, "
            "COALESCE(SUM(sl.quantity_on_hand), 0), "
            "COALESCE(SUM(sl.quantity_on_hand * COALESCE(lm.last_unit_cost, 0)), 0) "
            f"{base_from} WHERE {where_sql} AND {idle_cond}"
        ),
        params,
    ).one()

    idle_count = int(summ_row[0] or 0)
    idle_qty = float(summ_row[1] or 0)
    idle_value = float(summ_row[2] or 0)

    if format == "csv":
        params["limit"] = MAX_EXPORT_ROWS
        limit_clause = "LIMIT :limit"
    else:
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        limit_clause = "LIMIT :limit OFFSET :offset"

    data_rows = db.execute(
        text(
            "SELECT sl.item_id, i.item_code, i.item_name, i.sku, "
            "sl.warehouse_id, w.name, "
            "sl.quantity_on_hand, sl.quantity_reserved, sl.quantity_available, "
            "lm.last_moved_at, lm.last_unit_cost "
            f"{base_from} WHERE {where_sql} AND {idle_cond} "
            f"ORDER BY lm.last_moved_at ASC NULLS FIRST, i.item_code {limit_clause}"
        ),
        params,
    ).fetchall()

    now = datetime.now(UTC)
    rows: list[InventoryAgingRow] = []
    for r in data_rows:
        last_moved = r[9]
        last_cost = float(r[10]) if r[10] is not None else None
        days: int | None = None
        if last_moved is not None:
            days = (now - _tz(last_moved)).days
        qty = float(r[6] or 0)
        rows.append(
            InventoryAgingRow(
                item_id=r[0],
                item_code=r[1],
                item_name=r[2],
                sku=r[3],
                warehouse_id=r[4],
                warehouse_name=r[5],
                quantity_on_hand=qty,
                quantity_reserved=float(r[7] or 0),
                quantity_available=float(r[8] or 0),
                last_moved_at=last_moved,
                last_unit_cost=last_cost,
                est_value=qty * (last_cost or 0),
                days_idle=days,
            )
        )

    if format == "csv":
        return _csv_response("inventory_aging.csv", rows, InventoryAgingRow)

    return InventoryAgingReportResponse(
        summary=InventoryAgingSummary(
            idle_item_count=idle_count,
            total_idle_qty=idle_qty,
            total_idle_value=idle_value,
            days_idle=days_idle,
        ),
        rows=rows,
        pagination=_paginate(page, page_size, idle_count),
    )


# ── 3. Receiving vs ASN variance report ────────────────────────────────────


@router.get("/receiving-variance", response_model=ReceivingVarianceReportResponse)
async def receiving_variance_report(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    date_from: datetime | None = Query(None, description="ASN order date from"),
    date_to: datetime | None = Query(None, description="ASN order date to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    format: str = Query("json", pattern="^(json|csv)$", description="json or csv"),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
) -> ReceivingVarianceReportResponse | StreamingResponse:
    org_id = current_user.organization_id
    _, wh_id_strs, _ = _resolve_scope(db, current_user, org_id, warehouse_id)
    if wh_id_strs is None:
        if format == "csv":
            return _csv_response("receiving_variance.csv", [], ReceivingVarianceRow)
        return ReceivingVarianceReportResponse(
            summary=ReceivingVarianceSummary(),
            rows=[],
            pagination=_paginate(page, page_size, 0),
        )

    clauses = ["a.organization_id = :org"]
    params: dict = {"org": str(org_id)}
    if wh_id_strs:
        ph = ", ".join(f":wh{i}" for i in range(len(wh_id_strs)))
        clauses.append(f"a.warehouse_id_to IN ({ph})")
        for i, wid in enumerate(wh_id_strs):
            params[f"wh{i}"] = wid
    if date_from:
        clauses.append("a.order_date >= :date_from")
        params["date_from"] = _tz(date_from)
    if date_to:
        clauses.append("a.order_date < :date_to")
        params["date_to"] = _tz(date_to)

    where_sql = " AND ".join(clauses)

    # Aggregate expected qty at the ASN × item level so multiple ASN lines
    # sharing an SKU collapse into one row (received qty is only keyed by SKU).
    base_from = """
        FROM (
            SELECT asn_order_id, item_id, SUM(qty) AS expected
            FROM asn_order_items
            WHERE organization_id = :org
            GROUP BY asn_order_id, item_id
        ) exp
        JOIN asn_orders a ON a.id = exp.asn_order_id
        JOIN items i ON i.id = exp.item_id
        LEFT JOIN warehouses_extended w ON w.id = a.warehouse_id_to
        LEFT JOIN (
            SELECT rs.asn_order_id, rsi.sku, SUM(rsi.quantity) AS received
            FROM receiving_slip_items rsi
            JOIN receiving_slips rs ON rs.id = rsi.slip_id
            WHERE rs.asn_order_id IS NOT NULL
            GROUP BY rs.asn_order_id, rsi.sku
        ) recv ON recv.asn_order_id = a.id AND recv.sku = i.sku
    """

    summ_row = db.execute(
        text(
            "SELECT COALESCE(SUM(exp.expected), 0), "
            "COALESCE(SUM(COALESCE(recv.received, 0)), 0), "
            "COUNT(*), "
            "COUNT(*) FILTER (WHERE exp.expected > COALESCE(recv.received, 0)), "
            "COUNT(*) FILTER (WHERE exp.expected < COALESCE(recv.received, 0)) "
            f"{base_from} WHERE {where_sql}"
        ),
        params,
    ).one()

    expected = float(summ_row[0] or 0)
    received = float(summ_row[1] or 0)
    total = int(summ_row[2] or 0)

    if format == "csv":
        params["limit"] = MAX_EXPORT_ROWS
        limit_clause = "LIMIT :limit"
    else:
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        limit_clause = "LIMIT :limit OFFSET :offset"

    data_rows = db.execute(
        text(
            "SELECT a.id, a.asn_order_no, a.order_date, a.status, "
            "a.warehouse_id_to, w.name, "
            "i.id, i.item_code, i.item_name, i.sku, "
            "exp.expected, COALESCE(recv.received, 0) "
            f"{base_from} WHERE {where_sql} "
            f"ORDER BY a.order_date DESC {limit_clause}"
        ),
        params,
    ).fetchall()

    rows: list[ReceivingVarianceRow] = []
    for r in data_rows:
        exp = float(r[10] or 0)
        rec = float(r[11] or 0)
        rows.append(
            ReceivingVarianceRow(
                asn_order_id=r[0],
                asn_order_no=r[1],
                order_date=r[2],
                asn_status=r[3],
                warehouse_id=r[4],
                warehouse_name=r[5],
                item_id=r[6],
                item_code=r[7],
                item_name=r[8],
                sku=r[9],
                expected_qty=exp,
                received_qty=rec,
                variance_qty=exp - rec,
            )
        )

    if format == "csv":
        return _csv_response("receiving_variance.csv", rows, ReceivingVarianceRow)

    return ReceivingVarianceReportResponse(
        summary=ReceivingVarianceSummary(
            total_expected_qty=expected,
            total_received_qty=received,
            total_variance_qty=expected - received,
            line_count=total,
            short_line_count=int(summ_row[3] or 0),
            excess_line_count=int(summ_row[4] or 0),
        ),
        rows=rows,
        pagination=_paginate(page, page_size, total),
    )


# ── 4. Bin capacity utilization report ─────────────────────────────────────


@router.get("/bin-capacity", response_model=BinCapacityReportResponse)
async def bin_capacity_report(
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    format: str = Query("json", pattern="^(json|csv)$", description="json or csv"),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
) -> BinCapacityReportResponse | StreamingResponse:
    org_id = current_user.organization_id
    wh_ids, _, _ = _resolve_scope(db, current_user, org_id, warehouse_id)
    if wh_ids is None:
        if format == "csv":
            return _csv_response("bin_capacity.csv", [], BinCapacityRow)
        return BinCapacityReportResponse(
            summary=BinCapacitySummary(),
            rows=[],
            pagination=_paginate(page, page_size, 0),
        )

    base_filters = [
        WarehouseLocation.organization_id == org_id,
        WarehouseLocation.is_active == True,
        WarehouseLocation.location_type == "bin",
    ]
    if warehouse_id:
        base_filters.append(WarehouseLocation.warehouse_id == warehouse_id)
    else:
        base_filters.append(WarehouseLocation.warehouse_id.in_(wh_ids))

    # Reuse the (already fixed) volumetric engine for occupied volume/weight.
    occupancy: dict[str, tuple[Decimal, Decimal]] = {}
    counts: dict[str, tuple[Decimal, Decimal]] = {}
    for wid in wh_ids:
        occupancy.update(compute_warehouse_bin_occupancy(db, wid))
        counts.update(compute_warehouse_bin_counts(db, wid))

    # Summary from a lightweight (id, capacity) projection — avoids loading
    # full WarehouseLocation objects for every bin.
    summary = BinCapacitySummary()
    summary.total_occupied_cc = (
        sum(float(m3) for m3, _ in occupancy.values()) * 1_000_000
    )
    summary.total_occupied_grams = sum(float(kg) for _, kg in occupancy.values()) * 1000

    cap_rows = (
        db.query(
            WarehouseLocation.id,
            WarehouseLocation.max_volume_cc,
            WarehouseLocation.max_weight_grams,
        )
        .filter(*base_filters)
        .all()
    )

    for bin_id, max_vol, max_wt in cap_rows:
        key = str(bin_id)
        occ_m3, occ_kg = occupancy.get(key, (Decimal("0"), Decimal("0")))
        occ_cc = float(occ_m3) * 1_000_000
        occ_g = float(occ_kg) * 1000
        cap_cc = float(max_vol) if max_vol is not None else None
        cap_g = float(max_wt) if max_wt is not None else None
        vol_pct = (occ_cc / cap_cc * 100) if cap_cc else None
        w_pct = (occ_g / cap_g * 100) if cap_g else None

        summary.total_bins += 1
        summary.total_capacity_cc += cap_cc or 0
        summary.total_capacity_grams += cap_g or 0
        if cap_cc is not None:
            summary.bins_with_volume_capacity += 1
        if cap_g is not None:
            summary.bins_with_weight_capacity += 1
        if (vol_pct is not None and vol_pct > 100) or (
            w_pct is not None and w_pct > 100
        ):
            summary.over_utilized_bins += 1
        if (vol_pct is not None and vol_pct >= FULL_THRESHOLD_PCT) or (
            w_pct is not None and w_pct >= FULL_THRESHOLD_PCT
        ):
            summary.full_bins += 1

    summary.volume_utilization_pct = (
        (summary.total_occupied_cc / summary.total_capacity_cc * 100)
        if summary.total_capacity_cc
        else None
    )
    summary.weight_utilization_pct = (
        (summary.total_occupied_grams / summary.total_capacity_grams * 100)
        if summary.total_capacity_grams
        else None
    )

    # Rows — paginate in SQL so only the requested page loads full objects;
    # CSV export stays bounded by MAX_EXPORT_ROWS.
    rows_q = (
        db.query(WarehouseLocation)
        .filter(*base_filters)
        .order_by(WarehouseLocation.full_path)
    )
    if format == "csv":
        rows_q = rows_q.limit(MAX_EXPORT_ROWS)
    else:
        rows_q = rows_q.offset((page - 1) * page_size).limit(page_size)

    rows: list[BinCapacityRow] = []
    for b in rows_q.all():
        key = str(b.id)
        occ_m3, occ_kg = occupancy.get(key, (Decimal("0"), Decimal("0")))
        units, packs = counts.get(key, (Decimal("0"), Decimal("0")))
        occ_cc = float(occ_m3) * 1_000_000
        occ_g = float(occ_kg) * 1000
        cap_cc = float(b.max_volume_cc) if b.max_volume_cc is not None else None
        cap_g = float(b.max_weight_grams) if b.max_weight_grams is not None else None
        rows.append(
            BinCapacityRow(
                bin_id=b.id,
                code=b.code,
                full_path=b.full_path,
                location_type=b.location_type,
                is_pickable=bool(b.is_pickable),
                unit_count=float(units),
                master_pack_count=float(packs),
                occupied_cc=occ_cc,
                capacity_cc=cap_cc,
                volume_utilization_pct=(occ_cc / cap_cc * 100) if cap_cc else None,
                occupied_grams=occ_g,
                capacity_grams=cap_g,
                weight_utilization_pct=(occ_g / cap_g * 100) if cap_g else None,
            )
        )

    if format == "csv":
        return _csv_response("bin_capacity.csv", rows, BinCapacityRow)

    return BinCapacityReportResponse(
        summary=summary,
        rows=rows,
        pagination=_paginate(page, page_size, summary.total_bins),
    )
