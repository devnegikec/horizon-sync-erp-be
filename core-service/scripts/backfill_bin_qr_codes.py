"""One-off backfill: assign unique 5-char QR codes to bins missing them.

Layout-generated bins were persisted without a ``qr_code`` (only manually
created bins got one). This script backfills every bin whose ``qr_code`` is
NULL with a unique 5-char code, matching ``FloorPlanGeneratorService``.

Run inside the core-service container:
    python scripts/backfill_bin_qr_codes.py
"""

import random

from app.database import SessionLocal
from app.models.warehouse_location import WarehouseLocation

CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def main() -> None:
    db = SessionLocal()
    try:
        bins = (
            db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.location_type == "bin",
                WarehouseLocation.qr_code.is_(None),
            )
            .all()
        )
        if not bins:
            print("No bins missing QR codes.")
            return

        existing = {
            row[0]
            for row in db.query(WarehouseLocation.qr_code)
            .filter(WarehouseLocation.qr_code.isnot(None))
            .all()
        }

        assigned = 0
        failed = 0
        for loc in bins:
            for _ in range(10):
                code = "".join(random.choices(CHARS, k=5))
                if code not in existing:
                    existing.add(code)
                    loc.qr_code = code
                    assigned += 1
                    break
            else:
                failed += 1
                print(f"WARN: could not generate unique code for bin {loc.id}")

        db.commit()
        print(f"Assigned {assigned}/{len(bins)} QR codes ({failed} failed).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
