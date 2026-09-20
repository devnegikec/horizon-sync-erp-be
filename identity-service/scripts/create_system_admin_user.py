#!/usr/bin/env python3
"""Create (or reset) a fully-privileged system_admin user.

Creates a user with ``user_type = system_admin`` in the master organization and
grants it a ``super_admin`` role linked to the master permissions
(``*.*`` and ``system_admin.master``) plus every active permission in the DB.
This gives full access: manage users, organizations, billing, reporting, audit
logs — everything.

Idempotent: safe to run multiple times. If the user already exists its password
is reset and its role membership is ensured.

Credentials can be overridden via environment variables:
    SYSADMIN_EMAIL     (default: superadmin@horizonsync.com)
    SYSADMIN_PASSWORD  (default: SuperAdmin@2025)
    SYSADMIN_FIRST     (default: Super)
    SYSADMIN_LAST      (default: Admin)

Usage (inside identity-service container / image):
    python -m scripts.create_system_admin_user
"""

import os
import sys
from datetime import datetime

# Add parent directory to path so `app` is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    ActionType,
    Organization,
    OrganizationType,
    Permission,
    ResourceType,
    Role,
    RolePermission,
    User,
    UserOrganizationRole,
    UserStatus,
    UserType,
)

# --- Configurable credentials ------------------------------------------------
EMAIL = os.getenv("SYSADMIN_EMAIL", "superadmin@horizonsync.com").strip().lower()
PASSWORD = os.getenv("SYSADMIN_PASSWORD", "SuperAdmin@2025")
FIRST_NAME = os.getenv("SYSADMIN_FIRST", "Super")
LAST_NAME = os.getenv("SYSADMIN_LAST", "Admin")

ROLE_CODE = "super_admin"
ROLE_NAME = "Super Admin"


def _get_master_org(db) -> Organization:
    master = (
        db.query(Organization)
        .filter(Organization.organization_type == OrganizationType.MASTER)
        .order_by(Organization.created_at.asc())
        .first()
    )
    if not master:
        raise SystemExit(
            "❌ No master organization found. Run create_master_organization.py first."
        )
    print(f"  Master org: {master.name} ({master.id})")
    return master


def _ensure_permission(db, code, name, description) -> Permission:
    perm = db.query(Permission).filter(Permission.code == code).first()
    if not perm:
        perm = Permission(
            code=code,
            name=name,
            description=description,
            resource=ResourceType.ALL,
            action=ActionType.MANAGE,
            module="system_admin",
            is_active=True,
        )
        db.add(perm)
        db.flush()
        print(f"  Created permission: {code}")
    return perm


def _get_or_create_role(db, master_org_id) -> Role:
    role = (
        db.query(Role)
        .filter(Role.code == ROLE_CODE, Role.organization_id == master_org_id)
        .first()
    )
    if not role:
        role = Role(
            organization_id=master_org_id,
            name=ROLE_NAME,
            code=ROLE_CODE,
            description="Full system admin access — grants all permissions",
            is_system=True,
            is_default=False,
            hierarchy_level=100,
            is_active=True,
        )
        db.add(role)
        db.flush()
        print(f"  Created role: {ROLE_NAME} ({role.id})")
    else:
        print(f"  Found role: {ROLE_NAME} ({role.id})")
    return role


def _link_all_permissions(db, role) -> None:
    """Link the role to *.* , system_admin.master, and every active permission."""
    _ensure_permission(db, "*.*", "Full Access (Wildcard)",
                        "Grants access to all resources and actions")
    _ensure_permission(db, "system_admin.master", "System Admin Master",
                        "Grants access to all system admin endpoints")

    all_perms = db.query(Permission).filter(Permission.is_active == True).all()  # noqa: E712
    existing_links = {
        rp.permission_id
        for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
    }
    linked = 0
    for perm in all_perms:
        if perm.id not in existing_links:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            linked += 1
    db.flush()
    print(f"  Linked {linked} new permission(s) to role (total active: {len(all_perms)})")


def _create_or_update_user(db) -> User:
    user = db.query(User).filter(User.email == EMAIL).first()
    if user:
        user.password_hash = hash_password(PASSWORD)
        user.user_type = UserType.SYSTEM_ADMIN
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        db.flush()
        print(f"  Updated existing user: {EMAIL} (password reset)")
        return user

    user = User(
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        first_name=FIRST_NAME,
        last_name=LAST_NAME,
        display_name=f"{FIRST_NAME} {LAST_NAME}",
        user_type=UserType.SYSTEM_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    print(f"  Created user: {EMAIL} ({user.id})")
    return user


def _ensure_membership(db, user, master_org_id, role) -> None:
    uor = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user.id,
            UserOrganizationRole.organization_id == master_org_id,
            UserOrganizationRole.role_id == role.id,
        )
        .first()
    )
    if uor:
        uor.is_active = True
        uor.is_primary = True
        uor.status = "active"
        db.flush()
        print("  Membership already exists — ensured active")
        return

    db.add(
        UserOrganizationRole(
            user_id=user.id,
            organization_id=master_org_id,
            role_id=role.id,
            is_primary=True,
            is_active=True,
            status="active",
            joined_at=datetime.utcnow(),
        )
    )
    db.flush()
    print("  Created master-org role membership")


def main() -> None:
    print("🔧 Creating fully-privileged system_admin user")
    print("=" * 60)
    db = SessionLocal()
    try:
        master = _get_master_org(db)
        role = _get_or_create_role(db, master.id)
        _link_all_permissions(db, role)
        user = _create_or_update_user(db)
        _ensure_membership(db, user, master.id, role)
        db.commit()
        print("\n✅ System admin ready!")
        print("=" * 60)
        print(f"  Login email : {EMAIL}")
        print(f"  Password    : {PASSWORD}")
        print(f"  User type   : system_admin")
        print(f"  Role        : {ROLE_NAME} (full access)")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"\n❌ Failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
