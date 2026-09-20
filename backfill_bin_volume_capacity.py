"""Backfill ``max_volume_cc`` on active bins so the dashboard Volume populates.

The dashboard Volume reads ``warehouse_locations.max_volume_cc`` (in cubic
centimetres, cc) summed across ACTIVE bins. The current bins were regenerated
from the floor plan with ``capacity_uom='volume'`` but ``max_volume_cc`` was
never carried over (it is NULL everywhere), so no Volume row renders.

Usage (venv active, from repo root):
    python backfill_bin_volume_capacity.py                          # dry-run, all warehouses
    python backfill_bin_volume_capacity.py --warehouse "Mother Warehouse"
    python backfill_bin_volume_capacity.py --fixed-cc 1000000 --apply   # 1 m³ per bin
    python backfill_bin_volume_capacity.py --factor 1000 --apply        # capacity (litres) -> cc

Modes (mutually exclusive):
    --fixed-cc N   every active bin gets max_volume_cc = N cc
    --factor F     max_volume_cc = bin.capacity * F  (only bins with
                   capacity_uom = 'volume', i.e. volume-capacity bins)

Defaults: --fixed-cc 1000000 (1 m³), matching the old pre-regeneration bins.
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


def _plan(c, warehouse_id: str | None, mode: str, value: Decimal) -> list:
    sql = """
        SELECT id, code, capacity, capacity_uom, max_volume_cc
        FROM warehouse_locations
        WHERE location_type = 'bin' AND is_active IS TRUE
    """
    params: dict = {}
    if warehouse_id:
        sql += " AND warehouse_id = :wh"
        params["wh"] = warehouse_id
    rows = c.execute(text(sql), params).all()

    plan = []
    for loc_id, code, capacity, uom, cur in rows:
        cap = Decimal(str(capacity)) if capacity is not None else Decimal("0")
        if mode == "fixed":
            new_cc = value
        else:  # factor
            if uom != "volume":
                continue
            new_cc = cap * value
        if cur is None or Decimal(str(cur)) != new_cc:
            plan.append((loc_id, code, cap, uom, cur, new_cc))
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", help="Warehouse name or UUID (default: all)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fixed-cc", type=Decimal, default=CC_PER_M3,
                      help="Fixed max_volume_cc per bin (default 1,000,000 cc = 1 m³)")
    mode.add_argument("--factor", type=Decimal,
                      help="Multiply bin.capacity by this to get cc (volume-uom bins only)")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()

    engine = _engine()
    with engine.connect() as c:
        wh_id = _resolve_warehouse_id(c, args.warehouse) if args.warehouse else None
        mode = "factor" if args.factor is not None else "fixed"
        value = args.factor if mode == "factor" else args.fixed_cc
        plan = _plan(c, wh_id, mode, value)

    if not plan:
        print("No active bins need updating.")
        return

    print(f"Mode: {'factor (capacity × ' + str(value) + ')' if mode == 'factor' else 'fixed (' + str(value) + ' cc)'}")
    print(f"Bins to update: {len(plan)}\n")
    for loc_id, code, cap, uom, cur, new_cc in plan[:20]:
        print(f"  {code:<24} capacity={cap} uom={uom!r}  max_volume_cc: {cur} -> {new_cc}")
    if len(plan) > 20:
        print(f"  ... and {len(plan) - 20} more")

    if not args.apply:
        print("\nDry-run — re-run with --apply to write.")
        return

    with engine.begin() as c:
        for loc_id, _code, _cap, _uom, _cur, new_cc in plan:
            c.execute(
                text("UPDATE warehouse_locations SET max_volume_cc = :v WHERE id = :id"),
                {"v": new_cc, "id": loc_id},
            )
    print(f"\nApplied. Updated max_volume_cc on {len(plan)} bins.")


if __name__ == "__main__":
    main()
