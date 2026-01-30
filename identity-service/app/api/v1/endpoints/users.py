"""User management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import (
    is_system_admin,
    require_permission,
    validate_user_in_organization,
)
from app.core.exceptions import DuplicateEmailException, UserNotFoundException
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.role import UserOrganizationRole
from app.schemas.user import (
    PaginationMeta,
    UserCreate,
    UserListItem,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter()


def _user_organization_ids(db: Session, user_id: UUID) -> list[UUID]:
    """Return list of organization IDs the user is a member of."""
    rows = (
        db.query(UserOrganizationRole.organization_id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.is_active,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users; requires user.read.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    organization_id: UUID | None = Query(
        None, description="Filter by organization (requires membership)"
    ),
    status: str | None = Query(
        None, description="Filter by status (active, inactive, suspended, pending)"
    ),
    user_type: str | None = Query(
        None,
        description="Filter by user type (system_admin, organization_admin, user, guest)",
    ),
    email_verified: bool | None = Query(
        None, description="Filter by email verification status"
    ),
    search: str | None = Query(
        None, description="Search in email, first_name, last_name"
    ),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List users with pagination and filters.

    Requires authentication and user.read permission.
    If organization_id is provided, only users in that organization are returned
    (and you must be a member). If not system admin and no organization_id,
    only users from your organizations are returned.
    """
    require_permission(current_user.permissions, "user.read")
    organization_ids: list[UUID] | None = None
    if organization_id is not None:
        validate_user_in_organization(current_user.id, organization_id, db)
        organization_ids = [organization_id]
    elif not is_system_admin(current_user.permissions):
        organization_ids = _user_organization_ids(db, current_user.id)
        if not organization_ids:
            return UserListResponse(
                users=[],
                pagination=PaginationMeta(
                    page=page,
                    page_size=min(page_size, 100),
                    total_items=0,
                    total_pages=0,
                    has_next=False,
                    has_prev=False,
                ),
            )

    user_service = UserService(db)
    users, pagination = user_service.get_users(
        page=page,
        page_size=page_size,
        status=status,
        user_type=user_type,
        email_verified=email_verified,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        organization_ids=organization_ids,
    )
    user_items = [UserListItem.model_validate(user) for user in users]
    return UserListResponse(users=user_items, pagination=PaginationMeta(**pagination))


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user",
    description="Get user by ID; requires user.read.",
)
async def get_user(
    user_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user by ID. Requires user.read permission."""
    require_permission(current_user.permissions, "user.read")
    user_service = UserService(db)
    try:
        user = user_service.get_user_by_id(user_id)
        return UserResponse.model_validate(user)
    except UserNotFoundException:
        raise


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create user",
    description="Create a new user; requires user.create.",
)
async def create_user(
    body: UserCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create user. Requires user.create permission."""
    require_permission(current_user.permissions, "user.create")
    user_service = UserService(db)
    try:
        user = user_service.create_user(body.model_dump())
        return UserResponse.model_validate(user)
    except DuplicateEmailException:
        raise


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user by ID; requires user.update.",
)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user. Requires user.update permission."""
    require_permission(current_user.permissions, "user.update")
    user_service = UserService(db)
    payload = body.model_dump(exclude_unset=True)
    try:
        user = user_service.update_user(user_id, payload)
        return UserResponse.model_validate(user)
    except UserNotFoundException:
        raise


@router.delete(
    "/users/{user_id}",
    status_code=204,
    summary="Delete user",
    description="Soft-delete user; requires user.delete.",
)
async def delete_user(
    user_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Soft delete user. Requires user.delete permission."""
    require_permission(current_user.permissions, "user.delete")
    user_service = UserService(db)
    try:
        user_service.delete_user(user_id)
    except UserNotFoundException:
        raise
