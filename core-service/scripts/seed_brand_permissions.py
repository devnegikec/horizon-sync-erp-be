"""Seed brand and QR product permissions into identity_db and assign admin to default org.

Run with:
    docker compose exec core-service python scripts/seed_brand_permissions.py
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings

IDENTITY_DB_URL = settings.identity_database_url

# (code, resource, action)
NEW_PERMISSIONS = [
    ("brand.create",        "brand",         "create"),
    ("brand.read",          "brand",         "read"),
    ("brand.update",        "brand",         "update"),
    ("qr_product.create",   "qr_product",    "create"),
    ("qr_product.read",     "qr_product",    "read"),
    ("qr_product.update",   "qr_product",    "update"),
    ("qr_product.delete",   "qr_product",    "delete"),
    ("pick_list.create",    "pick_list",     "create"),
    ("pick_list.read",      "pick_list",     "read"),
    ("delivery_note.create","delivery_note", "create"),
    ("delivery_note.read",  "delivery_note", "read"),
]

DEFAULT_ORG_SLUG = "default-org"
ADMIN_EMAIL = "admin@example.com"
ADMIN_ROLE_NAME = "System Administrator"


def run():
    engine = create_engine(IDENTITY_DB_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # ── 1. Resolve org and user IDs ───────────────────────────────────────
        org_row = db.execute(
            text("SELECT id FROM organizations WHERE slug = :slug LIMIT 1"),
            {"slug": DEFAULT_ORG_SLUG},
        ).fetchone()
        if not org_row:
            print(f"✗ Organization '{DEFAULT_ORG_SLUG}' not found. Run identity seed first.")
            return
        org_id = org_row[0]
        print(f"✓ Organization: {org_id}")

        user_row = db.execute(
            text("SELECT id FROM users WHERE email = :email LIMIT 1"),
            {"email": ADMIN_EMAIL},
        ).fetchone()
        if not user_row:
            print(f"✗ User '{ADMIN_EMAIL}' not found. Run identity seed first.")
            return
        user_id = user_row[0]
        print(f"✓ Admin user: {user_id}")

        role_row = db.execute(
            text("SELECT id FROM roles WHERE name = :name AND organization_id = :org_id LIMIT 1"),
            {"name": ADMIN_ROLE_NAME, "org_id": org_id},
        ).fetchone()
        if not role_row:
            print(f"✗ Role '{ADMIN_ROLE_NAME}' not found in org.")
            return
        role_id = role_row[0]
        print(f"✓ Role '{ADMIN_ROLE_NAME}': {role_id}")

        # ── 2. Insert missing permissions ─────────────────────────────────────
        print("\nSeeding permissions...")
        for code, resource, action in NEW_PERMISSIONS:
            existing = db.execute(
                text("SELECT id FROM permissions WHERE code = :code"),
                {"code": code},
            ).fetchone()
            if existing:
                perm_id = existing[0]
                print(f"  - {code} (already exists)")
            else:
                perm_id = uuid.uuid4()
                db.execute(
                    text(
                        "INSERT INTO permissions (id, code, name, description, resource, action, module, is_active, created_at, updated_at) "
                        "VALUES (:id, :code, :name, :desc, :resource, :action, :module, true, now(), now())"
                    ),
                    {
                        "id": perm_id,
                        "code": code,
                        "name": code.replace(".", " ").title(),
                        "desc": f"Permission to {action} {resource}",
                        "resource": resource,
                        "action": action,
                        "module": resource,
                    },
                )
                print(f"  + {code} (created)")

            # Assign to admin role if not already assigned
            rp_exists = db.execute(
                text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            ).fetchone()
            if not rp_exists:
                db.execute(
                    text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) "
                        "VALUES (:id, :role_id, :perm_id)"
                    ),
                    {"id": uuid.uuid4(), "role_id": role_id, "perm_id": perm_id},
                )
                print(f"    → assigned to '{ADMIN_ROLE_NAME}'")

        # ── 3. Assign admin user to default org with admin role ───────────────
        print("\nChecking admin org membership...")
        uor_exists = db.execute(
            text(
                "SELECT 1 FROM user_organization_roles "
                "WHERE user_id = :uid AND organization_id = :oid"
            ),
            {"uid": user_id, "oid": org_id},
        ).fetchone()

        if uor_exists:
            print(f"  - Admin already assigned to org (skipping)")
        else:
            db.execute(
                text(
                    "INSERT INTO user_organization_roles "
                    "(id, user_id, organization_id, role_id, is_active, is_primary, created_at, updated_at) "
                    "VALUES (:id, :uid, :oid, :rid, true, true, now(), now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "uid": user_id,
                    "oid": org_id,
                    "rid": role_id,
                },
            )
            print(f"  + Admin assigned to org '{DEFAULT_ORG_SLUG}' with role '{ADMIN_ROLE_NAME}'")

        db.commit()
        print("\n✓ Done. Admin can now access /api/v1/brands and QR endpoints.")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
