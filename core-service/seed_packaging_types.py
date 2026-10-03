"""Seed PackagingType master and back-fill item_packaging_units.packaging_type_id.

Run:  python seed_packaging_types.py
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.packaging_types import PackagingType

DATABASE_URL = settings.database_url
ORG_ID = uuid.UUID("bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150")

# Reusable physical packaging types. conversion_factor stays on
# item_packaging_units (how many base units fit in this pack).
DEFAULT_PACKAGING_TYPES = [
    {"code": "EACH", "name": "Each"},
    {"code": "BOX", "name": "Box"},
    {"code": "CARTON", "name": "Carton"},
    {"code": "CASE", "name": "Case"},
    {"code": "PALLET", "name": "Pallet"},
    {"code": "BAG", "name": "Bag"},
    {"code": "DRUM", "name": "Drum"},
    {"code": "BOTTLE", "name": "Bottle"},
]


def seed_packaging_types():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    created = 0
    skipped = 0

    try:
        for pt_data in DEFAULT_PACKAGING_TYPES:
            existing = (
                db.query(PackagingType)
                .filter(
                    PackagingType.organization_id == ORG_ID,
                    PackagingType.code == pt_data["code"],
                    PackagingType.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                print(f"  skip  {pt_data['code']} — already exists")
                skipped += 1
                continue
            pt = PackagingType(
                id=uuid.uuid4(),
                organization_id=ORG_ID,
                code=pt_data["code"],
                name=pt_data["name"],
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(pt)
            print(f"  create {pt_data['code']} — {pt_data['name']}")
            created += 1

        db.commit()
        print(f"\n✓ PackagingType seed complete — {created} created, {skipped} skipped")

        # Back-fill item_packaging_units.packaging_type_id by matching unit_name.
        backfilled = 0
        packaging_units = (
            db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.organization_id == ORG_ID,
                ItemPackagingUnit.packaging_type_id.is_(None),
            )
            .all()
        )
        types_by_name = {
            pt.name.upper(): pt
            for pt in db.query(PackagingType)
            .filter(PackagingType.organization_id == ORG_ID, PackagingType.deleted_at.is_(None))
            .all()
        }
        for pu in packaging_units:
            pt = types_by_name.get((pu.unit_name or "").strip().upper())
            if pt is None and pu.is_base_unit:
                pt = types_by_name.get("EACH")
            if pt is not None:
                pu.packaging_type_id = pt.id
                backfilled += 1
        db.commit()
        print(f"✓ Back-filled {backfilled} item packaging units with packaging_type_id")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_packaging_types()
