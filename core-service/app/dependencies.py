"""Dependency injection for FastAPI"""

from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.database import get_db

# HTTP Bearer token scheme
security = HTTPBearer()


@dataclass
class CurrentUser:
    """Current authenticated user data extracted from token"""

    id: UUID
    email: str
    organization_id: UUID | None
    user_type: str
    permissions: list[str]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Get current authenticated user from JWT token.

    This validates the token locally using the shared secret key.
    For permissions, it extracts them from the token payload.

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        CurrentUser object with user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token locally (shared secret with identity-service)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user data from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Get organization_id and permissions from identity-service /me (token rarely has them)
    user_type = payload.get("user_type", "user")

    # System admins don't need org/permissions lookup — skip the identity-service call
    if user_type == "system_admin":
        return CurrentUser(
            id=user_id,
            email=payload.get("email", ""),
            organization_id=None,
            user_type=user_type,
            permissions=["*.*"],
        )

    org_id, permissions = await _get_user_org_and_permissions(token)

    # Regular users must belong to an organization
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to determine user organization",
        )

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        organization_id=org_id,
        user_type=user_type,
        permissions=permissions,
    )


async def _get_user_org_and_permissions(token: str) -> tuple[UUID | None, list[str]]:
    """
    Get user's organization_id and permissions from identity-service /me.

    Args:
        token: Bearer token

    Returns:
        Tuple of (organization_id or None, list of permission codes)

    Raises:
        HTTPException: If identity service unavailable or returns error
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.identity_service_url}/api/v1/identity/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to get user context from identity service",
                )

            data = response.json()
            org_id_str = data.get("organization_id")
            organization_id = None
            if org_id_str:
                try:
                    organization_id = UUID(org_id_str)
                except ValueError:
                    pass
            permissions = data.get("permissions") or []
            if not isinstance(permissions, list):
                permissions = []
            return organization_id, permissions

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity service unavailable",
        ) from e


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        CurrentUser object

    Raises:
        HTTPException: If user is inactive
    """
    # Basic validation - user_type check can be extended
    return current_user

async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require system_admin user_type for admin portal endpoints."""
    if current_user.user_type != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user



def has_permission(permissions: list[str], required_permission: str) -> bool:
    """
    Check if user has the required permission, including wildcard matching.

    Matches: exact permission, resource.* (e.g. warehouse.*), or *.*.
    """
    if not permissions or not required_permission:
        return False
    if required_permission in permissions:
        return True
    if "*.*" in permissions:
        return True
    if "." in required_permission:
        resource, _, _ = required_permission.partition(".")
        if f"{resource}.*" in permissions:
            return True
    return False


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission (RBAC from identity-service).
    Supports wildcards: user has resource.* or *.* to grant all actions for that resource.

    Args:
        permission: Permission code required (e.g. "item.create", "warehouse.read")

    Returns:
        Dependency function that raises 403 if permission is missing
    """

    async def check_permission(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        # System admins bypass permission check (backward compatibility)
        if current_user.user_type == "system_admin":
            return current_user
        if not has_permission(current_user.permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )
        return current_user

    return check_permission
