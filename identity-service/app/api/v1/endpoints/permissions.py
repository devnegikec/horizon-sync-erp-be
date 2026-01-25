"""Permission management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicatePermissionException,
    PermissionNotFoundException,
    RolePermissionAlreadyAssignedException,
)
from app.database import get_db
from app.schemas.permission import (
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
)
from app.services.permission_service import PermissionService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
    summary="List permissions",
    description="Get paginated list of permissions with optional filters",
)
async def list_permissions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    resource: str | None = Query(None, description="Filter by resource type"),
    action: str | None = Query(None, description="Filter by action type"),
    module: str | None = Query(None, description="Filter by module"),
    search: str | None = Query(None, description="Search in code or name"),
    db: Session = Depends(get_db),
):
    """
    List permissions with pagination and filters.

    This endpoint is public and does not require authentication.

    **Query Parameters:**
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum records to return (default: 10, max: 100)
    - **is_active**: Filter by active status
    - **resource**: Filter by resource type
    - **action**: Filter by action type
    - **module**: Filter by module
    - **search**: Search term for code or name
    """
    logger.info(
        f"Listing permissions - "
        f"skip: {skip}, limit: {limit}"
    )

    permission_service = PermissionService(db)

    try:
        result = permission_service.list_permissions(
            skip=skip,
            limit=limit,
            is_active=is_active,
            resource=resource,
            action=action,
            module=module,
            search=search,
        )

        logger.info(f"Retrieved {len(result['data'])} permissions")

        return PermissionListResponse(**result)

    except Exception as e:
        logger.error(f"Error listing permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permissions",
        )


@router.get(
    "/permissions/{permission_id}",
    response_model=PermissionResponse,
    summary="Get permission",
    description="Get a specific permission by ID",
)
async def get_permission(
    permission_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific permission by ID.

    This endpoint is public and does not require authentication.

    **Path Parameters:**
    - **permission_id**: UUID of the permission
    """
    logger.info(f"Fetching permission: {permission_id}")

    permission_service = PermissionService(db)

    try:
        result = permission_service.get_permission_by_id(permission_id)
        logger.info(f"Permission fetched: {permission_id}")
        return PermissionResponse(**result)

    except PermissionNotFoundException as e:
        logger.warning(f"Permission not found: {permission_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error fetching permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve permission",
        )


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create permission",
    description="Create a new permission",
)
async def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new permission.

    This endpoint does not require authentication.

    **Request Body:**
    - **code**: Unique permission code
    - **name**: Permission name
    - **description**: Optional description
    - **resource**: Resource type
    - **action**: Action type
    - **module**: Optional module
    - **category**: Optional category
    - **is_active**: Active status (default: true)
    - **extra_data**: Optional metadata
    """
    logger.info(
        f"Creating permission: {permission.code}"
    )

    permission_service = PermissionService(db)

    try:
        result = permission_service.create_permission(permission.model_dump())
        logger.info(f"Permission created: {result['id']}")
        return PermissionResponse(**result)

    except DuplicatePermissionException as e:
        logger.warning(f"Duplicate permission code: {permission.code}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error creating permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create permission",
        )


@router.put(
    "/permissions/{permission_id}",
    response_model=PermissionResponse,
    summary="Update permission",
    description="Update an existing permission",
)
async def update_permission(
    permission_id: UUID,
    permission: PermissionUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a permission.

    This endpoint does not require authentication.

    **Path Parameters:**
    - **permission_id**: UUID of the permission

    **Request Body:**
    - **name**: Optional new name
    - **description**: Optional new description
    - **is_active**: Optional active status
    - **extra_data**: Optional metadata
    """
    logger.info(
        f"Updating permission: {permission_id}"
    )

    permission_service = PermissionService(db)

    try:
        result = permission_service.update_permission(
            permission_id,
            permission.model_dump(exclude_unset=True),
        )
        logger.info(f"Permission updated: {permission_id}")
        return PermissionResponse(**result)

    except PermissionNotFoundException as e:
        logger.warning(f"Permission not found: {permission_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error updating permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update permission",
        )


@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete permission",
    description="Delete a permission",
)
async def delete_permission(
    permission_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a permission.

    This endpoint does not require authentication.

    **Path Parameters:**
    - **permission_id**: UUID of the permission
    """
    logger.info(
        f"Deleting permission: {permission_id}"
    )

    permission_service = PermissionService(db)

    try:
        permission_service.delete_permission(permission_id)
        logger.info(f"Permission deleted: {permission_id}")

    except PermissionNotFoundException as e:
        logger.warning(f"Permission not found: {permission_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except RolePermissionAlreadyAssignedException as e:
        logger.warning(
            f"Cannot delete permission {permission_id}: "
            f"has active role assignments"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete permission",
        )
