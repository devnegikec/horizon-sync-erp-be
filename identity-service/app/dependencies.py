"""Dependency injection for FastAPI"""

import secrets
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models.base import UserStatus, UserType
from app.models.role import Permission, Role, RolePermission, UserOrganizationRole
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
    # Organization-scoped authorization context. ``permissions`` above is the
    # union of every organization's grants, which is only safe for operations
    # that are not tied to a single tenant. Anything that touches one
    # organization MUST resolve permissions through ``permissions_in()`` so a
    # role held in organization A never authorizes access to organization B.
    organization_permissions: dict[str, list[str]] = field(default_factory=dict)
    organization_ids: list[str] = field(default_factory=list)

    def is_member_of(self, organization_id: UUID | str) -> bool:
        """True when the user holds an active membership in the organization."""
        return str(organization_id) in self.organization_permissions

    def permissions_in(self, organization_id: UUID | str) -> list[str]:
        """Permission codes granted to the user *inside* one organization."""
        return self.organization_permissions.get(str(organization_id), [])


# HTTP Bearer token scheme
security = HTTPBearer()


def _get_organization_permissions(
    db: Session, user_id: UUID
) -> tuple[dict[str, list[str]], list[str]]:
    """Map every organization the user belongs to onto its permission codes.

    Returns ``(mapping, organization_ids)`` where ``mapping`` contains an entry
    for **every active membership** — including organizations where the user has
    no role, which resolves to an empty list. That distinction matters: an empty
    list means "member without permissions" while a missing key means "not a
    member", and the organization guard needs to tell them apart.
    """
    try:
        memberships = (
            db.query(UserOrganizationRole.organization_id)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.is_active == True,  # noqa: E712
            )
            .distinct()
            .all()
        )
        mapping: dict[str, list[str]] = {str(org_id): [] for (org_id,) in memberships}

        rows = (
            db.query(UserOrganizationRole.organization_id, Permission.code)
            .join(Role, Role.id == UserOrganizationRole.role_id)
            .join(
                RolePermission, RolePermission.role_id == UserOrganizationRole.role_id
            )
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.is_active == True,  # noqa: E712
                Role.is_active == True,  # noqa: E712
                Permission.is_active == True,  # noqa: E712
            )
            .distinct()
            .all()
        )
        for org_id, code in rows:
            if code:
                mapping.setdefault(str(org_id), []).append(code)

        return mapping, sorted(mapping)
    except Exception:  # noqa: BLE001 — never break authentication on a lookup error
        import logging

        logging.getLogger(__name__).error(
            "Error fetching organization permissions for user %s",
            user_id,
            exc_info=True,
        )
        return {}, []


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

    organization_permissions, organization_ids = _get_organization_permissions(
        db, user.id
    )
    # The union is derived from the per-organization map, so only one extra
    # round-trip is needed per request.
    permissions = sorted(
        {code for codes in organization_permissions.values() for code in codes}
    )

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
        organization_permissions=organization_permissions,
        organization_ids=organization_ids,
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


async def require_internal_service(
    x_internal_secret: str = Header(None, alias="X-Internal-Secret"),
) -> None:
    """Guard service-to-service endpoints with the shared internal secret.

    Mirrors core-service's ``require_internal_service``. Callers (core-service)
    must send ``X-Internal-Secret``.
    """
    expected = settings.internal_service_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal service secret not configured",
        )
    if not x_internal_secret or not secrets.compare_digest(x_internal_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal service secret",
        )


def require_permission(permission: str):
    """Create dependency that requires specific permission for access

    Args:
        permission: Permission code required (e.g., 'system_admin.org_manager')

    Returns:
        Dependency function that validates user has the required permission
    """

    async def _require_permission(
        current_user: CurrentUser = Depends(get_current_active_user),
    ) -> CurrentUser:
        """Check if current user has the required permission"""

        # Check for exact permission match
        if permission in current_user.permissions:
            return current_user

        # Organization Owner has the full organization-scoped wildcard.
        # Keep this aligned with core-service and app.core.authorization so
        # owners are not incorrectly denied permissions such as warehouse.read.
        # The wildcard is organization-scoped: platform-level ``system_admin.*``
        # codes gate cross-organization data (admin-user listing, organization
        # deactivation) and must never be satisfied by an org-scoped owner.
        if "*.*" in current_user.permissions and not permission.startswith(
            "system_admin."
        ):
            return current_user

        # system_admin.master grants all system_admin.* permissions
        if (
            permission.startswith("system_admin.")
            and "system_admin.master" in current_user.permissions
        ):
            return current_user

        # _manage expansion: system_admin.users_manage grants system_admin.users_{read,create,update,delete}
        if "." in permission:
            resource, _, action = permission.partition(".")
            if "_" in action:
                domain = action.rsplit("_", 1)[0]  # e.g. "users" from "users_read"
                manage_perm = f"{resource}.{domain}_manage"
                if manage_perm in current_user.permissions:
                    return current_user

        # Check for partial wildcard matches (e.g., 'resource.*' matches 'resource.anything')
        if "." in permission:
            resource, _, _ = permission.partition(".")
            if f"{resource}.*" in current_user.permissions:
                return current_user

        # Permission not found
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required",
        )

    return _require_permission


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

    Used for organization onboarding (currency seeding, UOMs, tax templates, item groups)
    and optionally for chart of accounts creation.

    Returns:
        CoreServiceClient instance or None if core_service_url is not configured
    """
    if not settings.core_service_url:
        return None

    return CoreServiceClient(
        base_url=settings.core_service_url, timeout=settings.core_service_timeout
    )
