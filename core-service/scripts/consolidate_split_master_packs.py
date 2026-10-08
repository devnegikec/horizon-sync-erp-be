"""One-off consolidation: move scattered master-pack units into a single bin.

Fixes bin stock where the units of one QSeal master pack (parent) were put
away into two or more bins. The pre-fix put-away generator chunked serials
positionally instead of grouping them by parent box, so a physical master
pack could land 2 units in one bin and 1 unit in another.

For every parent whose available units span multiple bins, this script keeps
the bin holding the most units of that parent and transfers the remaining
units into it — restoring "one master pack = one bin" without changing total
on-hand (the move stays within the same warehouse).

Run inside the core-service container (``PYTHONPATH`` points at the repo root
so ``app`` is importable):

    cd /app && PYTHONPATH=/app python scripts/consolidate_split_master_packs.py --org-id <org-uuid>
    cd /app && PYTHONPATH=/app python scripts/consolidate_split_master_packs.py --org-id <org-uuid> --sku 41752
    cd /app && PYTHONPATH=/app python scripts/consolidate_split_master_packs.py --org-id <org-uuid> --dry-run
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from app.database import SessionLocal
from app.models.bin_stock_level import BinStockLevel, InventoryStatus
from app.models.item import Item
from app.models.qseal import QSealParameters
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_stock_service import BinStockService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolidate split QSeal master packs into one bin each."
    )
    parser.add_argument(
        "--org-id",
        required=True,
        type=UUID,
        help="Organization UUID to scope the consolidation.",
    )
    parser.add_argument(
        "--sku",
        default=None,
        help="Optional SKU to limit the consolidation to a single item.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would move without writing anything.",
    )
    return parser.parse_args()


def _find_scattered_parents(
    db, org_id: UUID, sku: str | None
) -> dict[UUID, dict]:
    """Return {parent_id: {bin_id: [unit rows]}} for split master packs.

    Only ``available`` stock with a positive on-hand is considered, so picked,
    staged, or segregated units are never touched.
    """
    query = (
        db.query(BinStockLevel, QSealParameters.parent_id)
        .join(
            QSealParameters,
            QSealParameters.serial_number == BinStockLevel.batch_number,
        )
        .filter(
            BinStockLevel.organization_id == org_id,
            QSealParameters.organization_id == org_id,
            BinStockLevel.inventory_status == InventoryStatus.AVAILABLE.value,
            BinStockLevel.quantity_on_hand > 0,
            QSealParameters.parent_id.isnot(None),
        )
    )
    if sku:
        query = query.join(Item, Item.id == BinStockLevel.item_id).filter(
            Item.sku == sku, Item.organization_id == org_id
        )

    parent_bins: dict[UUID, dict[UUID, list[BinStockLevel]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for stock, parent_id in query.all():
        parent_bins[parent_id][stock.bin_location_id].append(stock)

    # Only parents that are physically split across more than one bin.
    return {
        parent_id: bins
        for parent_id, bins in parent_bins.items()
        if len(bins) > 1
    }


def _choose_target_bin(
    db, org_id: UUID, bins: dict[UUID, list[BinStockLevel]]
) -> UUID:
    """Pick the bin holding the most units; tie-break earliest arrival, then id."""
    bin_codes = {
        row[0]: row[1]
        for row in db.query(WarehouseLocation.id, WarehouseLocation.code)
        .filter(
            WarehouseLocation.id.in_(bins.keys()),
            WarehouseLocation.organization_id == org_id,
        )
        .all()
    }

    def sort_key(bin_id: UUID) -> tuple[int, str, str, str]:
        rows = bins[bin_id]
        createds = [r.created_at for r in rows if r.created_at is not None]
        earliest = min(createds) if createds else None
        return (
            -len(rows),  # most units first
            earliest.isoformat() if earliest else "",
            bin_codes.get(bin_id, "") or "",
            str(bin_id),
        )

    return sorted(bins.keys(), key=sort_key)[0]


def _transfer_unit(
    db, org_id: UUID, stock: BinStockLevel, to_bin_id: UUID
) -> None:
    """Move one unit row into the target bin, preserving its status."""
    BinStockService(db).transfer_stock(
        from_bin_id=stock.bin_location_id,
        to_bin_id=to_bin_id,
        item_id=stock.item_id,
        quantity=Decimal(str(stock.quantity_on_hand)),
        org_id=org_id,
        batch_number=stock.batch_number,
        inventory_status=stock.inventory_status,
        from_inventory_status=stock.inventory_status,
    )


def main() -> None:
    args = _parse_args()
    db = SessionLocal()
    try:
        scattered = _find_scattered_parents(db, args.org_id, args.sku)
        if not scattered:
            print("No split master packs found — nothing to consolidate.")
            return

        print(f"Found {len(scattered)} master pack(s) split across multiple bins.")

        bin_codes = dict(
            db.query(WarehouseLocation.id, WarehouseLocation.code).filter(
                WarehouseLocation.organization_id == args.org_id
            ).all()
        )

        parents_moved = 0
        units_moved = 0
        parents_skipped = 0
        total_to_move = 0
        for parent_id, bins in scattered.items():
            target_bin = _choose_target_bin(db, args.org_id, bins)
            rows_to_move = [
                stock
                for bin_id, stocks in bins.items()
                if bin_id != target_bin
                for stock in stocks
            ]
            total_to_move += len(rows_to_move)
            moved_this_parent = 0
            summary = ", ".join(
                f"{bin_codes.get(bin_id, bin_id)}={len(stocks)}"
                for bin_id, stocks in bins.items()
            )
            print(
                f"\nParent {parent_id}: {summary} "
                f"-> target {bin_codes.get(target_bin, target_bin)}"
            )
            for stock in rows_to_move:
                from_code = bin_codes.get(stock.bin_location_id, stock.bin_location_id)
                to_code = bin_codes.get(target_bin, target_bin)
                print(
                    f"  move serial {stock.batch_number} "
                    f"{from_code} -> {to_code}"
                    + (" (dry-run)" if args.dry_run else "")
                )
                if not args.dry_run:
                    try:
                        _transfer_unit(db, args.org_id, stock, target_bin)
                        units_moved += 1
                        moved_this_parent += 1
                    except Exception as exc:  # noqa: BLE001 - report and continue
                        print(f"  SKIP {stock.batch_number}: {exc}")
                        parents_skipped += 1
            if not args.dry_run and moved_this_parent:
                parents_moved += 1

        if args.dry_run:
            print(
                f"\nDry run: {total_to_move} unit(s) would be moved across "
                f"{len(scattered)} master pack(s)."
            )
        else:
            print(
                f"\nDone: moved {units_moved} unit(s) across "
                f"{parents_moved} master pack(s) "
                f"({parents_skipped} unit(s) skipped)."
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
