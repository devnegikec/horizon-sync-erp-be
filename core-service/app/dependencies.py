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

    org_id, permissions = await _get_user_org_and_permissions(token)

    # Regular (non-system-admin) users must belong to an organization
    if not org_id and user_type != "system_admin":
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
    Check if user has the required permission.

    Matches (in order):
    1. Exact match
    2. system_admin.master grants all system_admin.* permissions
    3. _manage expansion: system_admin.users_manage grants system_admin.users_{read,create,update,delete}
    4. Resource wildcard: resource.* grants resource.anything
    5. system_admin domain mapping: system_admin.users_read grants user.read
    """
    if not permissions or not required_permission:
        return False
    # Exact match
    if required_permission in permissions:
        return True
    # Full wildcard
    if "*.*" in permissions:
        return True
    # system_admin.master grants all system_admin.* permissions
    if required_permission.startswith("system_admin.") and "system_admin.master" in permissions:
        return True
    # _manage expansion: system_admin.users_manage grants system_admin.users_{read,create,update,delete}
    if "." in required_permission:
        resource, _, action = required_permission.partition(".")
        if "_" in action:
            domain = action.rsplit("_", 1)[0]  # e.g. "users" from "users_read"
            manage_perm = f"{resource}.{domain}_manage"
            if manage_perm in permissions:
                return True
    # Resource wildcard: resource.* grants resource.anything
    if "." in required_permission:
        resource, _, _ = required_permission.partition(".")
        if f"{resource}.*" in permissions:
            return True
    # system_admin domain → org-level resource mapping
    # e.g. required "user.read" is granted by "system_admin.users_read"
    if "." in required_permission:
        resource, _, action = required_permission.partition(".")
        _SA_RESOURCE_TO_DOMAIN = {
            "user": "users", "organization": "organizations",
            "role": "users", "permission": "users", "invitation": "users",
            "billing": "billing", "invoice": "billing", "subscription": "billing",
            "reporting": "reporting", "report": "reporting",
        }
        domain = _SA_RESOURCE_TO_DOMAIN.get(resource)
        if domain:
            if f"system_admin.{domain}_{action}" in permissions:
                return True
            if f"system_admin.{domain}_manage" in permissions:
                return True
    return False


def require_permission(*permissions: str):
    """
    Dependency factory to require at least one of the specified permissions (OR logic).
    Supports wildcards: user has resource.* or *.* to grant all actions for that resource.

    Args:
        *permissions: One or more permission codes. User needs ANY one to pass.

    Returns:
        Dependency function that raises 403 if none of the permissions are present
    """

    async def check_permission(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        if not any(has_permission(current_user.permissions, p) for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required one of: {', '.join(permissions)}",
            )
        return current_user

    return check_permission


def require_feature_flag(flag_name: str):
    """
    Dependency factory that gates an entire router/endpoint behind a feature flag.

    Returns HTTP 423 (Locked) with a structured JSON body when the flag is
    disabled or missing.  The response includes a machine-readable ``code``
    field (``FEATURE_DISABLED``) so frontends can distinguish this from
    auth errors (401/403).

    Usage:
        router = APIRouter(dependencies=[Depends(require_feature_flag("invoices_enabled"))])
    """
    from app.services.feature_flag_service import is_feature_enabled
    from app.core.constants import FEATURE_DISABLED_CODE, HTTP_FEATURE_DISABLED

    async def _check_flag(db: Session = Depends(get_db)) -> None:
        if not is_feature_enabled(flag_name, db):
            raise HTTPException(
                status_code=HTTP_FEATURE_DISABLED,
                detail={
                    "code": FEATURE_DISABLED_CODE,
                    "feature": flag_name,
                    "message": f"Feature '{flag_name}' is currently disabled by your administrator.",
                },
            )

    return _check_flag
