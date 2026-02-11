"""User management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
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
    UserProfileResponse,
    UserResponse,
    UserSelfUpdate,
    UserStatusCounts,
    UserUpdate,
)
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

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


def _users_share_organization(db: Session, user_id: UUID, other_user_id: UUID) -> bool:
    """Return True if both users belong to at least one common organization."""
    my_orgs = set(_user_organization_ids(db, user_id))
    if not my_orgs:
        return False
    other_orgs = set(_user_organization_ids(db, other_user_id))
    return bool(my_orgs & other_orgs)


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

    Requires authentication and user.read (or user.* or *.* via wildcard).
    Users see only users from their own organization(s):
    - If organization_id query param is provided, you must be a member of that org; results are limited to that org.
    - Otherwise results are limited to all organizations the current user belongs to.
    No user can see users from organizations they do not belong to.
    """
    require_permission(current_user.permissions, "user.read")
    organization_ids: list[UUID] | None = None
    if organization_id is not None:
        validate_user_in_organization(current_user.id, organization_id, db)
        organization_ids = [organization_id]
    else:
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
            status_counts=UserStatusCounts(),
        )

    user_service = UserService(db)
    try:
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
        status_counts = user_service.get_user_status_counts(
            organization_ids=organization_ids,
            user_type=user_type,
            email_verified=email_verified,
            search=search,
        )
        user_items = [UserListItem.model_validate(user) for user in users]
        return UserListResponse(
            users=user_items,
            pagination=PaginationMeta(**pagination),
            status_counts=UserStatusCounts(**status_counts),
        )
    except Exception as e:
        logger.error(f"Error in list_users endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}",
        )


# ----- Self-service profile (logged-in user updates own info) -----
# Must be defined before /users/{user_id} so "me" is matched as literal


@router.get(
    "/users/me",
    response_model=UserProfileResponse,
    summary="Get my profile",
    description="Get current user's profile including preferences, extra_data, timezone. No permission required.",
)
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's own profile including preferences, extra_data, timezone, language.

    Any logged-in user can access their own profile. No permission required.
    """
    user_service = UserService(db)
    try:
        user = user_service.get_user_by_id(current_user.id)
        return UserProfileResponse.model_validate(user)
    except UserNotFoundException:
        raise


@router.get(
    "/users/me/permissions",
    summary="Get my permissions",
    description="Get current user's permissions within an organization for UI/navigation access control",
)
async def get_my_permissions(
    organization_id: UUID = Query(..., description="Organization ID to get permissions for"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's permissions within a specific organization.
    
    This endpoint returns all permissions the user has in the specified organization,
    allowing the frontend to determine which UI elements, navigation items, and features
    the user can access without making additional backend calls.
    
    **Query Parameters:**
    - **organization_id**: UUID of the organization to check permissions for
    
    **Response:**
    - **user_id**: User's UUID
    - **organization_id**: Organization UUID
    - **permissions**: List of permission codes the user has
    - **roles**: List of role names the user has in the organization
    - **has_access**: Boolean indicating if user has any access to the organization
    """
    from app.models.role import Permission, Role, RolePermission
    
    logger.info(f"Fetching permissions for user {current_user.id} in org {organization_id}")
    
    # Validate user is member of the organization
    try:
        validate_user_in_organization(current_user.id, organization_id, db)
    except HTTPException:
        # User is not a member of this organization
        return {
            "user_id": str(current_user.id),
            "organization_id": str(organization_id),
            "permissions": [],
            "roles": [],
            "has_access": False,
        }
    
    # Get user's roles in this organization
    user_roles = (
        db.query(Role)
        .join(UserOrganizationRole, UserOrganizationRole.role_id == Role.id)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.is_active,
            Role.is_active,
        )
        .all()
    )
    
    role_names = [role.name for role in user_roles]
    
    # Get all permissions for these roles
    permission_codes = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserOrganizationRole, RolePermission.role_id == UserOrganizationRole.role_id)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.is_active,
            Permission.is_active == True,  # noqa: E712
        )
        .distinct()
        .all()
    )
    
    permissions = [code for (code,) in permission_codes if code]
    
    logger.info(
        f"User {current_user.id} has {len(permissions)} permissions "
        f"and {len(role_names)} roles in org {organization_id}"
    )
    
    return {
        "user_id": str(current_user.id),
        "organization_id": str(organization_id),
        "permissions": permissions,
        "roles": role_names,
        "has_access": len(permissions) > 0 or len(role_names) > 0,
    }


