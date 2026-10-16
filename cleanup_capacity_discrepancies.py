"""Diagnose and (optionally) clean up warehouse-capacity data discrepancies.

Fixes the mismatch between the count-based capacity dashboard and the
volume-based Location Tree, caused by:

1. Orphaned bin stock left in deactivated / non-bin locations (counted by the
   dashboard's ``used_capacity`` but hidden from the volume tree).
2. Duplicate warehouse rows (e.g. "Mother warehouse " with a trailing space).
3. Bins with no ``max_volume_cc`` (volume capacity never populates).
4. Items with stock but no base packaging unit (occupied volume = 0).

Usage (from repo root, venv active):
    python cleanup_capacity_discrepancies.py                # report only
    python cleanup_capacity_discrepancies.py --zero-orphaned-stock   # apply fix #1

The orphaned-stock fix is transactional and prints exactly what changed.
Duplicate-warehouse merging is NOT automated — it needs a human to choose the
canonical row; the script only lists the candidates.
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


def _engine():
    if os.path.exists(ENV_PATH):
        dotenv.load_dotenv(ENV_PATH)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set and core-service/.env not found")
    return create_engine(url)


def report(c) -> None:
    print("=" * 78)
    print("1. DUPLICATE WAREHOUSE ROWS (same code, or names differing only by whitespace)")
    print("=" * 78)
    rows = c.execute(
        text(
            """
            SELECT id, name, code, is_active, total_capacity
            FROM warehouses_extended
            ORDER BY code, name
            """
        )
    ).all()
    for r in rows:
        print(f"  {r[2]:<16} id={r[0]} active={r[3]} total_capacity={r[4]} name={r[1]!r}")

    print()
    print("=" * 78)
    print("2. ORPHANED BIN STOCK (inactive or non-bin locations, qty > 0)")
    print("=" * 78)
    orphan_rows = c.execute(
        text(
            """
            SELECT w.name, wl.location_type, wl.is_active,
                   COUNT(*) AS rows, SUM(bs.quantity_on_hand) AS qty
            FROM bin_stock_levels bs
            JOIN warehouse_locations wl ON wl.id = bs.bin_location_id
            JOIN warehouses_extended w ON w.id = wl.warehouse_id
            WHERE bs.quantity_on_hand > 0
              AND (wl.is_active IS FALSE OR wl.location_type <> 'bin')
            GROUP BY w.name, wl.location_type, wl.is_active
            ORDER BY qty DESC
            """
        )
    ).all()
    if not orphan_rows:
        print("  (none)")
    for r in orphan_rows:
        print(f"  {r[0]!r} type={r[1]} active={r[2]} rows={r[3]} qty={r[4]}")

    print()
    print("=" * 78)
    print("3. BINS WITHOUT max_volume_cc (volume capacity will never populate)")
    print("=" * 78)
    vol_rows = c.execute(
        text(
            """
            SELECT w.name,
                   COUNT(*) FILTER (WHERE wl.max_volume_cc IS NULL) AS no_vol_limit,
                   COUNT(*) AS total_bins
            FROM warehouse_locations wl
            JOIN warehouses_extended w ON w.id = wl.warehouse_id
            WHERE wl.location_type = 'bin' AND wl.is_active IS TRUE
            GROUP BY w.name ORDER BY w.name
            """
        )
    ).all()
    for r in vol_rows:
        print(f"  {r[0]!r}: {r[1]} of {r[2]} bins have no max_volume_cc")

    print()
    print("=" * 78)
    print("4. ITEMS WITH STOCK BUT NO BASE PACKAGING UNIT (occupied volume = 0)")
    print("=" * 78)
    pkg_rows = c.execute(
        text(
            """
            SELECT w.name, i.item_code, i.item_name, SUM(bs.quantity_on_hand) AS qty
            FROM bin_stock_levels bs
            JOIN warehouse_locations wl ON wl.id = bs.bin_location_id
            JOIN warehouses_extended w ON w.id = wl.warehouse_id
            JOIN items i ON i.id = bs.item_id
            LEFT JOIN item_packaging_units base
                   ON base.item_id = bs.item_id AND base.is_base_unit IS TRUE
            WHERE bs.quantity_on_hand > 0
              AND wl.is_active IS TRUE AND wl.location_type = 'bin'
              AND base.id IS NULL
            GROUP BY w.name, i.item_code, i.item_name
            ORDER BY qty DESC
            """
        )
    ).all()
    if not pkg_rows:
        print("  (none)")
    for r in pkg_rows:
        print(f"  {r[0]!r} {r[1]} ({r[2]!r}) qty={r[3]}")


def zero_orphaned_stock(engine) -> None:
    """Zero bin_stock in inactive/non-bin locations and reconcile stock_levels."""
    with engine.begin() as c:
        orphans = c.execute(
            text(
                """
                SELECT bs.id, bs.item_id, wl.warehouse_id, bs.organization_id,
                       bs.quantity_on_hand
                FROM bin_stock_levels bs
                JOIN warehouse_locations wl ON wl.id = bs.bin_location_id
                WHERE bs.quantity_on_hand > 0
                  AND (wl.is_active IS FALSE OR wl.location_type <> 'bin')
                """
            )
        ).all()
        if not orphans:
            print("No orphaned bin stock found — nothing to do.")
            return

        # Aggregate orphaned qty per (item, warehouse) for stock_levels sync.
        deltas: dict[tuple, Decimal] = {}
        for _bs_id, item_id, wh_id, org_id, qty in orphans:
            key = (item_id, wh_id, org_id)
            deltas[key] = deltas.get(key, Decimal("0")) + Decimal(str(qty))

        # Zero only the rows captured in the snapshot, so a concurrently-added
        # orphan row is not zeroed without a matching stock_levels deduction.
        orphan_ids = [row[0] for row in orphans]
        if orphan_ids:
            placeholders = ", ".join(f":id{i}" for i in range(len(orphan_ids)))
            c.execute(
                text(
                    f"UPDATE bin_stock_levels SET quantity_on_hand = 0 "
                    f"WHERE id IN ({placeholders})"
                ),
                {f"id{i}": str(oid) for i, oid in enumerate(orphan_ids)},
            )

        # Reconcile warehouse-level stock_levels (never below 0).
        for (item_id, wh_id, org_id), qty in deltas.items():
            c.execute(
                text(
                    """
                    UPDATE stock_levels
                    SET quantity_on_hand = GREATEST(0, quantity_on_hand - :qty),
                        quantity_available = GREATEST(
                            0,
                            GREATEST(0, quantity_on_hand - :qty) - quantity_reserved
                        )
                    WHERE item_id = :item_id
                      AND warehouse_id = :wh_id
                      AND organization_id = :org_id
                    """
                ),
                {"qty": qty, "item_id": item_id, "wh_id": wh_id, "org_id": org_id},
            )

        print(f"Zeroed {len(orphans)} orphaned bin-stock rows.")
        print(f"Reconciled {len(deltas)} warehouse stock_levels rows:")
        for (item_id, wh_id, _org), qty in sorted(deltas.items(), key=lambda kv: -kv[1]):
            print(f"  item={item_id} warehouse={wh_id} -{qty}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zero-orphaned-stock",
        action="store_true",
        help="Zero orphaned bin stock and reconcile warehouse stock_levels.",
    )
    args = parser.parse_args()

    engine = _engine()
    if args.zero_orphaned_stock:
        zero_orphaned_stock(engine)
    else:
        with engine.connect() as c:
            report(c)


if __name__ == "__main__":
    main()
