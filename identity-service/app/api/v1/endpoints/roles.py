"""Role management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

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
from app.dependencies import get_current_active_user
from app.schemas.role import (
    BulkAssignRolePermissionsRequest,
    RoleCreate,
    RoleListResponse,
    RolePermissionCreate,
    RolePermissionDetailResponse,
    RolePermissionResponse,
    RolePermissionUpdate,
    RoleResponse,
    RoleUpdate,
    RoleUsersListResponse,
)
from app.services.role_service import RoleService

router = APIRouter()
logger = logging.getLogger(__name__)


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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List roles with pagination and filters.

    Requires authentication.

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

    role_service = RoleService(db)

    try:
        result = role_service.list_roles(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            is_active=is_active,
            is_system=is_system,
            search=search,
            include_permissions=include_permissions,
        )

        logger.info(f"Retrieved {len(result['data'])} roles")

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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific role by ID.

    Requires authentication.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Query Parameters:**
    - **include_permissions**: Include permissions in response
    """
    logger.info(f"User {current_user.id} fetching role: {role_id}")

    role_service = RoleService(db)

    try:
        result = role_service.get_role_by_id(
            role_id,
            include_permissions=include_permissions,
        )
        logger.info(f"Role fetched: {role_id}")
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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new role.

    Requires authentication and admin privileges.

    **Request Body:**
    - **organization_id**: Organization UUID (required)
    - **name**: Role name
    - **code**: Unique role code
    - **description**: Optional description
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

    role_service = RoleService(db)

    try:
        result = role_service.create_role(
            role.model_dump(exclude={"organization_id"}),
            role.organization_id,
        )
        logger.info(f"Role created: {result['id']}")
        return RoleResponse(**result)

    except DuplicateRoleException as e:
        logger.warning(f"Duplicate role code: {role.code}")
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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a role.

    Requires authentication and admin privileges.

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

    role_service = RoleService(db)

    try:
        result = role_service.update_role(
            role_id,
            role.model_dump(exclude_unset=True),
        )
        logger.info(f"Role updated: {role_id}")
        return RoleResponse(**result)

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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a role.

    Requires authentication and admin privileges.

    **Path Parameters:**
    - **role_id**: UUID of the role
    """
    logger.info(f"User {current_user.id} deleting role: {role_id}")

    role_service = RoleService(db)

    try:
        role_service.delete_role(role_id)
        logger.info(f"Role deleted: {role_id}")

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SystemRoleModificationException as e:
        logger.warning(f"Cannot delete system role: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except RoleHasUsersException as e:
        logger.warning(f"Cannot delete role {role_id}: has active users")
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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get permissions assigned to a role.

    Requires authentication.

    **Path Parameters:**
    - **role_id**: UUID of the role

    **Query Parameters:**
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return
    - **resource**: Filter by resource type
    - **action**: Filter by action type
    """
    logger.info(
        f"User {current_user.id} fetching permissions for role: {role_id}"
    )

    role_service = RoleService(db)

    try:
        result = role_service.get_role_permissions(
            role_id,
            skip=skip,
            limit=limit,
            resource=resource,
            action=action,
        )

        logger.info(f"Retrieved {len(result['data'])} permissions for role")

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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Assign a permission to a role.

    Requires authentication and admin privileges.

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

    role_service = RoleService(db)

    try:
        result = role_service.assign_permission_to_role(
            role_id,
            permission.permission_id,
            permission.conditions,
        )

        logger.info(f"Permission assigned to role: {result['id']}")

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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Remove a permission from a role.

    Requires authentication and admin privileges.

    **Path Parameters:**
    - **role_id**: UUID of the role
    - **permission_id**: UUID of the permission
    """
    logger.info(
        f"User {current_user.id} removing permission {permission_id} "
        f"from role {role_id}"
    )

    role_service = RoleService(db)

    try:
        role_service.remove_permission_from_role(role_id, permission_id)
        logger.info(f"Permission removed from role: {role_id}")

    except RoleNotFoundException as e:
        logger.warning(f"Role not found: {role_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except RolePermissionNotFoundException as e:
        logger.warning(
            f"Role-permission not found: {role_id} -> {permission_id}"
        )
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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Bulk assign permissions to a role.

    Requires authentication and admin privileges.

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

    role_service = RoleService(db)

    try:
        result = role_service.bulk_assign_permissions_to_role(
            role_id,
            request.permission_ids,
            request.mode,
        )

        logger.info(
            f"Bulk assigned {result['assigned_count']} permissions to role"
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
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get users assigned to a role.

    Requires authentication.

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

    role_service = RoleService(db)

    try:
        result = role_service.get_role_users(
            role_id,
            organization_id,
            skip=skip,
            limit=limit,
        )

        logger.info(f"Retrieved {len(result['data'])} users for role")

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
