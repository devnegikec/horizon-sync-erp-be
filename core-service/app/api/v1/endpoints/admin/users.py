"""Admin user management endpoints.

Proxies to identity-service for user CRUD.

POST   /admin/users        — create user
GET    /admin/users        — paginated list with filters
GET    /admin/users/{id}   — detail
PATCH  /admin/users/{id}   — update
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.authorization import (
    SYSTEM_ADMIN_USERS_CREATE,
    SYSTEM_ADMIN_USERS_READ,
    SYSTEM_ADMIN_USERS_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserUpdate,
)
from app.services.admin_user_service import AdminUserService

router = APIRouter()
security = HTTPBearer()


@router.post("", response_model=AdminUserDetailResponse, status_code=201)
async def create_user(
    body: AdminUserCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_USERS_CREATE)),
) -> AdminUserDetailResponse:
    service = AdminUserService(db, token=credentials.credentials)
    return await service.create_user(body)


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    search: str | None = Query(None, description="Search by email, phone, or name"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_USERS_READ)),
) -> AdminUserListResponse:
    service = AdminUserService(db, token=credentials.credentials)
    return await service.list_users(
        organization_id=organization_id,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=AdminUserDetailResponse)
async def get_user(
    user_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_USERS_READ)),
) -> AdminUserDetailResponse:
    service = AdminUserService(db, token=credentials.credentials)
    return await service.get_user(user_id)


@router.patch("/{user_id}", response_model=AdminUserDetailResponse)
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_USERS_UPDATE)),
) -> AdminUserDetailResponse:
    service = AdminUserService(db, token=credentials.credentials)
    return await service.update_user(user_id, body)
