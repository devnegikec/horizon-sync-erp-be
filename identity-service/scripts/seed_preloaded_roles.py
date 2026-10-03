"""
Seed preloaded organization roles.

This script is IDEMPOTENT — safe to run multiple times.
It creates the 11 standard org-level roles (Owner, Administrator, Sales Agent,
Procurement Officer, Accountant, Warehouse Staff, Viewer, WMS Supervisor,
WMS Manager, WMS Operator, ASN Coordinator) for every existing organization
that doesn't already have them.

Usage:
    cd horizon-sync-erp-be
    python -m identity-service.scripts.seed_preloaded_roles

    # Or from inside the identity-service directory:
    python scripts/seed_preloaded_roles.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    ActionType,
    Organization,
    OrganizationType,
    Permission,
    ResourceType,
    Role,
    RolePermission,
)
from app.core.modules import PRELOADED_ORG_ROLES, RoleTemplate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_permission(db: Session, code: str) -> Permission | None:
    """Return existing permission by code, or None if it doesn't exist in DB."""
    return db.query(Permission).filter(Permission.code == code).first()


def _ensure_role_for_org(
    db: Session,
    org: Organization,
    template: RoleTemplate,
    permissions_map: dict[str, Permission],
) -> tuple[Role, bool]:
    """
    Ensure a role matching the template exists for the given org and that the
    role has every permission listed in the template (idempotent).

    Returns (role, created) where created=True if a new role was inserted.
    Existing roles get any missing permission links back-filled, so running
    this script after a template/permission change repairs older databases.
    """
    existing = (
        db.query(Role)
        .filter(Role.organization_id == org.id, Role.code == template.code)
        .first()
    )

    if existing is None:
        role = Role(
            organization_id=org.id,
            name=template.name,
            code=template.code,
            description=template.description,
            is_system=template.is_system,
            is_default=False,
            hierarchy_level=template.hierarchy_level,
            is_active=True,
        )
        db.add(role)
        db.flush()
        created = True
    else:
        role = existing
        created = False

    # Sync permission links (idempotent — adds missing, keeps existing).
    existing_perm_ids = {
        rp.permission_id
        for rp in db.query(RolePermission).filter(
            RolePermission.role_id == role.id
        ).all()
    }
    assigned = 0
    for code in template.permission_codes:
        perm = permissions_map.get(code)
        if perm is None:
            print(f"    ⚠  Permission '{code}' not found in DB — skipping")
            continue
        if perm.id not in existing_perm_ids:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            assigned += 1

    if created:
        print(f"    ✓ Created role + assigned {assigned} permissions: {template.name}")
    elif assigned:
        print(f"    ↻ Back-filled {assigned} missing permission(s): {template.name}")

    return role, created


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed_preloaded_roles(db: Session | None = None) -> None:
    """
    Seed preloaded org roles for all non-master organizations.
    Can be called with an existing session (for use inside other scripts)
    or will create its own session if none is provided.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        print("\n" + "=" * 60)
        print("Seeding preloaded organization roles")
        print("=" * 60)

        # Build a map of permission code → Permission object for fast lookup
        all_permissions = db.query(Permission).all()
        permissions_map: dict[str, Permission] = {p.code: p for p in all_permissions}
        print(f"Found {len(permissions_map)} permissions in DB")

        # Get all non-master organizations
        orgs = (
            db.query(Organization)
            .filter(Organization.organization_type != OrganizationType.MASTER)
            .all()
        )
        print(f"Found {len(orgs)} organization(s) to process\n")

        total_created = 0
        total_skipped = 0

        for org in orgs:
            print(f"Organization: {org.name} ({org.id})")
            for template in PRELOADED_ORG_ROLES:
                role, created = _ensure_role_for_org(db, org, template, permissions_map)
                if created:
                    print(f"  ✓ Created role: {template.name}")
                    total_created += 1
                else:
                    print(f"  · Skipped (exists): {template.name}")
                    total_skipped += 1

        if own_session:
            db.commit()

        print(f"\n{'=' * 60}")
        print(f"Done. Created: {total_created}  |  Already existed: {total_skipped}")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if own_session:
            db.rollback()
        raise
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    seed_preloaded_roles()
