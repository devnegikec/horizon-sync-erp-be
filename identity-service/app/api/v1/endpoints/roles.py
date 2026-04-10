"""Role management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    is_system_admin,
    require_permission,
    validate_user_in_organization,
)
from app.core.exceptions import (
    DuplicateRoleException,
    PermissionNotFoundException,
    RoleHasUsersException,
    RoleNotFoundException,
    RolePermissionAlreadyAssignedException,
    RolePermissionNotFoundException,
    SystemRoleModificationException,
)
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.role import UserOrganizationRole
from app.schemas.role import (
    BulkAssignRolePermissionsRequest,
    RoleCreate,
    RoleListResponse,
    RolePermissionCreate,
    RolePermissionDetailResponse,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdate,
    RoleUsersListResponse,
)
from app.services.role_service import RoleService

router = APIRouter()
logger = logging.getLogger(__name__)


def _user_organization_ids(db: Session, user_id: UUID) -> list[UUID]:
    """Return list of organization IDs the user is a member of."""
    rows = (
        db.query(UserOrganizationRole.organization_id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@router.get(
    "/roles",
    response_model=RoleListResponse,
    summary="List roles",
    description="Get paginated list of roles with optional filters",
)
async def list_roles(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_system: bool | None = Query(None, description="Filter by system role flag"),
    search: str | None = Query(None, description="Search in code or name"),
    include_permissions: bool = Query(False, description="Include permissions"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List roles with pagination and filters.

    Requires authentication and 'role.read' permission.

    **Query Parameters:**
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum records to return (default: 10, max: 100)
    - **organization_id**: Filter by organization
    - **is_active**: Filter by active status
    - **is_system**: Filter by system role flag
    - **search**: Search term for code or name
    - **include_permissions**: Include permissions in response
    """
    logger.info(
        f"User {current_user.id} listing roles - "
        f"skip: {skip}, limit: {limit}, org_id: {organization_id}"
    )

    # Check permission - user must have role.read (or role.* or *.*)
    require_permission(current_user.permissions, "role.read")

    # Restrict to user's organizations only - never return roles from other orgs
    organization_ids: list[UUID] | None = None
    if organization_id is not None:
        # Specific org requested: validate user is a member
        validate_user_in_organization(current_user.id, organization_id, db)
        organization_ids = [organization_id]
    else:
        # No org specified: restrict to user's own organizations
        organization_ids = _user_organization_ids(db, current_user.id)
        if not organization_ids:
            # User has no org membership - return empty list
            return RoleListResponse(
                data=[],
                total=0,
                skip=skip,
                limit=limit,
            )

    # Non-system-admin users should never see roles from the master organization
    # (those are system admin roles like Super Admin, System User Manager, etc.)
    if not is_system_admin(current_user.permissions) and organization_ids:
        from app.models.organization import Organization
        from app.models.base import OrganizationType
        master_org_ids = {
            row[0] for row in
            db.query(Organization.id)
            .filter(
                Organization.organization_type == OrganizationType.MASTER,
                Organization.id.in_(organization_ids),
            )
            .all()
        }
        if master_org_ids:
            organization_ids = [oid for oid in organization_ids if oid not in master_org_ids]
            if not organization_ids:
                return RoleListResponse(data=[], total=0, skip=skip, limit=limit)

    role_service = RoleService(db)

    try:
        result = role_service.list_roles(
            organization_ids=organization_ids,
            skip=skip,
            limit=limit,
            is_active=is_active,
            is_system=is_system,
            search=search,
            include_permissions=include_permissions,
        )

        # Non-system-admin users: filter out roles that only have system_admin.* permissions
        # These are system admin roles that leaked into the user's org
        if not is_system_admin(current_user.permissions) and result.get("data"):
            from app.models.role import Permission, RolePermission, Role as RoleModel
            filtered_data = []
            for role_item in result["data"]:
                role_id = role_item.id if hasattr(role_item, "id") else role_item.get("id")
                if role_id:
                    # Check if ALL permissions for this role are system_admin.*
                    perm_codes = (
                        db.query(Permission.code)
                        .join(RolePermission, RolePermission.permission_id == Permission.id)
                        .filter(RolePermission.role_id == role_id)
                        .all()
                    )
                    codes = [c[0] for c in perm_codes if c[0]]
                    # If role has permissions and ALL are system_admin.*, skip it
                    if codes and all(c.startswith("system_admin.") for c in codes):
                        continue
                filtered_data.append(role_item)
            result["data"] = filtered_data

        logger.info(f"User {current_user.id} retrieved {len(result['data'])} roles")

        return RoleListResponse(**result)

    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles",
        )


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Get role",
    description="Get a specific role by ID",
)
async def get_role(
    role_id: UUID,
    include_permissions: bool = Query(False, description="Include permissions"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific role by ID.

    Requires authentication and 'role.read' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Query Parameters:**
    - **include_permissions**: Include permissions in response
    """
    logger.info(f"User {current_user.id} fetching role: {role_id}")

    # Check permission
    require_permission(current_user.permissions, "role.read")

    role_service = RoleService(db)

    try:
        result = role_service.get_role_by_id(
            role_id,
            include_permissions=include_permissions,
        )

        # Validate organization membership
        validate_user_in_organization(current_user.id, result["organization_id"], db)

        logger.info(f"User {current_user.id} fetched role: {role_id}")
        return RoleResponse(**result)

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error fetching role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role",
        )


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description="Create a new role",
)
async def create_role(
    role: RoleCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new role with optional permissions in one step.

    Requires authentication and 'role.create' permission.

    **Request Body:**
    - **organization_id**: Organization UUID (required)
    - **name**: Role name
    - **code**: Unique role code
    - **description**: Optional description
    - **permission_ids**: Optional list of permission UUIDs to assign
    - **is_system**: System role flag (default: false)
    - **is_default**: Default role flag (default: false)
    - **hierarchy_level**: Hierarchy level (default: 0)
    - **is_active**: Active status (default: true)
    - **extra_data**: Optional metadata
    """
    logger.info(
        f"User {current_user.id} creating role: {role.code} "
        f"in org: {role.organization_id}"
    )

    # Check permission
    require_permission(current_user.permissions, "role.create")

    # Validate user is in the organization
    validate_user_in_organization(current_user.id, role.organization_id, db)

    role_service = RoleService(db)

    try:
        result = role_service.create_role(
            role.model_dump(exclude={"organization_id"}),
            role.organization_id,
        )
        logger.info(
            f"User {current_user.id} created role: {result['id']} "
            f"in org: {role.organization_id}"
        )
        return RoleResponse(**result)

    except DuplicateRoleException as e:
        logger.warning(f"User {current_user.id}: Duplicate role code: {role.code}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error creating role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role",
        )


@router.put(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
    description="Update an existing role",
)
async def update_role(
    role_id: UUID,
    role: RoleUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a role.

    Requires authentication and 'role.update' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Request Body:**
    - **name**: Optional new name
    - **description**: Optional new description
    - **hierarchy_level**: Optional hierarchy level
    - **is_active**: Optional active status
    - **extra_data**: Optional metadata
    """
    logger.info(f"User {current_user.id} updating role: {role_id}")

    # Check permission
    require_permission(current_user.permissions, "role.update")

    role_service = RoleService(db)

    try:
        # Get role first to validate org membership and system role check
        existing_role = role_service.get_role_by_id(role_id)

        # Validate organization membership
        validate_user_in_organization(
            current_user.id, existing_role["organization_id"], db
        )

        # Check if trying to modify system role
        if existing_role["is_system"] and not is_system_admin(current_user.permissions):
            logger.warning(
                f"User {current_user.id} attempted to modify system role {role_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles",
            )

        result = role_service.update_role(
            role_id,
            role.model_dump(exclude_unset=True),
        )
        logger.info(f"User {current_user.id} updated role: {role_id}")
        return RoleResponse(**result)

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SystemRoleModificationException as e:
        logger.warning(f"User {current_user.id}: Cannot modify system role: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error updating role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role",
        )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
    description="Delete a role",
)
async def delete_role(
    role_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a role.

    Requires authentication and 'role.delete' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role
    """
    logger.info(f"User {current_user.id} deleting role: {role_id}")

    # Check permission
    require_permission(current_user.permissions, "role.delete")

    role_service = RoleService(db)

    try:
        # Get role first to validate org membership
        existing_role = role_service.get_role_by_id(role_id)

        # Validate organization membership
        validate_user_in_organization(
            current_user.id, existing_role["organization_id"], db
        )

        # Check if trying to delete system role
        if existing_role["is_system"] and not is_system_admin(current_user.permissions):
            logger.warning(
                f"User {current_user.id} attempted to delete system role {role_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system roles",
            )

        role_service.delete_role(role_id)
        logger.info(f"User {current_user.id} deleted role: {role_id}")

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SystemRoleModificationException as e:
        logger.warning(f"User {current_user.id}: Cannot delete system role: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except RoleHasUsersException as e:
        logger.warning(
            f"User {current_user.id}: Cannot delete role {role_id}: has active users"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete role",
        )


@router.get(
    "/roles/{role_id}/permissions",
    summary="Get role permissions",
    description="Get permissions for a specific role",
)
async def get_role_permissions(
    role_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    resource: str | None = Query(None, description="Filter by resource type"),
    action: str | None = Query(None, description="Filter by action type"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get permissions assigned to a role.

    Requires authentication and 'role.read' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Query Parameters:**
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **resource**: Filter by resource type
    - **action**: Filter by action type
    """
    logger.info(f"User {current_user.id} fetching permissions for role: {role_id}")

    # Check permission
    require_permission(current_user.permissions, "role.read")

    role_service = RoleService(db)

    try:
        # Get role to validate org membership
        existing_role = role_service.get_role_by_id(role_id)
        validate_user_in_organization(
            current_user.id, existing_role["organization_id"], db
        )

        result = role_service.get_role_permissions(
            role_id,
            skip=skip,
            limit=limit,
            resource=resource,
            action=action,
        )

        logger.info(
            f"User {current_user.id} retrieved {len(result['data'])} permissions for role"
        )

        return {
            "data": [RolePermissionDetailResponse(**item) for item in result["data"]],
            "total": result["total"],
            "skip": result["skip"],
            "limit": result["limit"],
        }

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error fetching role permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role permissions",
        )


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RolePermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign permission to role",
    description="Assign a permission to a role",
)
async def assign_permission_to_role(
    role_id: UUID,
    permission: RolePermissionCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Assign a permission to a role.

    Requires authentication and 'role.manage' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Request Body:**
    - **permission_id**: UUID of the permission
    - **conditions**: Optional conditions dictionary
    """
    logger.info(
        f"User {current_user.id} assigning permission {permission.permission_id} "
        f"to role {role_id}"
    )

    # Check permission
    require_permission(current_user.permissions, "role.manage")

    role_service = RoleService(db)

    try:
        # Get role to validate org membership and system role
        existing_role = role_service.get_role_by_id(role_id)
        validate_user_in_organization(
            current_user.id, existing_role["organization_id"], db
        )

        # Check if trying to modify system role
        if existing_role["is_system"] and not is_system_admin(current_user.permissions):
            logger.warning(
                f"User {current_user.id} attempted to modify system role {role_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles unless you are a system admin",
            )

        result = role_service.assign_permission_to_role(
            role_id,
            permission.permission_id,
            permission.conditions,
        )

        logger.info(
            f"User {current_user.id} assigned permission {permission.permission_id} "
            f"to role {role_id}"
        )

        return RolePermissionResponse(**result)

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except PermissionNotFoundException as e:
        logger.warning(f"Permission not found: {permission.permission_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SystemRoleModificationException as e:
        logger.warning(f"Cannot modify system role: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except RolePermissionAlreadyAssignedException as e:
        logger.warning(
            f"Permission {permission.permission_id} already assigned to role {role_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error assigning permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign permission",
        )


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove permission from role",
    description="Remove a permission from a role",
)
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Remove a permission from a role.

    Requires authentication and 'role.manage' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role
    - **permission_id**: UUID of the permission
    """
    logger.info(
        f"User {current_user.id} removing permission {permission_id} "
        f"from role {role_id}"
    )

    # Check permission
    require_permission(current_user.permissions, "role.manage")

    role_service = RoleService(db)

    try:
        # Get role to validate org membership and system role
        existing_role = role_service.get_role_by_id(role_id)
        validate_user_in_organization(
            current_user.id, existing_role["organization_id"], db
        )

        # Check if trying to modify system role
        if existing_role["is_system"] and not is_system_admin(current_user.permissions):
            logger.warning(
                f"User {current_user.id} attempted to modify system role {role_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles unless you are a system admin",
            )

        role_service.remove_permission_from_role(role_id, permission_id)
        logger.info(
            f"User {current_user.id} removed permission {permission_id} "
            f"from role {role_id}"
        )

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except RolePermissionNotFoundException as e:
        logger.warning(f"Role-permission not found: {role_id} -> {permission_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SystemRoleModificationException as e:
        logger.warning(f"Cannot modify system role: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error removing permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove permission",
        )


@router.post(
    "/roles/{role_id}/permissions/bulk",
    summary="Bulk assign permissions",
    description="Bulk assign multiple permissions to a role",
)
async def bulk_assign_permissions_to_role(
    role_id: UUID,
    request: BulkAssignRolePermissionsRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Bulk assign permissions to a role.

    Requires authentication and 'role.manage' permission.
    Only system admins can bulk assign to system roles.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Request Body:**
    - **permission_ids**: List of permission UUIDs
    - **mode**: "replace" (default) or "add"
    """
    logger.info(
        f"User {current_user.id} bulk assigning {len(request.permission_ids)} "
        f"permissions to role {role_id}"
    )

    # Check permission
    require_permission(current_user.permissions, "role.manage")

    role_service = RoleService(db)

    try:
        # Get role to validate org membership and system role
        existing_role = role_service.get_role_by_id(role_id)
        validate_user_in_organization(
            current_user.id, existing_role["organization_id"], db
        )

        # Check if trying to modify system role
        if existing_role["is_system"] and not is_system_admin(current_user.permissions):
            logger.warning(
                f"User {current_user.id} attempted to bulk modify system role {role_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles unless you are a system admin",
            )

        result = role_service.bulk_assign_permissions_to_role(
            role_id,
            request.permission_ids,
            request.mode,
        )

        logger.info(
            f"User {current_user.id} bulk assigned {result['assigned_count']} "
            f"permissions to role"
        )

        return result

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SystemRoleModificationException as e:
        logger.warning(f"Cannot modify system role: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error bulk assigning permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk assign permissions",
        )


@router.get(
    "/roles/{role_id}/users",
    response_model=RoleUsersListResponse,
    summary="Get role users",
    description="Get users assigned to a role",
)
async def get_role_users(
    role_id: UUID,
    organization_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get users assigned to a role.

    Requires authentication and 'user.read' permission.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Query Parameters:**
    - **organization_id**: Organization UUID (required)
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    """
    logger.info(
        f"User {current_user.id} fetching users for role: {role_id} "
        f"in org: {organization_id}"
    )

    # Check permission
    require_permission(current_user.permissions, "user.read")

    # Validate organization membership
    validate_user_in_organization(current_user.id, organization_id, db)

    role_service = RoleService(db)

    try:
        result = role_service.get_role_users(
            role_id,
            organization_id,
            skip=skip,
            limit=limit,
        )

        logger.info(
            f"User {current_user.id} retrieved {len(result['data'])} users for role"
        )

        return RoleUsersListResponse(**result)

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error fetching role users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role users",
        )
