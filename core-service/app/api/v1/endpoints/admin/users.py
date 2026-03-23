"""Admin user management endpoints.

POST   /admin/users        — create user (201, 409 for duplicate email)
GET    /admin/users        — paginated list with org_id, search, is_active filters
GET    /admin/users/{id}   — detail with organization_name (404 if not found)
PATCH  /admin/users/{id}   — update roles, is_active
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserUpdate,
)
from app.services.admin_user_service import AdminUserService

router = APIRouter()


@router.post("", response_model=AdminUserDetailResponse, status_code=201)
async def create_user(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminUserDetailResponse:
    """Create a new user in a specified organization. Returns 409 if email already exists."""
    service = AdminUserService(db)
    return service.create_user(body)


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    search: str | None = Query(None, description="Search by email, phone, or name"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminUserListResponse:
    """Return a paginated list of users across all organizations."""
    service = AdminUserService(db)
    return service.list_users(
        organization_id=organization_id,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=AdminUserDetailResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminUserDetailResponse:
    """Return full user detail with organization_name."""
    service = AdminUserService(db)
    return service.get_user(user_id)


@router.patch("/{user_id}", response_model=AdminUserDetailResponse)
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminUserDetailResponse:
    """Partially update a user's roles, is_active, or profile fields."""
    service = AdminUserService(db)
    return service.update_user(user_id, body)
