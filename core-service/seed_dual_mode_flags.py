"""Seed tenant-scoped product/item dual-mode feature flags for existing organizations.

Run:  python seed_dual_mode_flags.py

Backfills the four dual-mode flags for every organization that does not yet
have them, with Type-1 defaults (WMS + Qseal, product auto-managed).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.feature_flag import FeatureFlag

DATABASE_URL = settings.database_url

FLAG_DEFAULTS = {
    "wms_enabled": True,
    "qseal_enabled": True,
    "product_editable_manually": False,
    "item_auto_create_product": True,
    "variant_structured_enabled": True,
    "auto_create_sku_on_item": False,
    "auto_create_variant_axes": False,
    "require_item_approval": False,
    "auto_approve_single_create": True,
}
TENANT_SCOPE = "TENANT"


def seed_dual_mode_flags():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Collect all organization IDs from the tables that use org-scoping.
        org_rows = db.execute(
            text(
                "SELECT DISTINCT organization_id FROM items WHERE deleted_at IS NULL "
                "UNION "
                "SELECT DISTINCT organization_id FROM uoms WHERE deleted_at IS NULL"
            )
        ).fetchall()
        org_ids = [row[0] for row in org_rows]

        created = 0
        skipped = 0
        now = datetime.now(UTC)

        for org_id in org_ids:
            for name, enabled in FLAG_DEFAULTS.items():
                existing = (
                    db.query(FeatureFlag)
                    .filter(
                        FeatureFlag.name == name,
                        FeatureFlag.scope == TENANT_SCOPE,
                        FeatureFlag.tenant_id == org_id,
                    )
                    .first()
                )
                if existing:
                    skipped += 1
                    continue
                db.add(
                    FeatureFlag(
                        id=uuid.uuid4(),
                        name=name,
                        description=f"Tenant-scoped product/item dual-mode flag ({name})",
                        enabled=enabled,
                        visible=True,
                        scope=TENANT_SCOPE,
                        tenant_id=org_id,
                        user_id=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                created += 1

        db.commit()
        print(
            f"\n✓ Dual-mode flags seeded for {len(org_ids)} orgs — "
            f"{created} created, {skipped} skipped"
        )

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_dual_mode_flags()
