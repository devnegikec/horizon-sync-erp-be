"""Authorization helpers for RBAC implementation"""

import logging
from collections.abc import Callable, Sequence
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.role import UserOrganizationRole
from app.models.user import User

logger = logging.getLogger(__name__)


def validate_user_in_organization(
    user_id: UUID,
    organization_id: UUID,
    db: Session,
) -> bool:
    """
    Validate if user is a member of the specified organization.

    Args:
        user_id: User ID
        organization_id: Organization ID
        db: Database session

    Returns:
        True if user is in organization, False otherwise

    Raises:
        HTTPException: 403 Forbidden if user is not in organization
    """
    user_org = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == organization_id,
        )
        .first()
    )

    if not user_org:
        logger.warning(
            f"User {user_id} attempted to access organization {organization_id} "
            f"without membership"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this organization",
        )

    return True


def has_permission(permissions: list[str], required_permission: str) -> bool:
    """
    Check if user has the required permission, including wildcard matching.

    Permission format is resource.action (e.g. user.read, warehouse.create).
    Wildcards:
    - Exact match: user has "user.read" and required is "user.read"
    - Resource wildcard: user has "user.*" and required is "user.read" or "user.create"
    - Full wildcard: user has "*.*" grants any required permission

    Args:
        permissions: List of user permission codes (may include wildcards like user.*, *.*)
        required_permission: Required permission code (e.g. user.read)

    Returns:
        True if user has permission (exact or via wildcard), False otherwise
    """
    if not permissions or not required_permission:
        return False
    if required_permission in permissions:
        return True
    # Full wildcard is org-scoped (organization_admin role): it grants every
    # org-level permission but never platform-level system_admin.* ones.
    if "*.*" in permissions and not required_permission.startswith("system_admin."):
        return True
    if "." in required_permission:
        resource, _, _ = required_permission.partition(".")
        resource_wildcard = f"{resource}.*"
        if resource_wildcard in permissions:
            return True
    return False


def has_org_permission(permissions: list[str], required_permission: str) -> bool:
    """Org-level grant, including the ``system_admin.{domain}_{action}`` mapping.

    Use this (instead of ``has_permission``) whenever the permission is being
    evaluated against a single organization's grants, so seeded admin codes keep
    working inside their own organization.
    """
    return has_permission(permissions, required_permission) or _system_admin_grants(
        permissions, required_permission
    )


def _platform_grants(permissions: list[str]) -> list[str]:
    """Platform-level (cross-org) grants: ``system.admin`` + ``system_admin.*``."""
    return [
        perm
        for perm in permissions or ()
        if perm == "system.admin" or perm.startswith("system_admin.")
    ]


def cross_org_allows(
    permissions: list[str], required_permissions: Sequence[str]
) -> bool:
    """Whether platform grants authorise a cross-org request.

    ``system.admin`` / ``system_admin.master`` grant full access. Any other
    ``system_admin.{domain}_{action}`` grant authorises only the action it maps
    to, so ``system_admin.users_read`` must NOT authorise a write. The ``*.*``
    wildcard is organization-scoped and never counts here.
    """
    platform = _platform_grants(permissions)
    if not platform:
        return False
    if is_system_admin(platform):
        return True
    return any(_system_admin_grants(platform, code) for code in required_permissions)


