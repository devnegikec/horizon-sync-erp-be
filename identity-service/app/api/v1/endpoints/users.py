"""User management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    is_system_admin_or_owner,
    require_permission,
    validate_user_in_organization,
)
from app.core.exceptions import DuplicateEmailException, UserNotFoundException
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.base import UserType
from app.models.role import Role, UserOrganizationRole
from app.schemas.user import (
    PaginationMeta,
    UserCreate,
    UserListItem,
    UserListResponse,
    UserProfileResponse,
    UserResponse,
    UserRolesResponse,
    UserRolesUpdate,
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


def _normalize_role_name(role_name: str) -> str:
    return role_name.lower().replace("_", " ").replace("-", " ").strip()


def _user_has_owner_role(
    db: Session, user_id: UUID, organization_ids: list[UUID] | None = None
) -> bool:
    query = (
        db.query(Role.name)
        .join(UserOrganizationRole, UserOrganizationRole.role_id == Role.id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.is_active,
            Role.is_active,
        )
    )
    if organization_ids:
        query = query.filter(UserOrganizationRole.organization_id.in_(organization_ids))
    return any(
        _normalize_role_name(role_name) in {"owner", "organization owner"}
        for (role_name,) in query.all()
    )


def _is_org_admin_without_owner_role(current_user: CurrentUser, db: Session) -> bool:
    if current_user.user_type != UserType.ORGANIZATION_ADMIN:
        return False
    return not _user_has_owner_role(db, current_user.id)


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

    # Determine if caller can see system admin users
    # Only actual system_admin user_type with system_admin.master permission can see other system_admin users
    caller_is_super_admin = (
        current_user.user_type == "system_admin"
        and "system_admin.master" in current_user.permissions
    )

    # Determine if caller has cross-org user management access
    # Only actual system_admin user_type OR explicit system_admin.* permissions grant cross-org access.
    # An org owner with *.* permission within their org does NOT get cross-org access.
    has_cross_org_user_access = current_user.user_type == "system_admin" or any(
        p.startswith("system_admin.") for p in current_user.permissions
    )

    organization_ids: list[UUID] | None = None
    if organization_id is not None:
        if not has_cross_org_user_access:
            validate_user_in_organization(current_user.id, organization_id, db)
        organization_ids = [organization_id]
    elif not has_cross_org_user_access:
        organization_ids = _user_organization_ids(db, current_user.id)
    if organization_ids is not None and not organization_ids:
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

        # Isolation: hide system_admin users from non-master callers
        # system_admin.users_* holders only manage org-level users
        if not caller_is_super_admin:
            users = [u for u in users if u.user_type != UserType.SYSTEM_ADMIN]

        if _is_org_admin_without_owner_role(current_user, db):
            users = [
                u for u in users if not _user_has_owner_role(db, u.id, organization_ids)
            ]

        status_counts = user_service.get_user_status_counts(
            organization_ids=organization_ids,
            user_type=user_type,
            email_verified=email_verified,
            search=search,
        )

        # Batch-fetch org-level role names for all returned users to avoid N+1 queries.
        # We join UserOrganizationRole → Role scoped to the same organization_ids the
        # list was filtered by, so we only show roles relevant to the current org context.

        from app.models.role import Role
        from app.models.role import UserOrganizationRole as UOR

        user_ids = [u.id for u in users]
        roles_map: dict[str, list[str]] = {str(u.id): [] for u in users}

        if user_ids:
            role_rows = (
                db.query(UOR.user_id, Role.name)
                .join(Role, Role.id == UOR.role_id)
                .filter(
                    UOR.user_id.in_(user_ids),
                    UOR.is_active == True,  # noqa: E712
                    Role.is_active == True,  # noqa: E712
                    Role.code.notlike("custom_%"),
                )
            )
            # Scope to the same orgs the list was filtered by
            if organization_ids:
                role_rows = role_rows.filter(UOR.organization_id.in_(organization_ids))
            for user_id, role_name in role_rows.all():
                key = str(user_id)
                if key in roles_map:
                    roles_map[key].append(role_name)

        user_items = []
        for user in users:
            item = UserListItem.model_validate(user)
            item.roles = roles_map.get(str(user.id), [])
            user_items.append(item)

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
    organization_id: UUID = Query(
        ..., description="Organization ID to get permissions for"
    ),
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

    logger.info(
        f"Fetching permissions for user {current_user.id} in org {organization_id}"
    )

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

    role_names = [
        role.name for role in user_roles if role.code != f"custom_{current_user.id}"
    ]

    # Get all permissions for these roles
    permission_codes = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(
            UserOrganizationRole, RolePermission.role_id == UserOrganizationRole.role_id
        )
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
    has_cross_org_user_access = current_user.user_type == "system_admin" or any(
        p.startswith("system_admin.") for p in current_user.permissions
    )
    if not has_cross_org_user_access and not _users_share_organization(
        db, current_user.id, user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user_service = UserService(db)
    try:
        user = user_service.get_user_by_id(user_id)

        # Isolation: hide system_admin users from callers without system_admin.master
        if (
            user.user_type == UserType.SYSTEM_ADMIN
            and "system_admin.master" not in current_user.permissions
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

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
    organization_id: UUID = Query(
        ..., description="Organization ID to get permissions for"
    ),
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

    logger.info(
        f"User {current_user.id} fetching permissions for user {user_id} in org {organization_id}"
    )

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

    custom_code = f"custom_{user_id}"
    role_names = [role.name for role in user_roles if role.code != custom_code]

    # Custom (fine-grained) permissions come from the per-user custom role.
    custom_role_ids = [r.id for r in user_roles if r.code == custom_code]
    custom_permission_codes = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(
            RolePermission.role_id.in_(custom_role_ids),
            Permission.is_active == True,  # noqa: E712
        )
        .all()
    ) if custom_role_ids else []
    custom_permissions = [code for (code,) in custom_permission_codes if code]

    # Get all permissions for these roles
    permission_codes = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(
            UserOrganizationRole, RolePermission.role_id == UserOrganizationRole.role_id
        )
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
        "custom_permissions": custom_permissions,
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

    # Escalation guard: only callers with system_admin.master may create system_admin users
    if body.user_type and body.user_type == UserType.SYSTEM_ADMIN.value:
        if "system_admin.master" not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only users with system_admin.master permission can create system admin users",
            )

    user_service = UserService(db)
    try:
        data = body.model_dump()
        org_id = data.pop("organization_id", None)
        system_admin_role_ids = data.pop("system_admin_role_ids", None) or []
        user = user_service.create_user(data)

        # Create organization membership if org_id provided
        if org_id:
            from uuid import UUID as _UUID

            from app.models.role import Role, UserOrganizationRole

            if system_admin_role_ids:
                # Explicit role IDs provided — create one membership per role
                for idx, rid in enumerate(system_admin_role_ids):
                    membership = UserOrganizationRole(
                        user_id=user.id,
                        organization_id=org_id,
                        role_id=_UUID(rid),
                        is_primary=(idx == 0),
                    )
                    db.add(membership)
                try:
                    db.commit()
                except Exception as role_err:
                    db.rollback()
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Role assignment failed for user {user.id}: {role_err}"
                    )
            elif data.get("user_type") == "system_admin" or (
                hasattr(body, "user_type")
                and body.user_type == UserType.SYSTEM_ADMIN.value
            ):
                # System admin with no explicit roles — skip default role assignment.
                # Admin must assign roles explicitly via the UI.
                import logging

                logging.getLogger(__name__).info(
                    f"System admin user {user.id} created without role assignment — roles must be assigned explicitly"
                )
            else:
                # Regular user fallback: find a default role for this organization
                default_role = (
                    db.query(Role)
                    .filter(
                        Role.organization_id == org_id,
                        Role.is_active == True,  # noqa: E712
                    )
                    .order_by(Role.is_default.desc(), Role.created_at.asc())
                    .first()
                )

                if default_role:
                    membership = UserOrganizationRole(
                        user_id=user.id,
                        organization_id=org_id,
                        role_id=default_role.id,
                    )
                    db.add(membership)
                    db.commit()
                else:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"No role found for org {org_id} — skipping UserOrganizationRole creation"
                    )

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
    if not (
        current_user.user_type == "system_admin"
        or any(p.startswith("system_admin.") for p in current_user.permissions)
    ) and not _users_share_organization(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if _is_org_admin_without_owner_role(current_user, db) and _user_has_owner_role(
        db, user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators cannot modify organization owner accounts",
        )

    # Escalation guard: prevent user_type changes involving system_admin without system_admin.master
    payload = body.model_dump(exclude_unset=True)
    if "user_type" in payload:
        new_type = payload["user_type"]
        user_service = UserService(db)
        try:
            existing_user = user_service.get_user_by_id(user_id)
        except UserNotFoundException:
            raise

        # Case 1: promoting to system_admin
        if new_type == UserType.SYSTEM_ADMIN.value:
            if "system_admin.master" not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only users with system_admin.master permission can promote users to system admin",
                )

        # Case 2: demoting from system_admin to another type
        if (
            existing_user.user_type == UserType.SYSTEM_ADMIN
            and new_type != UserType.SYSTEM_ADMIN.value
        ):
            if "system_admin.master" not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only users with system_admin.master permission can demote system admin users",
                )

    user_service = UserService(db)
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
    if not (
        current_user.user_type == "system_admin"
        or any(p.startswith("system_admin.") for p in current_user.permissions)
    ) and not _users_share_organization(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if _is_org_admin_without_owner_role(current_user, db) and _user_has_owner_role(
        db, user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrators cannot delete organization owner accounts",
        )
    user_service = UserService(db)
    try:
        user_service.delete_user(user_id)
    except UserNotFoundException:
        raise


def _upsert_user_custom_permissions(
    db: Session, user_id: UUID, organization_id: UUID, permission_ids: list[UUID]
) -> None:
    """Store a user's fine-grained (custom) permissions on a per-user role.

    Mirrors the invitation flow: custom permissions live on a dedicated role
    with code ``custom_{user_id}``. An empty permission list deactivates the
    custom role (i.e. clears any custom permissions).
    """
    from app.models.role import Permission, RolePermission

    custom_code = f"custom_{user_id}"
    custom_role = (
        db.query(Role)
        .filter(Role.organization_id == organization_id, Role.code == custom_code)
        .first()
    )

    if not permission_ids:
        if custom_role is not None:
            custom_role.is_active = False
            db.query(UserOrganizationRole).filter(
                UserOrganizationRole.role_id == custom_role.id,
                UserOrganizationRole.user_id == user_id,
            ).update({"is_active": False})
        return

    # Only active, non-wildcard, non-platform permissions can be granted through
    # the fine-grained path. A caller with only user.update must not be able to
    # escalate a target (e.g. grant ``system_admin.master``, ``*.*``, or a
    # resource wildcard like ``user.*``).
    existing = {
        pid: code
        for pid, code in db.query(Permission.id, Permission.code)
        .filter(
            Permission.id.in_(permission_ids),
            Permission.is_active == True,  # noqa: E712
        )
        .all()
    }

    privileged = [
        code
        for code in existing.values()
        if code
        and (code == "*.*" or code.endswith(".*") or code.startswith("system_admin."))
    ]
    if privileged:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Custom permissions cannot include platform-level or wildcard "
                f"permissions: {sorted(privileged)}"
            ),
        )

    valid_ids = set(existing.keys())
    missing = set(permission_ids) - valid_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or restricted permission IDs: "
                f"{[str(m) for m in sorted(missing)]}"
            ),
        )

    if custom_role is None:
        custom_role = Role(
            organization_id=organization_id,
            name="Custom Permissions",
            code=custom_code,
            description="Fine-grained permissions assigned per user",
            is_system=False,
            is_default=False,
            is_active=True,
        )
        db.add(custom_role)
        db.flush()
    else:
        custom_role.is_active = True
        db.query(RolePermission).filter(
            RolePermission.role_id == custom_role.id
        ).delete(synchronize_session=False)

    for pid in permission_ids:
        db.add(RolePermission(role_id=custom_role.id, permission_id=pid))

    assignment = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == organization_id,
            UserOrganizationRole.role_id == custom_role.id,
        )
        .first()
    )
    if assignment is not None:
        assignment.is_active = True
    else:
        db.add(
            UserOrganizationRole(
                user_id=user_id,
                organization_id=organization_id,
                role_id=custom_role.id,
                is_primary=False,
                is_active=True,
                status="active",
            )
        )


@router.put(
    "/users/{user_id}/roles",
    response_model=UserRolesResponse,
    summary="Update user roles",
    description="Replace a user's organization roles with the provided list",
)
async def update_user_roles(
    user_id: UUID,
    body: UserRolesUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a user's roles within an organization.

    Requires authentication and 'user.update' permission.
    Deactivates all existing role assignments for the user in the specified
    organization and creates new ones for the provided role IDs.

    **Path Parameters:**
    - **user_id**: UUID of the user to update

    **Request Body:**
    - **organization_id**: UUID of the organization
    - **role_ids**: List of role UUIDs to assign (replaces existing)
    """
    require_permission(current_user.permissions, "user.update")

    if not _users_share_organization(db, current_user.id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        validate_user_in_organization(current_user.id, body.organization_id, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization",
        )

    # Verify target user is also in the organization
    target_in_org = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == body.organization_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not target_in_org:
        # Allow if caller has cross-org access, otherwise target must be in org
        has_cross_org = current_user.user_type == "system_admin" or any(
            p.startswith("system_admin.") for p in current_user.permissions
        )
        if not has_cross_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a member of this organization",
            )

    # Load requested roles and validate they belong to the org
    requested_roles = (
        (
            db.query(Role)
            .filter(
                Role.id.in_(body.role_ids) if body.role_ids else False,
                Role.organization_id == body.organization_id,
            )
            .all()
        )
        if body.role_ids
        else []
    )

    requested_role_ids = {r.id for r in requested_roles}
    missing = set(body.role_ids) - requested_role_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role IDs for this organization: {[str(r) for r in missing]}",
        )

    # Check for system roles
    system_roles = [r for r in requested_roles if r.is_system]
    if system_roles and not is_system_admin_or_owner(current_user.permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admins or organization owners can assign system roles",
        )

    # Deactivate existing role assignments for this user/org
    (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == body.organization_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .update({"is_active": False})
    )

    # Create new role assignments
    for role in requested_roles:
        existing = (
            db.query(UserOrganizationRole)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == body.organization_id,
                UserOrganizationRole.role_id == role.id,
            )
            .first()
        )
        if existing:
            existing.is_active = True
        else:
            db.add(
                UserOrganizationRole(
                    user_id=user_id,
                    organization_id=body.organization_id,
                    role_id=role.id,
                    is_primary=False,
                    is_active=True,
                )
            )

    # Apply fine-grained (custom) permissions via the per-user custom role.
    _upsert_user_custom_permissions(
        db, user_id, body.organization_id, body.custom_permission_ids
    )

    db.commit()

    # Fetch updated role names
    updated_roles = (
        db.query(Role.name)
        .join(UserOrganizationRole, UserOrganizationRole.role_id == Role.id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.organization_id == body.organization_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
            Role.is_active == True,  # noqa: E712
        )
        .all()
    )

    return UserRolesResponse(
        user_id=user_id,
        organization_id=body.organization_id,
        roles=[name for (name,) in updated_roles],
    )
