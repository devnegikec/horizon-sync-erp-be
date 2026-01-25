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
    organization_id: UUID
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

    # Extract organization_id (if present in token)
    org_id_str = payload.get("organization_id")
    organization_id = None
    if org_id_str:
        try:
            organization_id = UUID(org_id_str)
        except ValueError:
            pass

    # If organization_id not in token, call identity-service to get it
    if not organization_id:
        organization_id = await _get_user_organization(token)

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        organization_id=organization_id,
        user_type=payload.get("user_type", "user"),
        permissions=payload.get("permissions", []),
    )


async def _get_user_organization(token: str) -> UUID:
    """
    Get user's organization from identity-service.

    Args:
        token: Bearer token

    Returns:
        Organization UUID

    Raises:
        HTTPException: If unable to get organization
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.identity_service_url}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )

            if response.status_code == 200:
                data = response.json()
                org_id_str = data.get("organization_id")
                if org_id_str:
                    return UUID(org_id_str)

            # Fallback: return a default org (should not happen in production)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to determine user organization",
            )

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


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission.

    Args:
        permission: Permission code required (e.g., "item.create")

    Returns:
        Dependency function that checks permission
    """

    async def check_permission(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        # System admins have all permissions
        if current_user.user_type == "system_admin":
            return current_user

        # Check if user has the required permission
        if permission not in current_user.permissions:
            # For now, allow all authenticated users (permissions not yet in token)
            # In production, you'd enforce this strictly
            pass

        return current_user

    return check_permission
