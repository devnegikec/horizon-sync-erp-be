"""Authorization helpers for RBAC implementation"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.role import UserOrganizationRole

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
    Check if user is a system administrator.

    System admin has *.* or system.admin or role.manage (backward compatibility).

    Args:
        permissions: List of user permission codes

    Returns:
        True if user is system admin
    """
    return (
        "*.*" in permissions
        or "system.admin" in permissions
        or "role.manage" in permissions
    )


def require_permission(permissions: list[str], required_permission: str) -> None:
    """
    Require a specific permission (with wildcard support) or raise exception.

    Args:
        permissions: List of user permission codes
        required_permission: Required permission code

    Raises:
        HTTPException: 403 Forbidden if permission missing
    """
    if not has_permission(permissions, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required: {required_permission}",
        )
