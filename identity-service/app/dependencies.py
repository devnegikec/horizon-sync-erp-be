"""Dependency injection for FastAPI"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models.base import UserStatus, UserType
from app.models.role import Permission, RolePermission, UserOrganizationRole
from app.repositories.user_repository import UserRepository
from app.services.core_service_client import CoreServiceClient


@dataclass
class CurrentUser:
    id: UUID
    email: str
    first_name: str
    last_name: str
    display_name: str | None
    user_type: UserType | None
    status: UserStatus | None
    is_active: bool
    permissions: list[str]


# HTTP Bearer token scheme
security = HTTPBearer()


def _get_user_permissions(db: Session, user_id: UUID) -> list[str]:
    """
    Get user's permission codes from their active roles.

    Handles potential enum issues gracefully by catching exceptions
    and returning an empty list if there are database errors.
    """
    try:
        permission_codes = (
            db.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(
                UserOrganizationRole,
                RolePermission.role_id == UserOrganizationRole.role_id,
            )
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.is_active,
                Permission.is_active == True,  # noqa: E712
            )
            .distinct()
            .all()
        )
        return [code for (code,) in permission_codes if code]
    except Exception as e:
        # Log the error but don't fail - return empty permissions
        # This prevents 500 errors if there are enum issues in permissions table
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Error fetching permissions for user {user_id}: {e}", exc_info=True
        )
        return []


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    token = credentials.credentials

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    user_repo = UserRepository(db)
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    permissions = _get_user_permissions(db, user.id)

    return CurrentUser(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        user_type=user.user_type,
        status=user.status,
        is_active=user.is_active,
        permissions=permissions,
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    return current_user


async def require_admin(
    current_user: CurrentUser = Depends(get_current_active_user),
) -> CurrentUser:
    """Require system_admin user_type for admin portal endpoints."""
    if current_user.user_type != UserType.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_client_ip(request) -> str | None:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        IP address string or None
    """
    # Check for forwarded IP (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check for real IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to client host
    if request.client:
        return request.client.host

    return None


def get_core_service_client() -> CoreServiceClient | None:
    """
    Get CoreServiceClient instance for service-to-service communication.

    Returns None if auto chart creation is disabled in settings.

    Returns:
        CoreServiceClient instance or None
    """
    if not settings.enable_auto_chart_creation:
        return None

    return CoreServiceClient(
        base_url=settings.core_service_url,
        timeout=settings.core_service_timeout
    )
