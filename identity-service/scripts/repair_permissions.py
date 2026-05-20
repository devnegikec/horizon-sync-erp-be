"""
One-shot repair script: ensures all organization.* permissions exist and are active.

Run inside the container:
    docker exec horizon_identity python scripts/repair_permissions.py

Or from the host:
    docker exec horizon_identity python /app/scripts/repair_permissions.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from sqlalchemy import text


def repair():
    db = SessionLocal()
    try:
        print("=== Permission Repair Script ===\n")

        # 1. Show current state of organization.* permissions
        print("1. Current organization.* permissions in DB:")
        rows = db.execute(text(
            "SELECT code, resource, action, module, is_active FROM permissions "
            "WHERE code LIKE 'organization.%' OR code LIKE 'org.%' "
            "ORDER BY code"
        )).fetchall()
        if rows:
            for r in rows:
                print(f"   {r.code:40s}  resource={r.resource:15s}  action={r.action:10s}  module={r.module or 'NULL':15s}  is_active={r.is_active}")
        else:
            print("   (none found)")

        print()

        # 2. Deactivate any legacy org.* permissions
        result = db.execute(text(
            "UPDATE permissions SET is_active = false "
            "WHERE code LIKE 'org.%' AND is_active = true"
        ))
        if result.rowcount:
            print(f"2. Deactivated {result.rowcount} legacy 'org.*' permissions")
        else:
            print("2. No legacy 'org.*' permissions to deactivate")

        # 3. Upsert all organization.* permissions
        actions = [
            ("read",   "Organization Read",   "Read organizations"),
            ("create", "Organization Create", "Create organizations"),
            ("update", "Organization Update", "Update organizations"),
            ("delete", "Organization Delete", "Delete organizations"),
            ("manage", "Organization Manage", "Full organization management"),
        ]

        print("\n3. Upserting organization.* permissions:")
        for action, name, description in actions:
            code = f"organization.{action}"
            # Check if exists (active or inactive)
            existing = db.execute(text(
                "SELECT id, is_active, module FROM permissions WHERE code = :code"
            ), {"code": code}).fetchone()

            if existing:
                if not existing.is_active or existing.module != "identity":
                    db.execute(text(
                        "UPDATE permissions SET is_active = true, module = 'identity', "
                        "name = :name, description = :description, updated_at = NOW() "
                        "WHERE code = :code"
                    ), {"code": code, "name": name, "description": description})
                    print(f"   UPDATED  {code}  (was is_active={existing.is_active}, module={existing.module})")
                else:
                    print(f"   OK       {code}  (already active, module=identity)")
            else:
                db.execute(text("""
                    INSERT INTO permissions
                        (id, code, name, description, resource, action, module, is_active, created_at, updated_at, extra_data)
                    VALUES
                        (gen_random_uuid(), :code, :name, :description,
                         'organization', :action, 'identity', true, NOW(), NOW(), '{}')
                """), {"code": code, "name": name, "description": description, "action": action})
                print(f"   CREATED  {code}")

        db.commit()

        # 4. Verify final state
        print("\n4. Final state of organization.* permissions:")
        rows = db.execute(text(
            "SELECT code, resource, action, module, is_active FROM permissions "
            "WHERE code LIKE 'organization.%' "
            "ORDER BY code"
        )).fetchall()
        for r in rows:
            status = "✓" if r.is_active else "✗"
            print(f"   {status} {r.code:40s}  module={r.module or 'NULL':15s}  is_active={r.is_active}")

        # 5. Show all active identity permissions
        print("\n5. All active permissions with module='identity':")
        rows = db.execute(text(
            "SELECT code, resource, action, is_active FROM permissions "
            "WHERE module = 'identity' AND is_active = true "
            "ORDER BY resource, action"
        )).fetchall()
        for r in rows:
            print(f"   {r.code:40s}  resource={r.resource:15s}  action={r.action}")

        print("\n=== Repair complete ===")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    repair()
