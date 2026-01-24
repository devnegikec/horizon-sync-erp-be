"""Permission service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicatePermissionException,
    PermissionNotFoundException,
    RolePermissionAlreadyAssignedException,
)
from app.repositories.permission_repository import PermissionRepository

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for permission operations"""

    def __init__(self, db: Session):
        self.db = db
        self.permission_repo = PermissionRepository(db)

    def create_permission(self, permission_data: dict) -> dict:
        """
        Create a new permission.

        Args:
            permission_data: Dictionary containing permission data

        Returns:
            Permission response dictionary

        Raises:
            DuplicatePermissionException: If code already exists
        """
        logger.info(f"Creating permission: {permission_data.get('code')}")

        existing = self.permission_repo.get_permission_by_code(
            permission_data.get("code")
        )

        if existing:
            logger.warning(f"Permission code already exists: {permission_data.get('code')}")
            raise DuplicatePermissionException(
                f"Permission code '{permission_data.get('code')}' already exists"
            )

        permission = self.permission_repo.create_permission(permission_data)
        logger.info(f"Permission created: {permission.id}")

        return {
            "id": permission.id,
            "code": permission.code,
            "name": permission.name,
            "description": permission.description,
            "resource": permission.resource,
            "action": permission.action,
            "module": permission.module,
            "category": permission.category,
            "is_active": permission.is_active,
            "extra_data": permission.extra_data,
            "created_at": permission.created_at,
            "updated_at": permission.updated_at,
        }

    def get_permission_by_id(self, permission_id: UUID) -> dict:
        """
        Get permission by ID.

        Args:
            permission_id: Permission UUID

        Returns:
            Permission response dictionary

        Raises:
            PermissionNotFoundException: If permission not found
        """
        logger.debug(f"Fetching permission: {permission_id}")

        permission = self.permission_repo.get_permission_by_id(permission_id)

        if not permission:
            logger.warning(f"Permission not found: {permission_id}")
            raise PermissionNotFoundException(f"Permission with ID {permission_id} not found")

        return {
            "id": permission.id,
            "code": permission.code,
            "name": permission.name,
            "description": permission.description,
            "resource": permission.resource,
            "action": permission.action,
            "module": permission.module,
            "category": permission.category,
            "is_active": permission.is_active,
            "extra_data": permission.extra_data,
            "created_at": permission.created_at,
            "updated_at": permission.updated_at,
        }

    def list_permissions(
        self,
        skip: int = 0,
        limit: int = 10,
        is_active: bool | None = None,
        resource: str | None = None,
        action: str | None = None,
        module: str | None = None,
        search: str | None = None,
    ) -> dict:
        """
        List permissions with pagination and filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            resource: Filter by resource type
            action: Filter by action type
            module: Filter by module
            search: Search term

        Returns:
            Dictionary with permissions list and pagination info
        """
        logger.debug(
            f"Listing permissions - skip: {skip}, limit: {limit}, "
            f"is_active: {is_active}, resource: {resource}, action: {action}"
        )

        permissions, total_count = self.permission_repo.list_permissions(
            skip=skip,
            limit=limit,
            is_active=is_active,
            resource=resource,
            action=action,
            module=module,
            search=search,
        )

        return {
            "data": [
                {
                    "id": p.id,
                    "code": p.code,
                    "name": p.name,
                    "description": p.description,
                    "resource": p.resource,
                    "action": p.action,
                    "module": p.module,
                    "category": p.category,
                    "is_active": p.is_active,
                    "extra_data": p.extra_data,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
                for p in permissions
            ],
            "total": total_count,
            "skip": skip,
            "limit": limit,
        }

    def update_permission(self, permission_id: UUID, update_data: dict) -> dict:
        """
        Update a permission.

        Args:
            permission_id: Permission UUID
            update_data: Dictionary of fields to update

        Returns:
            Updated permission response dictionary

        Raises:
            PermissionNotFoundException: If permission not found
        """
        logger.info(f"Updating permission: {permission_id}")

        permission = self.permission_repo.get_permission_by_id(permission_id)

        if not permission:
            logger.warning(f"Permission not found for update: {permission_id}")
            raise PermissionNotFoundException(f"Permission with ID {permission_id} not found")

        # Remove None values from update_data
        filtered_data = {k: v for k, v in update_data.items() if v is not None}

        permission = self.permission_repo.update_permission(permission, filtered_data)
        logger.info(f"Permission updated: {permission.id}")

        return {
            "id": permission.id,
            "code": permission.code,
            "name": permission.name,
            "description": permission.description,
            "resource": permission.resource,
            "action": permission.action,
            "module": permission.module,
            "category": permission.category,
            "is_active": permission.is_active,
            "extra_data": permission.extra_data,
            "created_at": permission.created_at,
            "updated_at": permission.updated_at,
        }

    def delete_permission(self, permission_id: UUID) -> None:
        """
        Delete a permission.

        Args:
            permission_id: Permission UUID

        Raises:
            PermissionNotFoundException: If permission not found
        """
        logger.info(f"Deleting permission: {permission_id}")

        permission = self.permission_repo.get_permission_by_id(permission_id)

        if not permission:
            logger.warning(f"Permission not found for deletion: {permission_id}")
            raise PermissionNotFoundException(f"Permission with ID {permission_id} not found")

        if self.permission_repo.check_permission_used_in_roles(permission_id):
            logger.warning(f"Cannot delete permission {permission_id} - used in roles")
            raise RolePermissionAlreadyAssignedException(
                "Cannot delete permission with active role assignments"
            )

        self.permission_repo.delete_permission(permission)
        logger.info(f"Permission deleted: {permission_id}")
