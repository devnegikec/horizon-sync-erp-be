"""Seed UOM Conversion data based on existing items and inserted UOMs.

Conversions are assigned per item based on the item's base UOM.
Only standard, universally applicable conversions are seeded.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.uom_conversion import UOMConversion

DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
ORG_ID = uuid.UUID("bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150")

# Conversion rules per UOM family:
# (from_uom, to_uom, factor)  — factor means: 1 from_uom = factor to_uom
UOM_CONVERSION_RULES = {
    # --- Quantity ---
    "PCS": [
        ("PCS", "DOZ", 0.083333),  # 1 PCS = 1/12 DOZ
        ("PCS", "UNIT", 1.0),
    ],
    "DOZ": [
        ("DOZ", "PCS", 12.0),  # 1 DOZ = 12 PCS
        ("DOZ", "UNIT", 12.0),
    ],
    "BOX": [
        ("BOX", "PCS", 12.0),  # 1 BOX = 12 PCS (common default)
        ("BOX", "CTN", 0.1),  # 10 BOX = 1 CTN
    ],
    "CTN": [
        ("CTN", "BOX", 10.0),  # 1 CTN = 10 BOX
        ("CTN", "PCS", 120.0),
    ],
    "PCK": [
        ("PCK", "PCS", 6.0),  # 1 PACK = 6 PCS (common default)
    ],
    # --- Weight ---
    "KG": [
        ("KG", "GM", 1000.0),
        ("KG", "MG", 1000000.0),
        ("KG", "MT", 0.001),
        ("KG", "LB", 2.204623),
        ("KG", "OZ", 35.273962),
    ],
    "GM": [
        ("GM", "KG", 0.001),
        ("GM", "MG", 1000.0),
        ("GM", "LB", 0.002205),
        ("GM", "OZ", 0.035274),
    ],
    "MG": [
        ("MG", "GM", 0.001),
        ("MG", "KG", 0.000001),
    ],
    "MT": [
        ("MT", "KG", 1000.0),
        ("MT", "LB", 2204.623),
    ],
    "LB": [
        ("LB", "KG", 0.453592),
        ("LB", "OZ", 16.0),
        ("LB", "GM", 453.592),
    ],
    "OZ": [
        ("OZ", "LB", 0.0625),
        ("OZ", "GM", 28.349523),
        ("OZ", "KG", 0.028350),
    ],
    # --- Volume ---
    "LTR": [
        ("LTR", "ML", 1000.0),
        ("LTR", "CBM", 0.001),
        ("LTR", "GAL", 0.264172),
    ],
    "ML": [
        ("ML", "LTR", 0.001),
        ("ML", "GAL", 0.000264),
    ],
    "CBM": [
        ("CBM", "LTR", 1000.0),
        ("CBM", "GAL", 264.172),
    ],
    "GAL": [
        ("GAL", "LTR", 3.785412),
        ("GAL", "ML", 3785.412),
    ],
    # --- Length ---
    "MTR": [
        ("MTR", "CM", 100.0),
        ("MTR", "MM", 1000.0),
        ("MTR", "KM", 0.001),
        ("MTR", "IN", 39.370079),
        ("MTR", "FT", 3.280840),
        ("MTR", "YD", 1.093613),
    ],
    "CM": [
        ("CM", "MTR", 0.01),
        ("CM", "MM", 10.0),
        ("CM", "IN", 0.393701),
        ("CM", "FT", 0.032808),
    ],
    "MM": [
        ("MM", "CM", 0.1),
        ("MM", "MTR", 0.001),
        ("MM", "IN", 0.039370),
    ],
    "KM": [
        ("KM", "MTR", 1000.0),
        ("KM", "FT", 3280.840),
    ],
    "IN": [
        ("IN", "CM", 2.54),
        ("IN", "MTR", 0.0254),
        ("IN", "FT", 0.083333),
        ("IN", "MM", 25.4),
    ],
    "FT": [
        ("FT", "IN", 12.0),
        ("FT", "MTR", 0.3048),
        ("FT", "YD", 0.333333),
        ("FT", "CM", 30.48),
    ],
    "YD": [
        ("YD", "FT", 3.0),
        ("YD", "MTR", 0.9144),
        ("YD", "IN", 36.0),
    ],
    # --- Area ---
    "SQM": [
        ("SQM", "SQF", 10.763910),
    ],
    "SQF": [
        ("SQF", "SQM", 0.092903),
    ],
}


def seed_uom_conversions():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    created = 0
    skipped = 0

    try:
        # Fetch all active items for this org
        items = db.execute(
            text("""
                SELECT id, item_code, item_name, uom
                FROM items
                WHERE organization_id = :org_id
                  AND deleted_at IS NULL
                ORDER BY item_code
            """),
            {"org_id": str(ORG_ID)},
        ).fetchall()

        if not items:
            print("✗ No items found for this organization. Seed items first.")
            return

        print(f"Found {len(items)} items. Seeding UOM conversions...\n")

        for item in items:
            item_id = item.id
            base_uom = (item.uom or "PCS").strip().upper()
            rules = UOM_CONVERSION_RULES.get(base_uom, [])

            if not rules:
                print(
                    f"  skip  {item.item_code} — no conversion rules for UOM '{base_uom}'"
                )
                continue

            for from_uom, to_uom, factor in rules:
                existing = (
                    db.query(UOMConversion)
                    .filter(
                        UOMConversion.organization_id == ORG_ID,
                        UOMConversion.item_id == item_id,
                        UOMConversion.from_uom == from_uom,
                        UOMConversion.to_uom == to_uom,
                        UOMConversion.deleted_at.is_(None),
                    )
                    .first()
                )

                if existing:
                    skipped += 1
                    continue

                conversion = UOMConversion(
                    id=uuid.uuid4(),
                    organization_id=ORG_ID,
                    item_id=item_id,
                    from_uom=from_uom,
                    to_uom=to_uom,
                    conversion_factor=factor,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                db.add(conversion)
                created += 1

            print(f"  {item.item_code} ({base_uom}) — {len(rules)} conversions queued")

        db.commit()
        print(
            f"\n✓ UOM conversion seed complete — {created} created, {skipped} skipped"
        )

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_uom_conversions()
