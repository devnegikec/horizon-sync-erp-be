"""WMS Dashboard API endpoints for warehouse managers and supervisors"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.asn_order import AsnOrder
from app.models.bin_stock_level import BinStockLevel
from app.models.dispatch_record import DispatchRecord
from app.models.item import Item
from app.models.pick_list import PickList
from app.models.put_away_list import PutAwayList
from app.models.receiving_slip import ReceivingSlip
from app.models.scan_session import ScanSession
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation
from app.models.warehouse_user import WarehouseUser
from app.models.wms_worker import WMSWorker

router = APIRouter()


def _get_user_warehouse_ids(
    db: Session,
    user_id: UUID,
    organization_id: UUID,
    user_type: str,
    permissions: list[str],
) -> list[UUID] | None:
    """Return the list of warehouse IDs assigned to this user.

    Returns None if the user has global/admin access (meaning no filter should
    be applied and all warehouses are visible).
    """
    if user_type in ("system_admin", "organization_admin") or "*.*" in permissions:
        return None  # global access — no warehouse filter

    # Check for primary (mother-warehouse) assignment → global access
    has_primary = (
        db.query(WarehouseUser)
        .filter(
            WarehouseUser.organization_id == organization_id,
            WarehouseUser.user_id == user_id,
            WarehouseUser.is_primary == True,
            WarehouseUser.is_active == True,
        )
        .first()
    )
    if has_primary:
        return None  # global access

    rows = (
        db.query(WarehouseUser.warehouse_id)
        .filter(
            WarehouseUser.organization_id == organization_id,
            WarehouseUser.user_id == user_id,
            WarehouseUser.is_active == True,
        )
        .all()
    )
    return [r.warehouse_id for r in rows]


@router.get("/stats")
async def get_wms_dashboard_stats(
    warehouse_id: UUID | None = Query(None),
    period: str = Query("week", pattern="^(week|month|year)$"),
    date: datetime | None = Query(None, description="Anchor date (defaults to now)"),
    page: int = Query(1, ge=1, description="Page number for paginated activity (used by View All)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page for activity pagination"),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """Get WMS dashboard statistics for managers/supervisors.

    Returns:
      - Stat cards: total stock items, assigned warehouses count, low stock count,
        out-of-stock count, active workers count.
      - Stock overview chart data: per-period inbound/outbound quantities and values,
        broken down into chart-ready buckets.
      - Recent activity: paginated list of all WMS events scoped to the user's
        assigned warehouses.
    """
    org_id = current_user.organization_id
    anchor = date or datetime.now(UTC)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)

    # ── Period boundaries ──────────────────────────────────────────────────
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    elif period == "month":
        start = anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start.replace(month=start.month % 12 + 1) if start.month < 12
               else start.replace(year=start.year + 1, month=1))
    else:  # year
        start = anchor.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)

    # ── Warehouse scope ────────────────────────────────────────────────────
    # Respect the optional ?warehouse_id filter AND the user's own assignments.
    user_wh_ids = _get_user_warehouse_ids(
        db, current_user.id, org_id, current_user.user_type, current_user.permissions
    )

    # Build the effective warehouse list
    wh_q = db.query(Warehouse).filter(
        Warehouse.organization_id == org_id,
        Warehouse.is_active == True,
    )
    if warehouse_id:
        wh_q = wh_q.filter(Warehouse.id == warehouse_id)
    elif user_wh_ids is not None:
        wh_q = wh_q.filter(Warehouse.id.in_(user_wh_ids))

    warehouses = wh_q.all()
    wh_ids = [w.id for w in warehouses]
    # Cast to str for .in_() compatibility with TypeDecorator UUID columns
    wh_id_strs = [str(wid) for wid in wh_ids]

    if not wh_ids:
        # No assigned warehouses — return empty dashboard
        return _empty_response(period, start, end)

    # ── Stat cards ─────────────────────────────────────────────────────────
    # Bin stock totals for assigned warehouses
    bin_location_ids = [
        r.id for r in db.query(WarehouseLocation.id)
        .filter(WarehouseLocation.warehouse_id.in_(wh_id_strs))
        .all()
    ]

    total_stock_items = 0
    low_stock_count = 0
    out_of_stock_count = 0

    if bin_location_ids:
        # Aggregate qty per (item, warehouse) using bin locations
        from sqlalchemy import case
        stock_agg = (
            db.query(
                BinStockLevel.item_id,
                func.sum(BinStockLevel.quantity_on_hand).label("total_qty"),
            )
            .filter(
                BinStockLevel.organization_id == org_id,
                BinStockLevel.bin_location_id.in_(bin_location_ids),
            )
            .group_by(BinStockLevel.item_id)
            .all()
        )
        item_ids = [r.item_id for r in stock_agg]
        reorder_map: dict[UUID, int] = {}
        if item_ids:
            items_q = db.query(Item.id, Item.reorder_level).filter(Item.id.in_(item_ids)).all()
            reorder_map = {r.id: (r.reorder_level or 0) for r in items_q}

        total_stock_items = len(stock_agg)
        for row in stock_agg:
            qty = float(row.total_qty or 0)
            rl = reorder_map.get(row.item_id, 0)
            if qty <= 0:
                out_of_stock_count += 1
            elif rl > 0 and qty <= rl:
                low_stock_count += 1

    active_workers = (
        db.query(WMSWorker)
        .filter(
            WMSWorker.organization_id == org_id,
            WMSWorker.warehouse_id.in_(wh_id_strs),
            WMSWorker.is_active == True,
        )
        .count()
    )

    # ── Chart data: inbound / outbound movements in period ────────────────
    # Group by day/week/month bucket depending on period granularity

    def _movement_buckets(movement_type: str) -> list[dict]:
        """Return per-bucket (day/week/month) aggregates of stock movement qty and value."""
        q = (
            db.query(StockMovement)
            .filter(
                StockMovement.organization_id == org_id,
                StockMovement.movement_type == movement_type,
                StockMovement.warehouse_id.in_(wh_id_strs),
                StockMovement.performed_at >= start,
                StockMovement.performed_at < end,
            )
            .all()
        )
        buckets: dict[str, dict] = {}
        for mv in q:
            ts = mv.performed_at
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if period == "week":
                key = ts.strftime("%a")  # Mon…Sun
            elif period == "month":
                key = str(ts.day)
            else:
                key = ts.strftime("%b")
            if key not in buckets:
                buckets[key] = {"label": key, "qty": 0, "value": 0.0}
            buckets[key]["qty"] += float(mv.quantity or 0)
            buckets[key]["value"] += float((mv.quantity or 0) * (mv.unit_cost or 0))
        return list(buckets.values())

    inbound_chart = _movement_buckets("in")
    outbound_chart = _movement_buckets("out")

    # Period totals for the header stat
    inbound_total_qty = sum(b["qty"] for b in inbound_chart)
    outbound_total_qty = sum(b["qty"] for b in outbound_chart)
    inbound_total_value = sum(b["value"] for b in inbound_chart)
    outbound_total_value = sum(b["value"] for b in outbound_chart)

    # Receiving slip count (separate from stock movements — more granular)
    inbound_slips = (
        db.query(ReceivingSlip)
        .filter(
            ReceivingSlip.organization_id == org_id,
            ReceivingSlip.warehouse_id.in_(wh_id_strs),
            ReceivingSlip.created_at >= start,
            ReceivingSlip.created_at < end,
        )
        .count()
    )
    dispatch_count = (
        db.query(DispatchRecord)
        .filter(
            DispatchRecord.organization_id == org_id,
            DispatchRecord.dispatched_at >= start,
            DispatchRecord.dispatched_at < end,
        )
        .count()
    )

    # ── Recent activity (all types, newest first, paginated) ──────────────
    all_activity: list[dict] = []

    # Scan sessions — join worker name
    scan_rows = (
        db.query(ScanSession, WMSWorker)
        .outerjoin(WMSWorker, ScanSession.worker_id == WMSWorker.id)
        .filter(
            ScanSession.organization_id == org_id,
            ScanSession.warehouse_id.in_(wh_id_strs),
        )
        .order_by(ScanSession.created_at.desc())
        .limit(50)
        .all()
    )
    for sc, worker in scan_rows:
        worker_name = None
        if worker:
            worker_name = worker.display_name or f"{worker.first_name} {worker.last_name}"
        all_activity.append({
            "type": "scan_session",
            "title": f"Scan Session {str(sc.id)[:8].upper()}",
            "status": sc.status,
            "warehouse_id": str(sc.warehouse_id) if sc.warehouse_id else None,
            "worker_name": worker_name,
            "created_at": sc.created_at.isoformat() if sc.created_at else None,
        })

    # Pick lists
    pick_rows = (
        db.query(PickList)
        .filter(
            PickList.organization_id == org_id,
            PickList.warehouse_id.in_(wh_id_strs),
        )
        .order_by(PickList.created_at.desc())
        .limit(50)
        .all()
    )
    for pl in pick_rows:
        all_activity.append({
            "type": "pick_list",
            "title": f"Pick List {pl.pick_list_no}",
            "status": pl.status.value if pl.status else "unknown",
            "warehouse_id": str(pl.warehouse_id),
            "worker_name": None,
            "created_at": pl.created_at.isoformat() if pl.created_at else None,
        })

    # Put-away lists
    putaway_rows = (
        db.query(PutAwayList)
        .filter(
            PutAwayList.organization_id == org_id,
            PutAwayList.warehouse_id.in_(wh_id_strs),
        )
        .order_by(PutAwayList.created_at.desc())
        .limit(50)
        .all()
    )
    for pa in putaway_rows:
        all_activity.append({
            "type": "put_away",
            "title": f"Put-Away {pa.put_away_list_no}",
            "status": pa.status or "unknown",
            "warehouse_id": str(pa.warehouse_id),
            "worker_name": None,
            "created_at": pa.created_at.isoformat() if pa.created_at else None,
        })

    # ASN orders
    asn_rows = (
        db.query(AsnOrder)
        .filter(
            AsnOrder.organization_id == org_id,
            AsnOrder.warehouse_id_to.in_(wh_id_strs),
        )
        .order_by(AsnOrder.created_at.desc())
        .limit(50)
        .all()
    )
    for asn in asn_rows:
        all_activity.append({
            "type": "asn_order",
            "title": f"ASN {asn.asn_order_no}",
            "status": asn.status.value if asn.status else "unknown",
            "warehouse_id": str(asn.warehouse_id_to) if asn.warehouse_id_to else None,
            "worker_name": None,
            "created_at": asn.created_at.isoformat() if asn.created_at else None,
        })

    # Receiving slips
    slip_rows = (
        db.query(ReceivingSlip)
        .filter(
            ReceivingSlip.organization_id == org_id,
            ReceivingSlip.warehouse_id.in_(wh_id_strs),
        )
        .order_by(ReceivingSlip.created_at.desc())
        .limit(50)
        .all()
    )
    for sl in slip_rows:
        all_activity.append({
            "type": "receiving_slip",
            "title": f"Receiving Slip {sl.slip_number}",
            "status": sl.status,
            "warehouse_id": str(sl.warehouse_id),
            "worker_name": None,
            "created_at": sl.created_at.isoformat() if sl.created_at else None,
        })

    # Dispatches
    dispatch_rows = (
        db.query(DispatchRecord)
        .filter(DispatchRecord.organization_id == org_id)
        .order_by(DispatchRecord.dispatched_at.desc())
        .limit(50)
        .all()
    )
    for dr in dispatch_rows:
        all_activity.append({
            "type": "dispatch",
            "title": f"Dispatch {dr.dispatch_number}",
            "status": "completed",
            "warehouse_id": None,
            "worker_name": None,
            "created_at": dr.dispatched_at.isoformat() if dr.dispatched_at else None,
        })

    # Sort all combined activity newest-first, then paginate
    all_activity.sort(key=lambda x: x["created_at"] or "", reverse=True)
    total_activity = len(all_activity)
    offset = (page - 1) * page_size
    paged_activity = all_activity[offset: offset + page_size]

    return {
        "period": period,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        # Stat cards
        "stats": {
            "total_stock_items": total_stock_items,
            "assigned_warehouses": len(wh_ids),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "active_workers": active_workers,
        },
        # Chart data
        "stock_overview": {
            "inbound": {
                "total_qty": inbound_total_qty,
                "total_value": inbound_total_value,
                "receiving_slips": inbound_slips,
                "chart": inbound_chart,
            },
            "outbound": {
                "total_qty": outbound_total_qty,
                "total_value": outbound_total_value,
                "dispatches": dispatch_count,
                "chart": outbound_chart,
            },
        },
        # Paginated activity
        "recent_activity": paged_activity,
        "activity_pagination": {
            "page": page,
            "page_size": page_size,
            "total": total_activity,
            "total_pages": max(1, (total_activity + page_size - 1) // page_size),
            "has_next": offset + page_size < total_activity,
            "has_prev": page > 1,
        },
        # Legacy fields kept for backward compat with the WMS DashboardPanel
        "inbound": {
            "receiving_slips": inbound_slips,
            "items_received": 0,
            "stock_in_qty": int(inbound_total_qty),
        },
        "outbound": {
            "dispatches": dispatch_count,
            "stock_out_qty": int(outbound_total_qty),
        },
        "current_stock": {
            "total_records": total_stock_items,
            "total_quantity": 0.0,
        },
        "workers_count": active_workers,
    }


def _empty_response(period: str, start: datetime, end: datetime) -> dict:
    empty_pagination = {"page": 1, "page_size": 20, "total": 0, "total_pages": 1, "has_next": False, "has_prev": False}
    return {
        "period": period,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "stats": {"total_stock_items": 0, "assigned_warehouses": 0, "low_stock_count": 0, "out_of_stock_count": 0, "active_workers": 0},
        "stock_overview": {
            "inbound": {"total_qty": 0, "total_value": 0.0, "receiving_slips": 0, "chart": []},
            "outbound": {"total_qty": 0, "total_value": 0.0, "dispatches": 0, "chart": []},
        },
        "recent_activity": [],
        "activity_pagination": empty_pagination,
        "inbound": {"receiving_slips": 0, "items_received": 0, "stock_in_qty": 0},
        "outbound": {"dispatches": 0, "stock_out_qty": 0},
        "current_stock": {"total_records": 0, "total_quantity": 0.0},
        "workers_count": 0,
    }
