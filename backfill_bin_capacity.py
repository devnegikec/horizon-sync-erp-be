"""Backfill ``capacity`` on layout-derived bins so warehouse capacity stops reading 0.

Warehouse capacity is a roll-up of ``SUM(warehouse_locations.capacity)`` across
active bins, and ``capacity_math`` reads a volume-UOM ``capacity`` as **m³**.
Layout bins written before that roll-up existed carry ``capacity_uom='volume'``
and a real ``max_volume_cc`` but left ``capacity`` at the column default ``0``,
so every such warehouse reported ``total_capacity = 0``.

This script derives the missing value from the physical limit already on the bin
(``max_volume_cc / 1e6``) and leaves everything else — including the live
``available_capacity`` cache — untouched. It only touches bins whose ``capacity``
is still NULL/0, so it is safe to re-run.

Usage (venv active, from repo root):
    python backfill_bin_capacity.py                        # dry-run, all warehouses
    python backfill_bin_capacity.py --warehouse "ECity Bangalore"
    python backfill_bin_capacity.py --warehouse <uuid> --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

import dotenv
from sqlalchemy import create_engine, text

ENV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "core-service", ".env"
)

CC_PER_M3 = Decimal("1000000")
M3_SCALE = Decimal("0.001")


def _engine():
    if os.path.exists(ENV_PATH):
        dotenv.load_dotenv(ENV_PATH)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set and core-service/.env not found")
    return create_engine(url)


def _resolve_warehouse_id(c, name_or_id: str) -> str:
    rows = c.execute(
        text(
            "SELECT id, name FROM warehouses_extended "
            "WHERE is_active IS TRUE AND (name = :n OR id::text = :n)"
        ),
        {"n": name_or_id},
    ).all()
    if not rows:
        sys.exit(f"No active warehouse matches {name_or_id!r}")
    if len(rows) > 1:
        for r in rows:
            print(f"  {r[0]}  {r[1]!r}")
        sys.exit("Ambiguous warehouse — pass a full UUID instead.")
    return str(rows[0][0])


def _plan(c, warehouse_id: str | None) -> list:
    """Bins that need a m³ ``capacity`` derived from their cc volume limit."""
    sql = """
        SELECT id, code, warehouse_id, capacity, max_volume_cc
        FROM warehouse_locations
        WHERE location_type = 'bin'
          AND is_active IS TRUE
          AND capacity_uom = 'volume'
          AND max_volume_cc IS NOT NULL
          AND max_volume_cc > 0
          AND (capacity IS NULL OR capacity = 0)
    """
    params: dict = {}
    if warehouse_id:
        sql += " AND warehouse_id = :wh"
        params["wh"] = warehouse_id

    plan = []
    for loc_id, code, wh_id, capacity, max_cc in c.execute(text(sql), params).all():
        capacity_m3 = (Decimal(str(max_cc)) / CC_PER_M3).quantize(M3_SCALE)
        plan.append((loc_id, code, wh_id, capacity, max_cc, capacity_m3))
    return plan


def _rollup(c, warehouse_ids: list[str]) -> dict:
    if not warehouse_ids:
        return {}
    rows = c.execute(
        text(
            "SELECT warehouse_id, count(*), coalesce(sum(capacity), 0) "
            "FROM warehouse_locations "
            "WHERE location_type = 'bin' AND is_active IS TRUE "
            "AND warehouse_id = ANY(:ids) "
            "GROUP BY warehouse_id"
        ),
        {"ids": warehouse_ids},
    ).all()
    return {r[0]: (r[1], r[2]) for r in rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", help="Warehouse name or UUID (default: all)")
    parser.add_argument(
        "--apply", action="store_true", help="Write changes (default: dry-run)"
    )
    args = parser.parse_args()

    engine = _engine()
    with engine.connect() as c:
        wh_id = _resolve_warehouse_id(c, args.warehouse) if args.warehouse else None
        plan = _plan(c, wh_id)
        wh_ids = sorted({p[2] for p in plan})
        before = _rollup(c, wh_ids)

    if not plan:
        print("No active bins need a capacity backfill.")
        return

    print(f"Bins to update: {len(plan)} across {len(wh_ids)} warehouse(s)\n")
    for _loc_id, code, _wh, capacity, max_cc, capacity_m3 in plan[:10]:
        print(
            f"  {code:<24} max_volume_cc={max_cc}  capacity: "
            f"{capacity} -> {capacity_m3} m³"
        )
    if len(plan) > 10:
        print(f"  ... and {len(plan) - 10} more")

    print("\nWarehouse roll-up (SUM(bin.capacity)) if applied:")
    for wh in wh_ids:
        bin_count, current = before.get(wh, (0, Decimal(0)))
        added = sum(p[5] for p in plan if p[2] == wh)
        print(
            f"  {wh}: {current} -> {Decimal(str(current)) + added} m³ ({bin_count} bins)"
        )

    if not args.apply:
        print("\nDry-run — re-run with --apply to write.")
        return

    with engine.begin() as c:
        for loc_id, _code, _wh, _capacity, _max_cc, capacity_m3 in plan:
            c.execute(
                text(
                    "UPDATE warehouse_locations "
                    "SET capacity = :v, total_capacity = :v "
                    "WHERE id = :id AND is_active IS TRUE "
                    "AND (capacity IS NULL OR capacity = 0)"
                ),
                {"v": capacity_m3, "id": loc_id},
            )
    print(f"\nApplied. Backfilled capacity on {len(plan)} bins.")


if __name__ == "__main__":
    main()
