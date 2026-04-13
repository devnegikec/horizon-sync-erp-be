"""One-time cleanup: remove duplicate organization_admin roles and orphaned role_permissions."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()

# Delete duplicate roles (keep oldest per org)
deleted = db.execute(text("""
    DELETE FROM roles
    WHERE id IN (
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY code, organization_id ORDER BY created_at ASC) as rn
            FROM roles
            WHERE code = 'organization_admin'
        ) sub
        WHERE rn > 1
    )
"""))
print(f"Deleted {deleted.rowcount} duplicate organization_admin roles")

# Clean orphaned role_permissions
orphaned = db.execute(text("""
    DELETE FROM role_permissions
    WHERE role_id NOT IN (SELECT id FROM roles)
"""))
print(f"Deleted {orphaned.rowcount} orphaned role_permissions")

db.commit()
db.close()
print("Done")
