"""Permission repository for database operations"""

import logging
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.role import Permission

logger = logging.getLogger(__name__)


class PermissionRepository:
    """Repository for permission database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_permission(self, permission_data: dict) -> Permission:
        """
        Create a new permission.

        Args:
            permission_data: Dictionary containing permission data

        Returns:
            Created Permission object
        """
        logger.debug(f"Creating permission with code: {permission_data.get('code')}")
        permission = Permission(**permission_data)
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        logger.info(f"Permission created successfully: {permission.id}")
        return permission

    def get_permission_by_id(self, permission_id: UUID) -> Permission | None:
        """
        Get permission by ID.

        Args:
            permission_id: Permission UUID

        Returns:
            Permission object or None if not found
        """
        logger.debug(f"Fetching permission: {permission_id}")
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    def get_permission_by_code(self, code: str) -> Permission | None:
        """
        Get permission by code.

        Args:
            code: Permission code

        Returns:
            Permission object or None if not found
        """
        logger.debug(f"Fetching permission by code: {code}")
        return self.db.query(Permission).filter(Permission.code == code).first()

    def update_permission(
        self, permission: Permission, update_data: dict
    ) -> Permission:
        """
        Update permission fields.

        Args:
            permission: Permission object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Permission object
        """
        logger.debug(f"Updating permission: {permission.id}")
        for key, value in update_data.items():
            if hasattr(permission, key) and value is not None:
                setattr(permission, key, value)

        self.db.commit()
        self.db.refresh(permission)
        logger.info(f"Permission updated successfully: {permission.id}")
        return permission

    def delete_permission(self, permission: Permission) -> None:
        """
        Delete a permission.

        Args:
            permission: Permission object to delete
        """
        logger.debug(f"Deleting permission: {permission.id}")
        self.db.delete(permission)
        self.db.commit()
        logger.info(f"Permission deleted successfully: {permission.id}")

    def list_permissions(
        self,
        skip: int = 0,
        limit: int = 10,
        is_active: bool | None = None,
        resource: str | None = None,
        action: str | None = None,
        module: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Permission], int]:
        """
        List permissions with pagination and filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            resource: Filter by resource type
            action: Filter by action type
            module: Filter by module
            search: Search term for code or name

        Returns:
            Tuple of (list of permissions, total count)
        """
        logger.debug(
            f"Listing permissions - skip: {skip}, limit: {limit}, "
            f"is_active: {is_active}, resource: {resource}, action: {action}"
        )

        query = self.db.query(Permission)

        if is_active is not None:
            query = query.filter(Permission.is_active == is_active)

        if resource:
            # Map 'org' to 'organization' for enum comparison
            resource_normalized = resource.lower()
            if resource_normalized == "org":
                resource_normalized = "organization"
            # Include both exact resource match AND wildcard codes for that resource
            # e.g., filter resource='user' should show user.read, user.create, AND user.*
            resource_prefix = (
                "org" if resource_normalized == "organization" else resource_normalized
            )
            query = query.filter(
                or_(
                    Permission.resource == resource_normalized,
                    Permission.code.like(
                        f"{resource_prefix}.*"
                    ),  # Include user.*, org.*, etc.
                    Permission.code == "*.*",  # Include full wildcard
                )
            )

        if action:
            # When filtering by action, include wildcards that grant that action
            # e.g., filter action='read' should show user.read AND user.* AND *.*
            query = query.filter(
                or_(
                    Permission.action == action,
                    Permission.code.like(
                        f"%.{action}"
                    ),  # Any resource with this action
                    Permission.code.like("%.*"),  # Resource wildcards (user.*, org.*)
                    Permission.code == "*.*",  # Full wildcard
                )
            )

        if module:
            query = query.filter(Permission.module == module)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Permission.code.ilike(search_term),
                    Permission.name.ilike(search_term),
                )
            )

        total_count = query.count()

        permissions = query.offset(skip).limit(limit).all()

        logger.debug(f"Found {len(permissions)} permissions out of {total_count} total")

        return permissions, total_count

    def check_permission_used_in_roles(self, permission_id: UUID) -> bool:
        """
        Check if permission is used in any role.

        Args:
            permission_id: Permission UUID

        Returns:
            True if permission is used in any role, False otherwise
        """
        logger.debug(f"Checking if permission {permission_id} is used in roles")
        from app.models.role import RolePermission

        count = (
            self.db.query(RolePermission)
            .filter(RolePermission.permission_id == permission_id)
            .count()
        )

        return count > 0