def require_organization_permission(
    current_user,
    organization_id: UUID,
    required_permission: str,
) -> None:
    """Require a permission **inside one specific organization**.

    ``current_user.permissions`` is the union of the user's grants across every
    organization they belong to, so using it directly for a tenant-scoped
    operation lets a role held in organization A authorize work in organization
    B. This guard closes that gap:

    1. Platform admins (explicit ``system_admin.*``) bypass tenant scoping.
    2. The caller must be an active member of ``organization_id``.
    3. The permission must be granted by a role held *in that organization*.

    Args:
        current_user: The authenticated user context.
        organization_id: Organization the operation acts upon.
        required_permission: Permission code, e.g. ``user.update``.

    Raises:
        HTTPException: 403 when the caller is not a member or lacks the grant.
    """
    if cross_org_allows(current_user.permissions, (required_permission,)):
        return

    # A platform grant that does not map to this action is not a denial on its
    # own: the caller may well hold the permission through a role in *this*
    # organization, so fall through to the organization-scoped checks instead
    # of returning 403 before they run.
    if not current_user.organization_ids:
        # Authorization context was not populated (e.g. an older caller built
        # CurrentUser by hand) — fall back to the previous aggregate behaviour
        # rather than locking everyone out.
        check_permission(current_user.permissions, required_permission)
        return

    if not current_user.is_member_of(organization_id):
        logger.warning(
            "User %s attempted an operation on organization %s without membership",
            current_user.id,
            organization_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this organization",
        )

    # ``require_permission`` also honours the system_admin.{domain}_{action}
    # mappings, but applied to the permissions granted *in this organization*.
    require_permission(
        current_user.permissions_in(organization_id), required_permission
    )


def require_any_organization_permission(
    current_user,
    organization_id: UUID,
    required_permissions: Sequence[str],
) -> None:
    """Require **any one** of several permissions inside one organization.

    Used where an API is reachable through more than one grant — for example the
    invitation screens accept either ``user.invite`` or ``invitation.create``.
    """
    if cross_org_allows(current_user.permissions, required_permissions):
        return

    # Unmapped platform grants are not a denial by themselves — see
    # ``require_organization_permission``. The organization grant decides below.
    if not current_user.organization_ids:
        if not any(
            has_org_permission(current_user.permissions, code)
            for code in required_permissions
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Insufficient permissions. Required one of: "
                    + ", ".join(required_permissions)
                ),
            )
        return

    if not current_user.is_member_of(organization_id):
        logger.warning(
            "User %s attempted an operation on organization %s without membership",
            current_user.id,
            organization_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this organization",
        )

    org_permissions = current_user.permissions_in(organization_id)
    if any(has_org_permission(org_permissions, code) for code in required_permissions):
        return

    logger.warning(
        "Permission denied: user %s needs one of %s in organization %s",
        current_user.id,
        list(required_permissions),
        organization_id,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Insufficient permissions for this organization. Required one of: "
            + ", ".join(required_permissions)
        ),
    )


def shared_organization_ids(
    db: Session, user_id: UUID, other_user_id: UUID
) -> list[UUID]:
    """Organizations both users actively belong to."""
    mine = (
        db.query(UserOrganizationRole.organization_id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .distinct()
    )
    return [
        org_id
        for (org_id,) in db.query(UserOrganizationRole.organization_id)
        .filter(
            UserOrganizationRole.user_id == other_user_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
            UserOrganizationRole.organization_id.in_(mine.subquery().select()),
        )
        .distinct()
        .all()
    ]


def require_shared_organization_permission(
    db: Session,
    current_user,
    other_user_id: UUID,
    required_permission: str,
) -> None:
    """Require a permission in an organization shared with ``other_user_id``.

    Used by ``/users/{user_id}`` style endpoints, which identify the target by
    id only. The caller must share at least one organization with the target
    (otherwise 404, so existence is not leaked) and must hold the permission in
    one of those shared organizations.
    """
    if cross_org_allows(current_user.permissions, (required_permission,)):
        return

    # Unmapped platform grants are not a denial by themselves — the caller may
    # hold the permission in an organization shared with the target.
    shared = shared_organization_ids(db, current_user.id, other_user_id)
    if not shared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not current_user.organization_ids:
        check_permission(current_user.permissions, required_permission)
        return

    for org_id in shared:
        org_permissions = current_user.permissions_in(org_id)
        if has_permission(org_permissions, required_permission) or (
            _system_admin_grants(org_permissions, required_permission)
        ):
            return

    logger.warning(
        "Permission denied: user %s needs '%s' in an organization shared with %s",
        current_user.id,
        required_permission,
        other_user_id,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Insufficient permissions for this organization. "
            f"Required: {required_permission}"
        ),
    )