@router.patch(
    "/users/me",
    response_model=UserProfileResponse,
    summary="Update my profile",
    description="Update current user's own profile (preferences, extra_data, timezone, etc). No permission required.",
)
async def update_my_profile(
    body: UserSelfUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's own profile.

    Allowed fields: first_name, last_name, display_name, phone, preferences, extra_data,
    timezone, language. Any logged-in user can update these. No permission required.
    """
    user_service = UserService(db)
    payload = body.model_dump(exclude_unset=True)
    try:
        user = user_service.update_user(current_user.id, payload)
        return UserProfileResponse.model_validate(user)
    except UserNotFoundException:
        raise


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
    """Get user by ID. Requires user.read (or user.* / *.*). Target user must be in your org."""
    require_permission(current_user.permissions, "user.read")
    if not _users_share_organization(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_service = UserService(db)
    try:
        user = user_service.get_user_by_id(user_id)
        return UserResponse.model_validate(user)
    except UserNotFoundException:
        raise


@router.get(
    "/users/{user_id}/permissions",
    summary="Get user permissions",
    description="Get a user's permissions within an organization; requires user.read.",
)
async def get_user_permissions(
    user_id: UUID,
    organization_id: UUID = Query(..., description="Organization ID to get permissions for"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific user's permissions within an organization.
    
    Requires user.read permission. Both the current user and target user must be
    members of the specified organization.
    
    **Path Parameters:**
    - **user_id**: UUID of the user to get permissions for
    
    **Query Parameters:**
    - **organization_id**: UUID of the organization to check permissions for
    
    **Response:**
    - **user_id**: User's UUID
    - **organization_id**: Organization UUID
    - **permissions**: List of permission codes the user has
    - **roles**: List of role names the user has in the organization
    - **has_access**: Boolean indicating if user has any access to the organization
    """
    from app.models.role import Permission, Role, RolePermission
    
    require_permission(current_user.permissions, "user.read")
    
    logger.info(f"User {current_user.id} fetching permissions for user {user_id} in org {organization_id}")
    
    # Validate current user has access to the organization
    try:
        validate_user_in_organization(current_user.id, organization_id, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization",
        )
    
    # Validate target user is in the organization
    try:
        validate_user_in_organization(user_id, organization_id, db)
    except HTTPException:
        # Target user is not a member of this organization
        return {
            "user_id": str(user_id),
            "organization_id": str(organization_id),
            "permissions": [],
            "roles": [],
            "has_access": False,
        }
    
    # Get user's roles in this organization
    user_roles = (
        db.query(Role)
        .join(UserOrganizationRole, UserOrganizationRole.role_id == Role.id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.is_active,
            Role.is_active,
        )
        .all()
    )
    
    role_names = [role.name for role in user_roles]
    
    # Get all permissions for these roles
    permission_codes = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserOrganizationRole, RolePermission.role_id == UserOrganizationRole.role_id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.is_active,
            Permission.is_active == True,  # noqa: E712
        )
        .distinct()
        .all()
    )
    
    permissions = [code for (code,) in permission_codes if code]
    
    logger.info(
        f"User {user_id} has {len(permissions)} permissions "
        f"and {len(role_names)} roles in org {organization_id}"
    )
    
    return {
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "permissions": permissions,
        "roles": role_names,
        "has_access": len(permissions) > 0 or len(role_names) > 0,
    }


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
    """Update user. Requires user.update (or user.* / *.*). Target user must be in your org."""
    require_permission(current_user.permissions, "user.update")
    if not _users_share_organization(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
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
    """Soft delete user. Requires user.delete (or user.* / *.*). Target user must be in your org."""
    require_permission(current_user.permissions, "user.delete")
    if not _users_share_organization(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_service = UserService(db)
    try:
        user_service.delete_user(user_id)
    except UserNotFoundException:
        raise
