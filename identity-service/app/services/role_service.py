"""Role service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateRoleException,
    RoleHasUsersException,
    RoleNotFoundException,
    RolePermissionAlreadyAssignedException,
    RolePermissionNotFoundException,
    SystemRoleModificationException,
)
from app.repositories.role_repository import RoleRepository

logger = logging.getLogger(__name__)


def _convert_enum_to_string(value) -> str:
    """Convert enum value to string if needed."""
    if hasattr(value, "value"):
        return value.value
    return value


class RoleService:
    """Service for role operations"""

    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)

    def create_role(self, role_data: dict, organization_id: UUID) -> dict:
        """
        Create a new role.

        Args:
            role_data: Dictionary containing role data
            organization_id: Organization UUID

        Returns:
            Role response dictionary

        Raises:
            DuplicateRoleException: If role code already exists in organization
        """
        logger.info(f"Creating role: {role_data.get('code')} in org: {organization_id}")

        existing_role = self.role_repo.get_role_by_code(
            role_data.get("code"), organization_id
        )

        if existing_role:
            logger.warning(
                f"Role code already exists: {role_data.get('code')} "
                f"in org: {organization_id}"
            )
            raise DuplicateRoleException(
                f"Role code '{role_data.get('code')}' already exists in this organization"
            )

        role_data["organization_id"] = organization_id
        role = self.role_repo.create_role(role_data)
        logger.info(f"Role created: {role.id}")

        return self._role_to_dict(role)

    def get_role_by_id(
        self,
        role_id: UUID,
        include_permissions: bool = False,
    ) -> dict:
        """
        Get role by ID.

        Args:
            role_id: Role UUID
            include_permissions: Whether to include permissions

        Returns:
            Role response dictionary

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.debug(f"Fetching role: {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        return self._role_to_dict(role, include_permissions=include_permissions)

    def list_roles(
        self,
        organization_id: UUID | None = None,
        skip: int = 0,
        limit: int = 10,
        is_active: bool | None = None,
        is_system: bool | None = None,
        search: str | None = None,
        include_permissions: bool = False,
    ) -> dict:
        """
        List roles with pagination and filters.

        Args:
            organization_id: Filter by organization
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            is_system: Filter by system role flag
            search: Search term
            include_permissions: Whether to include permissions

        Returns:
            Dictionary with roles list and pagination info
        """
        logger.debug(
            f"Listing roles - org_id: {organization_id}, skip: {skip}, limit: {limit}"
        )

        roles, total_count = self.role_repo.list_roles(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            is_active=is_active,
            is_system=is_system,
            search=search,
        )

        return {
            "data": [
                self._role_to_dict(role, include_permissions=include_permissions)
                for role in roles
            ],
            "total": total_count,
            "skip": skip,
            "limit": limit,
        }

    def update_role(self, role_id: UUID, update_data: dict) -> dict:
        """
        Update a role.

        Args:
            role_id: Role UUID
            update_data: Dictionary of fields to update

        Returns:
            Updated role response dictionary

        Raises:
            RoleNotFoundException: If role not found
            SystemRoleModificationException: If attempting to modify system role
        """
        logger.info(f"Updating role: {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found for update: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            logger.warning(f"Cannot modify system role: {role_id}")
            raise SystemRoleModificationException(
                f"Cannot modify system role '{role.name}'"
            )

        filtered_data = {k: v for k, v in update_data.items() if v is not None}

        role = self.role_repo.update_role(role, filtered_data)
        logger.info(f"Role updated: {role.id}")

        return self._role_to_dict(role)

    def delete_role(self, role_id: UUID) -> None:
        """
        Delete a role.

        Args:
            role_id: Role UUID

        Raises:
            RoleNotFoundException: If role not found
            SystemRoleModificationException: If role is system role
            RoleHasUsersException: If role has active user assignments
        """
        logger.info(f"Deleting role: {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found for deletion: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            logger.warning(f"Cannot delete system role: {role_id}")
            raise SystemRoleModificationException(
                f"Cannot delete system role '{role.name}'"
            )

        user_count = self.role_repo.count_role_users(role_id)

        if user_count > 0:
            logger.warning(
                f"Cannot delete role {role_id} - has {user_count} active users"
            )
            raise RoleHasUsersException(
                f"Cannot delete role with active user assignments ({user_count} users)"
            )

        self.role_repo.delete_role(role)
        logger.info(f"Role deleted: {role_id}")

    def get_role_permissions(
        self,
        role_id: UUID,
        skip: int = 0,
        limit: int = 10,
        resource: str | None = None,
        action: str | None = None,
    ) -> dict:
        """
        Get permissions for a role.

        Args:
            role_id: Role UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            resource: Filter by resource type
            action: Filter by action type

        Returns:
            Dictionary with role permissions and pagination info

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.debug(f"Fetching permissions for role: {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        role_permissions, total_count = self.role_repo.get_role_permissions(
            role_id=role_id,
            skip=skip,
            limit=limit,
            resource=resource,
            action=action,
        )

        return {
            "data": [self._role_permission_to_dict(rp) for rp in role_permissions],
            "total": total_count,
            "skip": skip,
            "limit": limit,
        }

    def assign_permission_to_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        conditions: dict | None = None,
    ) -> dict:
        """
        Assign permission to role.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID
            conditions: Optional conditions dictionary

        Returns:
            Role-permission response dictionary

        Raises:
            RoleNotFoundException: If role not found
            PermissionNotFoundException: If permission not found
            SystemRoleModificationException: If role is system role
            RolePermissionAlreadyAssignedException: If permission already assigned
        """
        logger.info(f"Assigning permission {permission_id} to role {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            logger.warning(f"Cannot modify system role: {role_id}")
            raise SystemRoleModificationException(
                f"Cannot modify system role '{role.name}'"
            )

        from app.repositories.permission_repository import PermissionRepository

        permission_repo = PermissionRepository(self.db)
        permission = permission_repo.get_permission_by_id(permission_id)

        if not permission:
            logger.warning(f"Permission not found: {permission_id}")
            from app.core.exceptions import PermissionNotFoundException

            raise PermissionNotFoundException(
                f"Permission with ID {permission_id} not found"
            )

        existing = self.role_repo.get_role_permission(role_id, permission_id)

        if existing:
            logger.warning(
                f"Permission {permission_id} already assigned to role {role_id}"
            )
            raise RolePermissionAlreadyAssignedException(
                "Permission already assigned to this role"
            )

        role_permission = self.role_repo.assign_permission(
            role_id=role_id,
            permission_id=permission_id,
            conditions=conditions,
        )

        logger.info(f"Permission assigned to role: {role_permission.id}")

        return {
            "id": role_permission.id,
            "role_id": role_permission.role_id,
            "permission_id": role_permission.permission_id,
            "conditions": role_permission.conditions,
        }

    def remove_permission_from_role(
        self,
        role_id: UUID,
        permission_id: UUID,
    ) -> None:
        """
        Remove permission from role.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID

        Raises:
            RoleNotFoundException: If role not found
            RolePermissionNotFoundException: If mapping not found
            SystemRoleModificationException: If role is system role
        """
        logger.info(f"Removing permission {permission_id} from role {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            logger.warning(f"Cannot modify system role: {role_id}")
            raise SystemRoleModificationException(
                f"Cannot modify system role '{role.name}'"
            )

        role_permission = self.role_repo.get_role_permission(role_id, permission_id)

        if not role_permission:
            logger.warning(f"Role-permission not found: {role_id} -> {permission_id}")
            raise RolePermissionNotFoundException(
                "Permission not assigned to this role"
            )

        self.role_repo.remove_permission(role_id, permission_id)
        logger.info(f"Permission removed from role: {role_id}")

    def bulk_assign_permissions_to_role(
        self,
        role_id: UUID,
        permission_ids: list[UUID],
        mode: str = "replace",
    ) -> dict:
        """
        Bulk assign permissions to role.

        Args:
            role_id: Role UUID
            permission_ids: List of permission UUIDs
            mode: "replace" or "add"

        Returns:
            Dictionary with assignment results

        Raises:
            RoleNotFoundException: If role not found
            SystemRoleModificationException: If role is system role
        """
        logger.info(
            f"Bulk assigning {len(permission_ids)} permissions to role {role_id}"
        )

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        if role.is_system:
            logger.warning(f"Cannot modify system role: {role_id}")
            raise SystemRoleModificationException(
                f"Cannot modify system role '{role.name}'"
            )

        previous_count = len(role.role_permissions) if role.role_permissions else 0

        if mode == "replace":
            for rp in role.role_permissions or []:
                self.role_repo.remove_permission(role_id, rp.permission_id)

        assigned_count = 0

        for permission_id in permission_ids:
            existing = self.role_repo.get_role_permission(role_id, permission_id)

            if not existing:
                self.role_repo.assign_permission(
                    role_id=role_id,
                    permission_id=permission_id,
                )
                assigned_count += 1

        logger.info(f"Assigned {assigned_count} permissions to role {role_id}")

        return {
            "message": f"Successfully assigned {assigned_count} permissions",
            "role_id": role_id,
            "assigned_count": assigned_count,
            "previous_count": previous_count,
        }

    def assign_permission_by_code(
        self,
        role_id: UUID,
        permission_code: str,
        conditions: dict | None = None,
    ) -> dict:
        """
        Assign permission to role by permission code (convenience method).

        Gets or creates the permission if it doesn't exist, then assigns it to the role.

        Examples:
            assign_permission_by_code(role_id, "user.*")  # Assign user.* wildcard
            assign_permission_by_code(role_id, "*.*")      # Assign full access
            assign_permission_by_code(role_id, "user.read") # Assign specific permission

        Args:
            role_id: Role UUID
            permission_code: Permission code (e.g., "user.*", "*.*", "user.read")
            conditions: Optional conditions dictionary

        Returns:
            Role-permission response dictionary

        Raises:
            RoleNotFoundException: If role not found
            SystemRoleModificationException: If role is system role
            ValueError: If permission code format is invalid
        """
        from app.services.permission_service import PermissionService

        permission_service = PermissionService(self.db)
        permission = permission_service.get_or_create_permission_by_code(permission_code)

        return self.assign_permission_to_role(
            role_id=role_id,
            permission_id=permission.id,
            conditions=conditions,
        )

    def assign_full_access(self, role_id: UUID, conditions: dict | None = None) -> dict:
        """
        Assign full access (*.*) permission to role (convenience method).

        Args:
            role_id: Role UUID
            conditions: Optional conditions dictionary

        Returns:
            Role-permission response dictionary
        """
        return self.assign_permission_by_code(role_id, "*.*", conditions)

    def assign_resource_wildcard(
        self,
        role_id: UUID,
        resource: str,
        conditions: dict | None = None,
    ) -> dict:
        """
        Assign resource wildcard permission to role (convenience method).

        Examples:
            assign_resource_wildcard(role_id, "user")   # Assigns user.*
            assign_resource_wildcard(role_id, "org")     # Assigns org.*
            assign_resource_wildcard(role_id, "role")    # Assigns role.*

        Args:
            role_id: Role UUID
            resource: Resource name (will be normalized: "org" -> "org", "organization" -> "org")
            conditions: Optional conditions dictionary

        Returns:
            Role-permission response dictionary
        """
        # Normalize resource: "organization" -> "org" for code
        resource_normalized = resource.lower().strip()
        if resource_normalized == "organization":
            resource_normalized = "org"
        permission_code = f"{resource_normalized}.*"
        return self.assign_permission_by_code(role_id, permission_code, conditions)

    def assign_specific_permission(
        self,
        role_id: UUID,
        resource: str,
        action: str,
        conditions: dict | None = None,
    ) -> dict:
        """
        Assign specific permission to role (convenience method).

        Examples:
            assign_specific_permission(role_id, "user", "read")   # Assigns user.read
            assign_specific_permission(role_id, "org", "create") # Assigns org.create

        Args:
            role_id: Role UUID
            resource: Resource name (will be normalized: "organization" -> "org")
            action: Action name (e.g., "read", "create", "update", "delete")
            conditions: Optional conditions dictionary

        Returns:
            Role-permission response dictionary
        """
        # Normalize resource: "organization" -> "org" for code
        resource_normalized = resource.lower().strip()
        if resource_normalized == "organization":
            resource_normalized = "org"
        permission_code = f"{resource_normalized}.{action.lower().strip()}"
        return self.assign_permission_by_code(role_id, permission_code, conditions)

    def get_role_users(
        self,
        role_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> dict:
        """
        Get users assigned to a role.

        Args:
            role_id: Role UUID
            organization_id: Organization UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Dictionary with users and pagination info

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.debug(f"Fetching users for role: {role_id}")

        role = self.role_repo.get_role_by_id(role_id)

        if not role:
            logger.warning(f"Role not found: {role_id}")
            raise RoleNotFoundException(f"Role with ID {role_id} not found")

        user_assignments, total_count = self.role_repo.get_role_users(
            role_id=role_id,
            organization_id=organization_id,
            skip=skip,
            limit=limit,
        )

        data = []

        for assignment, user in user_assignments:
            data.append(
                {
                    "id": assignment.id,
                    "user_id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_primary": assignment.is_primary,
                    "is_active": assignment.is_active,
                    "status": assignment.status,
                    "joined_at": assignment.joined_at,
                }
            )

        return {
            "data": data,
            "total": total_count,
            "skip": skip,
            "limit": limit,
        }

    def _role_to_dict(self, role, include_permissions: bool = False) -> dict:
        """Convert role object to dictionary."""
        data = {
            "id": role.id,
            "organization_id": role.organization_id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_default": role.is_default,
            "hierarchy_level": role.hierarchy_level,
            "is_active": role.is_active,
            "extra_data": role.extra_data,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "permissions": [],
        }

        if include_permissions and role.role_permissions:
            data["permissions"] = [
                {
                    "id": rp.permission.id,
                    "code": rp.permission.code,
                    "name": rp.permission.name,
                    "description": rp.permission.description,
                    "resource": _convert_enum_to_string(rp.permission.resource),
                    "action": _convert_enum_to_string(rp.permission.action),
                    "module": rp.permission.module,
                    "category": rp.permission.category,
                    "is_active": rp.permission.is_active,
                    "extra_data": rp.permission.extra_data,
                    "created_at": rp.permission.created_at,
                    "updated_at": rp.permission.updated_at,
                }
                for rp in role.role_permissions
            ]

        return data

    def _role_permission_to_dict(self, role_permission) -> dict:
        """Convert role-permission object to dictionary."""
        return {
            "id": role_permission.id,
            "role_id": role_permission.role_id,
            "permission_id": role_permission.permission_id,
            "code": role_permission.permission.code,
            "name": role_permission.permission.name,
            "resource": _convert_enum_to_string(role_permission.permission.resource),
            "action": _convert_enum_to_string(role_permission.permission.action),
            "module": role_permission.permission.module,
            "conditions": role_permission.conditions,
        }