def check_permission(permissions: list[str], required_permission: str) -> bool:
    """
    Check if user has the required permission (with wildcard support).
    Raises HTTPException 403 if user lacks permission.

    Args:
        permissions: List of user permission codes
        required_permission: Required permission code

    Returns:
        True if user has permission

    Raises:
        HTTPException: 403 Forbidden if user lacks permission
    """
    if not has_permission(permissions, required_permission):
        logger.warning(
            f"Permission denied: required '{required_permission}', "
            f"user has {permissions}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {required_permission}",
        )
    return True


def is_system_admin(permissions: list[str]) -> bool:
    """
    Check if user is a system administrator with cross-org access.

    Only explicit system_admin.* permissions grant cross-org access.
    The *. * wildcard is an org-level permission (organization_admin role) and
    does NOT grant cross-org system admin access — it only grants full access
    within the user's own organization.

    Args:
        permissions: List of user permission codes

    Returns:
        True if user is system admin
    """
    return "system.admin" in permissions or "system_admin.master" in permissions


def is_system_admin_or_owner(permissions: list[str]) -> bool:
    """True for platform system admins OR organization owners (*.* wildcard).

    Organization owners have full authority within their own organization and
    may perform the same role-management operations as a system admin.
    """
    return is_system_admin(permissions) or "*.*" in permissions


def is_cross_org_admin(permissions: list[str]) -> bool:
    """
    Check if user has cross-organization administrative permissions.

    Platform grants are ``system.admin`` plus any seeded ``system_admin.*``
    permission (e.g. ``system_admin.users_read``). Both are platform-level and
    therefore tenant-agnostic; the ``*.*`` wildcard is an organization-level
    grant and must NOT be treated as cross-org access.

    Args:
        permissions: List of user permission codes

    Returns:
        True if user has cross-org admin permissions
    """
    return any(
        perm == "system.admin" or perm.startswith("system_admin.")
        for perm in permissions or ()
    )


def has_billing_admin_permission(permissions: list[str]) -> bool:
    """
    Check if user has billing administration permissions.

    Billing admin permissions (Task 1C-1):
    - system_admin.master (full system access)
    - system_admin.billing (specific billing permissions)
    - *.* (full wildcard access)

    Args:
        permissions: List of user permission codes

    Returns:
        True if user has billing admin permissions
    """
    return has_permission(permissions, "system_admin.billing") or is_system_admin(
        permissions
    )


def _system_admin_grants(permissions: list[str], required_permission: str) -> bool:
    """Check if any system_admin.* permission grants access to the required org-level permission.

    Mapping: system_admin.{domain}_{action} grants {resource}.{action}
    e.g. system_admin.users_read  → user.read
         system_admin.users_manage → user.* (all actions)
    """
    if "." not in required_permission:
        return False

    resource, _, action = required_permission.partition(".")

    # Map org-level resource names to system_admin domain names
    RESOURCE_TO_DOMAIN: dict[str, str] = {
        "user": "users",
        "organization": "organizations",
        "role": "users",  # role management falls under users domain
        "permission": "users",  # permission management falls under users domain
        "invitation": "users",  # invitation management falls under users domain
        "billing": "billing",
        "invoice": "billing",
        "subscription": "billing",
        "reporting": "reporting",
        "report": "reporting",
    }

    domain = RESOURCE_TO_DOMAIN.get(resource)
    if not domain:
        return False

    # Check exact action match: system_admin.{domain}_{action}
    sa_perm = f"system_admin.{domain}_{action}"
    if sa_perm in permissions:
        return True

    # Check _manage grants all actions for that domain
    sa_manage = f"system_admin.{domain}_manage"
    if sa_manage in permissions:
        return True

    return False


def require_permission(permissions: list[str], required_permission: str) -> None:
    """
    Require a specific permission (with wildcard support) or raise exception.

    System admins (identified by is_system_admin) bypass the check — they have
    cross-org access to identity-service resources.

    Also checks system_admin.{domain}_{action} mappings so that e.g.
    system_admin.users_read grants access to user.read endpoints.

    Args:
        permissions: List of user permission codes
        required_permission: Required permission code

    Raises:
        HTTPException: 403 Forbidden if permission missing
    """
    if is_system_admin(permissions):
        return
    if has_permission(permissions, required_permission):
        return
    if _system_admin_grants(permissions, required_permission):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied. Required: {required_permission}",
    )


