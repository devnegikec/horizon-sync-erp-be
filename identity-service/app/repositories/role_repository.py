"""Role repository for database operations"""

import logging
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.role import Role, RolePermission

logger = logging.getLogger(__name__)


class RoleRepository:
    """Repository for role database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_role(self, role_data: dict) -> Role:
        """
        Create a new role.

        Args:
            role_data: Dictionary containing role data

        Returns:
            Created Role object
        """
        logger.debug(f"Creating role with code: {role_data.get('code')}")
        role = Role(**role_data)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        logger.info(f"Role created successfully: {role.id}")
        return role

    def get_role_by_id(self, role_id: UUID) -> Role | None:
        """
        Get role by ID.

        Args:
            role_id: Role UUID

        Returns:
            Role object or None if not found
        """
        logger.debug(f"Fetching role: {role_id}")
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_code(self, code: str, organization_id: UUID) -> Role | None:
        """
        Get role by code within organization.

        Args:
            code: Role code
            organization_id: Organization UUID

        Returns:
            Role object or None if not found
        """
        logger.debug(f"Fetching role by code: {code} in org: {organization_id}")
        return (
            self.db.query(Role)
            .filter(
                and_(
                    Role.code == code,
                    Role.organization_id == organization_id,
                )
            )
            .first()
        )

    def update_role(self, role: Role, update_data: dict) -> Role:
        """
        Update role fields.

        Args:
            role: Role object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Role object
        """
        logger.debug(f"Updating role: {role.id}")
        for key, value in update_data.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)

        self.db.commit()
        self.db.refresh(role)
        logger.info(f"Role updated successfully: {role.id}")
        return role

    def delete_role(self, role: Role) -> None:
        """
        Delete a role.

        Args:
            role: Role object to delete
        """
        logger.debug(f"Deleting role: {role.id}")
        self.db.delete(role)
        self.db.commit()
        logger.info(f"Role deleted successfully: {role.id}")

    def list_roles(
        self,
        organization_ids: list[UUID] | None = None,
        organization_id: UUID | None = None,  # Deprecated: use organization_ids
        skip: int = 0,
        limit: int = 10,
        is_active: bool | None = None,
        is_system: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Role], int]:
        """
        List roles with pagination and filters.

        Args:
            organization_ids: Filter by organizations (roles in these orgs only)
            organization_id: Deprecated - use organization_ids
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            is_system: Filter by system role flag
            search: Search term for name or code

        Returns:
            Tuple of (list of roles, total count)
        """
        # Support legacy organization_id for backward compatibility
        if organization_ids is None and organization_id is not None:
            organization_ids = [organization_id]

        logger.debug(
            f"Listing roles - org_ids: {organization_ids}, skip: {skip}, limit: {limit}, "
            f"is_active: {is_active}, is_system: {is_system}"
        )

        query = self.db.query(Role)

        # Per-user custom roles (code `custom_<user_id>`) are an internal
        # implementation detail and must never appear in role lists.
        # The underscore is escaped so only the literal `custom_` prefix is
        # hidden (SQL LIKE treats `_` as a single-character wildcard).
        query = query.filter(Role.code.notlike("custom!_%", escape="!"))

        if organization_ids:
            query = query.filter(Role.organization_id.in_(organization_ids))

        if is_active is not None:
            query = query.filter(Role.is_active == is_active)

        if is_system is not None:
            query = query.filter(Role.is_system == is_system)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Role.code.ilike(search_term),
                    Role.name.ilike(search_term),
                )
            )

        total_count = query.count()

        roles = query.offset(skip).limit(limit).all()

        logger.debug(f"Found {len(roles)} roles out of {total_count} total")

        return roles, total_count

    def assign_permission(
        self,
        role_id: UUID,
        permission_id: UUID,
        conditions: dict | None = None,
    ) -> RolePermission:
        """
        Assign permission to role.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID
            conditions: Optional conditions dictionary

        Returns:
            Created RolePermission object
        """
        logger.debug(f"Assigning permission {permission_id} to role {role_id}")

        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
            conditions=conditions or {},
        )

        self.db.add(role_permission)
        self.db.commit()
        self.db.refresh(role_permission)

        logger.info(f"Permission assigned to role: {role_permission.id}")

        return role_permission

    def remove_permission(self, role_id: UUID, permission_id: UUID) -> None:
        """
        Remove permission from role.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID
        """
        logger.debug(f"Removing permission {permission_id} from role {role_id}")

        self.db.query(RolePermission).filter(
            and_(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        ).delete()

        self.db.commit()

        logger.info(f"Permission removed from role {role_id}")

    def get_role_permission(
        self, role_id: UUID, permission_id: UUID
    ) -> RolePermission | None:
        """
        Get role-permission mapping.

        Args:
            role_id: Role UUID
            permission_id: Permission UUID

        Returns:
            RolePermission object or None if not found
        """
        logger.debug(f"Fetching role-permission: {role_id} -> {permission_id}")

        return (
            self.db.query(RolePermission)
            .filter(
                and_(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
            .first()
        )

    def get_role_permission_by_id(
        self, role_permission_id: UUID
    ) -> RolePermission | None:
        """
        Get role-permission by ID.

        Args:
            role_permission_id: RolePermission UUID

        Returns:
            RolePermission object or None if not found
        """
        logger.debug(f"Fetching role-permission: {role_permission_id}")

        return (
            self.db.query(RolePermission)
            .filter(RolePermission.id == role_permission_id)
            .first()
        )

    def get_role_permissions(
        self,
        role_id: UUID,
        skip: int = 0,
        limit: int = 10,
        resource: str | None = None,
        action: str | None = None,
    ) -> tuple[list[RolePermission], int]:
        """
        Get permissions for a role.

        Args:
            role_id: Role UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            resource: Filter by resource type
            action: Filter by action type

        Returns:
            Tuple of (list of role-permissions, total count)
        """
        logger.debug(f"Fetching permissions for role: {role_id}")

        from app.models.role import Permission

        query = self.db.query(RolePermission).filter(RolePermission.role_id == role_id)

        if resource or action:
            query = query.join(Permission)

            if resource:
                query = query.filter(Permission.resource == resource)

            if action:
                query = query.filter(Permission.action == action)

        total_count = query.count()

        role_permissions = query.offset(skip).limit(limit).all()

        logger.debug(f"Found {len(role_permissions)} permissions for role")

        return role_permissions, total_count

    def count_role_users(self, role_id: UUID) -> int:
        """
        Count users assigned to a role.

        Args:
            role_id: Role UUID

        Returns:
            Number of users with the role
        """
        logger.debug(f"Counting users for role: {role_id}")

        from app.models.role import UserOrganizationRole

        count = (
            self.db.query(UserOrganizationRole)
            .filter(
                and_(
                    UserOrganizationRole.role_id == role_id,
                    UserOrganizationRole.is_active,
                )
            )
            .count()
        )

        logger.debug(f"Role has {count} active users")

        return count

    def get_role_users(
        self,
        role_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list, int]:
        """
        Get users assigned to a role.

        Args:
            role_id: Role UUID
            organization_id: Organization UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of user assignments, total count)
        """
        logger.debug(f"Fetching users for role: {role_id}")

        from app.models.role import UserOrganizationRole
        from app.models.user import User

        query = (
            self.db.query(UserOrganizationRole, User)
            .join(User, UserOrganizationRole.user_id == User.id)
            .filter(
                and_(
                    UserOrganizationRole.role_id == role_id,
                    UserOrganizationRole.organization_id == organization_id,
                )
            )
        )

        total_count = query.count()

        user_assignments = query.offset(skip).limit(limit).all()

        logger.debug(f"Found {len(user_assignments)} users for role")

        return user_assignments, total_count

    def update_role_permission(
        self,
        role_permission: RolePermission,
        update_data: dict,
    ) -> RolePermission:
        """
        Update role-permission conditions.

        Args:
            role_permission: RolePermission object
            update_data: Dictionary of fields to update

        Returns:
            Updated RolePermission object
        """
        logger.debug(f"Updating role-permission: {role_permission.id}")

        for key, value in update_data.items():
            if hasattr(role_permission, key) and value is not None:
                setattr(role_permission, key, value)

        self.db.commit()
        self.db.refresh(role_permission)

        logger.info(f"Role-permission updated: {role_permission.id}")

        return role_permission
