"""Authorization helpers for RBAC implementation"""

import logging
from typing import Callable, Optional
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
    if "*.*" in permissions:
        return True
    if "." in required_permission:
        resource, _, _ = required_permission.partition(".")
        resource_wildcard = f"{resource}.*"
        if resource_wildcard in permissions:
            return True
    return False


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
    return (
        "system.admin" in permissions
        or "system_admin.master" in permissions
    )


def is_system_admin_or_owner(permissions: list[str]) -> bool:
    """True for platform system admins OR organization owners (*.* wildcard).

    Organization owners have full authority within their own organization and
    may perform the same role-management operations as a system admin.
    """
    return is_system_admin(permissions) or "*.*" in permissions


def is_cross_org_admin(permissions: list[str]) -> bool:
    """
    Check if user has cross-organization administrative permissions.

    Only explicit system_admin.* permissions grant cross-org access.
    The *. * wildcard is org-scoped and does NOT grant cross-org access.

    Args:
        permissions: List of user permission codes

    Returns:
        True if user has cross-org admin permissions
    """
    cross_org_permissions = [
        "system_admin.master",
        "system_admin.users",
        "system_admin.organizations",
        "system_admin.billing",
        "system_admin.reporting",
    ]
    return any(perm in permissions for perm in cross_org_permissions)


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
    return has_permission(permissions, "system_admin.billing") or is_system_admin(permissions)


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
        "role": "users",          # role management falls under users domain
        "permission": "users",    # permission management falls under users domain
        "invitation": "users",    # invitation management falls under users domain
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


def has_system_admin_permission(permissions: list[str], required_permission: str) -> bool:
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
        "analytics.": "system_admin.reporting"
    }
    
    # Check if required permission falls under any system admin category
    for resource_prefix, admin_permission in system_admin_mappings.items():
        if required_permission.startswith(resource_prefix):
            if has_permission(permissions, admin_permission):
                return True
    
    return False


def validate_system_admin_access(permissions: list[str], organization_id: UUID = None) -> bool:
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


def require_permission_dependency(required_permission: str, organization_id: Optional[UUID] = None) -> Callable:
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
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> User:
        try:
            # Get user permissions from all organizations
            user_orgs = (
                db.query(UserOrganizationRole)
                .filter(
                    UserOrganizationRole.user_id == current_user.id,
                    UserOrganizationRole.is_active == True
                )
                .all()
            )
            
            # Collect all permissions from all roles
            all_permissions = []
            for user_org in user_orgs:
                if user_org.role and user_org.role.permissions:
                    role_permissions = [perm.permission_code for perm in user_org.role.permissions]
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
                            role_permissions = [perm.permission_code for perm in user_org.role.permissions]
                            org_permissions.extend(role_permissions)
                
                if has_permission(org_permissions, required_permission):
                    return current_user
            
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Permission validation error"
            )
    
    return check_permission
