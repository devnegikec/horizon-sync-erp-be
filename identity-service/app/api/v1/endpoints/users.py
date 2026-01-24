"""User management API endpoints"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.schemas.user import PaginationMeta, UserListItem, UserListResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users with optional filters",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List users with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by user status
    - **user_type**: Filter by user type
    - **email_verified**: Filter by email verification status
    - **search**: Search term for email, first_name, last_name
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)
    """
    user_service = UserService(db)

    # Get users with filters
    users, pagination = user_service.get_users(
        page=page,
        page_size=page_size,
        status=status,
        user_type=user_type,
        email_verified=email_verified,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response schema
    user_items = [UserListItem.model_validate(user) for user in users]

    return UserListResponse(users=user_items, pagination=PaginationMeta(**pagination))