def has_system_admin_permission(
    permissions: list[str], required_permission: str
) -> bool:
    """
    Check if user has system admin permission for the required resource.

    Task 1C-2: System administrators have special cross-org permissions.

    Args:
        permissions: List of user permission codes
        required_permission: Required permission code

    Returns:
        True if user has system admin permission for the resource
    """
    # Check for full system admin access
    if is_system_admin(permissions):
        return True

    # Check for specific system admin permissions
    system_admin_mappings = {
        "users.": "system_admin.users",
        "organizations.": "system_admin.organizations",
        "billing.": "system_admin.billing",
        "invoices.": "system_admin.billing",
        "subscriptions.": "system_admin.billing",
        "reporting.": "system_admin.reporting",
        "analytics.": "system_admin.reporting",
    }

    # Check if required permission falls under any system admin category
    for resource_prefix, admin_permission in system_admin_mappings.items():
        if required_permission.startswith(resource_prefix):
            if has_permission(permissions, admin_permission):
                return True

    return False


def validate_system_admin_access(
    permissions: list[str], organization_id: UUID = None
) -> bool:
    """
    Validate system admin access for cross-organization operations.

    Task 1C-2: System admins from master org can perform cross-org operations.

    Args:
        permissions: List of user permission codes
        organization_id: Organization context (if any)

    Returns:
        True if user has valid system admin access
    """
    # Must be system admin
    if not is_system_admin(permissions):
        return False

    # Must have cross-org admin permissions
    if not is_cross_org_admin(permissions):
        return False

    return True


def require_permission_dependency(
    required_permission: str, organization_id: UUID | None = None
) -> Callable:
    """
    FastAPI dependency factory to check if user has required permission.

    Task 1C-2: Enhanced with system admin validation and cross-org access.
    System admins from master organization can access cross-org operations.

    Args:
        required_permission: Permission string to check (e.g., "users.read", "billing.*")
        organization_id: Optional organization ID for context

    Returns:
        FastAPI dependency function that validates permissions

    Usage:
        @router.get("/admin/users")
        def get_all_users(
            current_user: User = Depends(require_permission_dependency("system_admin.users"))
        ):
            ...
    """

    def check_permission(
        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
    ) -> User:
        try:
            # Get user permissions from all organizations
            user_orgs = (
                db.query(UserOrganizationRole)
                .filter(
                    UserOrganizationRole.user_id == current_user.id,
                    UserOrganizationRole.is_active == True,
                )
                .all()
            )

            # Collect all permissions from all roles
            all_permissions = []
            for user_org in user_orgs:
                if user_org.role and user_org.role.permissions:
                    role_permissions = [
                        perm.permission_code for perm in user_org.role.permissions
                    ]
                    all_permissions.extend(role_permissions)

            # Check if user has the required permission
            if has_permission(all_permissions, required_permission):
                return current_user

            # For system admin users, check system admin permissions
            if current_user.user_type.value == "system_admin":
                if has_system_admin_permission(all_permissions, required_permission):
                    # Additional validation: system admin should be from master org
                    from app.services.organization_service import OrganizationService

                    org_service = OrganizationService(db)
                    master_org = org_service.get_master_organization()

                    if master_org:
                        # Check if user belongs to master organization
                        is_in_master = any(
                            role.organization_id == master_org.id for role in user_orgs
                        )
                        if is_in_master:
                            return current_user
                        else:
                            logger.warning(
                                f"System admin user {current_user.id} not in master "
                                f"organization, denying cross-org access"
                            )

            # If organization_id is specified, check within that org only
            if organization_id:
                org_permissions = []
                for user_org in user_orgs:
                    if user_org.organization_id == organization_id:
                        if user_org.role and user_org.role.permissions:
                            role_permissions = [
                                perm.permission_code
                                for perm in user_org.role.permissions
                            ]
                            org_permissions.extend(role_permissions)

                if has_permission(org_permissions, required_permission):
                    return current_user

            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_permission}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check error: {str(e)}")
            raise HTTPException(status_code=500, detail="Permission validation error")

    return check_permission
