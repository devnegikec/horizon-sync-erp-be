#!/usr/bin/env python3
"""
Script to check if a user has *.* permission in a specific organization,
and assign it if missing.

Usage:
    python scripts/check_and_assign_permission.py <user_id> <org_id>
"""

import sys
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.role import Permission, Role, RolePermission, UserOrganizationRole


def check_user_permission_in_org(
    db: Session, user_id: UUID, organization_id: UUID
) -> tuple[bool, list[str], list[Role]]:
    """
    Check if user has *.* permission in the specified organization.

    Returns:
        Tuple of (has_full_access, list of permission codes, list of roles)
    """
    # Get user's roles in this organization
    user_org_roles = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .all()
    )

    if not user_org_roles:
        return False, [], []

    role_ids = [uor.role_id for uor in user_org_roles]
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()

    # Get all permissions for these roles
    permission_codes = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(
            RolePermission.role_id.in_(role_ids),
            Permission.is_active == True,  # noqa: E712
        )
        .distinct()
        .all()
    )

    codes = [code for (code,) in permission_codes]
    has_full_access = "*.*" in codes

    return has_full_access, codes, roles


def assign_full_access_to_user(
    db: Session, user_id: UUID, organization_id: UUID
) -> dict:
    """
    Assign *.* permission to user in the specified organization.

    Strategy:
    1. Check if user has any role in the org
    2. If yes, get the first active role and assign *.* to it
    3. If no role exists, create an "Owner" role with *.* and assign user to it
    """
    # Get or create *.* permission
    full_access_perm = db.query(Permission).filter(Permission.code == "*.*").first()

    if not full_access_perm:
        # Create *.* permission if it doesn't exist
        from app.models.base import ActionType, ResourceType

        full_access_perm = Permission(
            code="*.*",
            name="Full access (all resources and actions)",
            description="Grants all permissions across all resources",
            resource=ResourceType.ALL,
            action=ActionType.MANAGE,
            is_active=True,
        )
        db.add(full_access_perm)
        db.commit()
        db.refresh(full_access_perm)
        print(f"Created *.* permission: {full_access_perm.id}")

    # Check if user has any role in this org
    user_org_role = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .first()
    )

    if user_org_role:
        # User has a role - assign *.* to that role
        role = db.query(Role).filter(Role.id == user_org_role.role_id).first()
        if not role:
            raise ValueError(f"Role {user_org_role.role_id} not found")

        # Check if role already has *.* permission
        existing_rp = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == full_access_perm.id,
            )
            .first()
        )

        if existing_rp:
            return {
                "status": "already_assigned",
                "message": f"*.* permission already assigned to role '{role.name}' ({role.code})",
                "role_id": str(role.id),
                "role_name": role.name,
                "permission_id": str(full_access_perm.id),
            }

        # Assign *.* to the role
        role_permission = RolePermission(
            role_id=role.id, permission_id=full_access_perm.id
        )
        db.add(role_permission)
        db.commit()
        db.refresh(role_permission)

        return {
            "status": "assigned",
            "message": f"Assigned *.* permission to existing role '{role.name}' ({role.code})",
            "role_id": str(role.id),
            "role_name": role.name,
            "role_code": role.code,
            "permission_id": str(full_access_perm.id),
            "role_permission_id": str(role_permission.id),
        }
    else:
        # User has no role - create Owner role and assign user to it
        from app.models.base import ActionType, ResourceType

        # Check if Owner role already exists in this org
        owner_role = (
            db.query(Role)
            .filter(
                Role.organization_id == organization_id,
                Role.code == "owner",
            )
            .first()
        )

        if not owner_role:
            # Create Owner role
            owner_role = Role(
                organization_id=organization_id,
                name="Organization Owner",
                code="owner",
                description="Full access to all resources in the organization",
                is_system=False,
                is_default=False,
                is_active=True,
            )
            db.add(owner_role)
            db.commit()
            db.refresh(owner_role)
            print(f"Created Owner role: {owner_role.id}")

        # Assign *.* permission to Owner role
        existing_rp = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == owner_role.id,
                RolePermission.permission_id == full_access_perm.id,
            )
            .first()
        )

        if not existing_rp:
            role_permission = RolePermission(
                role_id=owner_role.id, permission_id=full_access_perm.id
            )
            db.add(role_permission)
            db.commit()

        # Assign user to Owner role
        user_org_role = UserOrganizationRole(
            user_id=user_id,
            organization_id=organization_id,
            role_id=owner_role.id,
            is_primary=True,
            is_active=True,
            status="active",
        )
        db.add(user_org_role)
        db.commit()
        db.refresh(user_org_role)

        return {
            "status": "created_and_assigned",
            "message": "Created Owner role and assigned user to it with *.* permission",
            "role_id": str(owner_role.id),
            "role_name": owner_role.name,
            "role_code": owner_role.code,
            "permission_id": str(full_access_perm.id),
            "user_org_role_id": str(user_org_role.id),
        }


def _parse_args() -> tuple[UUID, UUID]:
    """Parse command line arguments."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/check_and_assign_permission.py <user_id> <org_id>")
        sys.exit(1)

    try:
        user_id = UUID(sys.argv[1])
        org_id = UUID(sys.argv[2])
        return user_id, org_id
    except ValueError as e:
        print(f"Error: Invalid UUID format - {e}")
        sys.exit(1)


def _display_status(
    user_id: UUID, org_id: UUID, has_access: bool, permissions: list[str], roles: list
):
    """Display current permission status for the user."""
    print(f"\n{'='*60}")
    print(f"User ID: {user_id}")
    print(f"Organization ID: {org_id}")
    print(f"{'='*60}\n")

    if not roles:
        print("❌ User has NO roles in this organization")
    elif has_access:
        print("✅ User HAS *.* permission in this organization")
        print(f"\nRoles ({len(roles)}):")
        for role in roles:
            print(f"  - {role.name} ({role.code})")
        print(f"\nPermissions ({len(permissions)}):")
        for perm in sorted(permissions):
            marker = " ⭐" if perm == "*.*" else ""
            print(f"  - {perm}{marker}")
    else:
        print("❌ User does NOT have *.* permission")
        print(f"\nCurrent roles ({len(roles)}):")
        for role in roles:
            print(f"  - {role.name} ({role.code})")
        print(f"\nCurrent permissions ({len(permissions)}):")
        for perm in sorted(permissions):
            print(f"  - {perm}")


def _assign_and_verify(db: Session, user_id: UUID, org_id: UUID):
    """Assign full access and verify the assignment."""
    print("\nAssigning *.* permission...")
    result = assign_full_access_to_user(db, user_id, org_id)
    print(f"\n✅ {result['message']}")
    print(f"   Role: {result.get('role_name', 'N/A')} ({result.get('role_code', 'N/A')})")
    print(f"   Permission ID: {result['permission_id']}")

    # Verify
    has_access_after, _, _ = check_user_permission_in_org(db, user_id, org_id)
    if has_access_after:
        print("\n✅ Verification: User now has *.* permission")
    else:
        print("\n❌ Verification failed: User still does not have *.* permission")


def main():
    user_id, org_id = _parse_args()

    db = SessionLocal()
    try:
        # Check current status
        has_access, permissions, roles = check_user_permission_in_org(
            db, user_id, org_id
        )

        _display_status(user_id, org_id, has_access, permissions, roles)

        if not roles or not has_access:
            _assign_and_verify(db, user_id, org_id)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
