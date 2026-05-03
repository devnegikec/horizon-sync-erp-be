"""Permission service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicatePermissionException,
    PermissionNotFoundException,
    RolePermissionAlreadyAssignedException,
)
from app.models.base import ActionType, ResourceType
from app.models.role import Permission
from app.repositories.permission_repository import PermissionRepository

logger = logging.getLogger(__name__)


def _convert_enum_to_string(value) -> str:
    """Convert enum value to string if needed."""
    if hasattr(value, "value"):
        return value.value
    return value


def _normalize_resource_for_db(value: str | None) -> str | None:
    """Map API/frontend resource values to DB enum values. ResourceType has 'organization' not 'org'."""
    if not value:
        return value
    v = value.lower().strip()
    if v == "org":
        return ResourceType.ORGANIZATION.value
    return v


def _normalize_action_for_db(value: str | None) -> str | None:
    """Map API/frontend action values to DB enum values. ActionType has create/read/update/delete/manage/execute/invite only."""
    if not value:
        return value
    v = value.lower().strip()
    if v in ("*.*", ".*", "owner"):
        return ActionType.MANAGE.value
    return v


def _parse_permission_code(code: str) -> tuple[str | None, str | None]:
    """
    Parse permission code to extract resource and action.

    Examples:
        "user.read" -> ("user", "read")
        "user.*" -> ("user", "*")
        "*.*" -> ("*", "*")
        "org.create" -> ("org", "create")  # Note: org in code, organization in DB

    Returns:
        Tuple of (resource_prefix, action) or (None, None) if invalid format
    """
    if not code or "." not in code:
        return None, None
    parts = code.split(".", 1)
    if len(parts) != 2:
        return None, None
    resource_prefix, action = parts
    return resource_prefix.lower(), action.lower()


def _validate_permission_code(code: str) -> tuple[bool, str | None]:
    """
    Validate permission code format.

    Valid formats:
        - resource.action (e.g., "user.read", "org.create")
        - resource.* (e.g., "user.*", "org.*")
        - *.* (full wildcard)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code or not isinstance(code, str):
        return False, "Permission code must be a non-empty string"
    if "." not in code:
        return (
            False,
            "Permission code must contain a dot (format: resource.action or resource.* or *.*)",
        )
    parts = code.split(".", 1)
    if len(parts) != 2:
        return False, "Permission code must have exactly one dot"
    resource_part, action_part = parts
    if not resource_part or not action_part:
        return False, "Permission code parts cannot be empty"
    if resource_part == "*" and action_part != "*":
        return False, "Full wildcard must be '*.*'"
    return True, None


def _convert_string_to_resource_type(value: str) -> ResourceType:
    """Convert string to ResourceType enum. Accepts 'org' and maps to ORGANIZATION."""
    if isinstance(value, ResourceType):
        return value
    normalized = _normalize_resource_for_db(value)
    try:
        return ResourceType(normalized)
    except ValueError:
        raise ValueError(f"Invalid resource type: {value}") from None


def _convert_string_to_action_type(value: str) -> ActionType:
    """Convert string to ActionType enum. Accepts '*.*', '.*', 'owner' and maps to MANAGE."""
    if isinstance(value, ActionType):
        return value
    normalized = _normalize_action_for_db(value)
    try:
        return ActionType(normalized)
    except ValueError:
        raise ValueError(f"Invalid action type: {value}") from None


class PermissionService:
    """Service for permission operations"""

    def __init__(self, db: Session):
        self.db = db
        self.permission_repo = PermissionRepository(db)

    def create_permission(self, permission_data: dict) -> dict:
        """
        Create a new permission.

        Valid permission code formats:
        - resource.action (e.g., "user.read", "org.create")
        - resource.* (e.g., "user.*", "org.*") - grants all actions for that resource
        - *.* - grants all permissions (all resources, all actions)

        Args:
            permission_data: Dictionary containing permission data

        Returns:
            Permission response dictionary

        Raises:
            DuplicatePermissionException: If code already exists
            ValueError: If code format is invalid
        """
        code = permission_data.get("code")
        logger.info(f"Creating permission: {code}")

        # Validate code format
        is_valid, error_msg = _validate_permission_code(code)
        if not is_valid:
            logger.warning(f"Invalid permission code format: {code} - {error_msg}")
            raise ValueError(error_msg or f"Invalid permission code format: {code}")

        existing = self.permission_repo.get_permission_by_code(code)

        if existing:
            logger.warning(f"Permission code already exists: {code}")
            raise DuplicatePermissionException(
                f"Permission code '{code}' already exists"
            )

        # Auto-derive resource and action from code if not provided
        self._derive_permission_metadata(permission_data)

        # Convert string values to enum types (if provided explicitly)
        self._convert_permission_metadata_to_enums(permission_data)

        permission = self.permission_repo.create_permission(permission_data)
        logger.info(f"Permission created: {permission.id}")

        return self._permission_to_dict(permission)

    def _derive_permission_metadata(self, permission_data: dict) -> None:
        """Derive resource and action from permission code if not provided."""
        code = permission_data.get("code")
        resource_prefix, action_part = _parse_permission_code(code)

        if resource_prefix and action_part:
            # Set resource based on code if not provided
            if not permission_data.get("resource"):
                if resource_prefix == "*":
                    permission_data["resource"] = ResourceType.ALL
                elif resource_prefix == "org":
                    permission_data["resource"] = ResourceType.ORGANIZATION
                else:
                    try:
                        permission_data["resource"] = ResourceType(resource_prefix)
                    except ValueError:
                        # If not in enum, use USER as default
                        permission_data["resource"] = ResourceType.USER

            # Set action based on code if not provided
            if not permission_data.get("action"):
                if action_part == "*":
                    permission_data["action"] = ActionType.MANAGE
                else:
                    try:
                        permission_data["action"] = ActionType(action_part)
                    except ValueError:
                        permission_data["action"] = ActionType.MANAGE

    def _convert_permission_metadata_to_enums(self, permission_data: dict) -> None:
        """Convert string metadata values to enum types."""
        if "resource" in permission_data and isinstance(
            permission_data["resource"], str
        ):
            permission_data["resource"] = _convert_string_to_resource_type(
                permission_data["resource"]
            )
        if "action" in permission_data and isinstance(permission_data["action"], str):
            permission_data["action"] = _convert_string_to_action_type(
                permission_data["action"]
            )

    def _permission_to_dict(self, permission: Permission) -> dict:
        """Convert a Permission object to a response dictionary."""
        return {
            "id": permission.id,
            "code": permission.code,
            "name": permission.name,
            "description": permission.description,
            "resource": _convert_enum_to_string(permission.resource),
            "action": _convert_enum_to_string(permission.action),
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
            raise PermissionNotFoundException(
                f"Permission with ID {permission_id} not found"
            )

        return {
            "id": permission.id,
            "code": permission.code,
            "name": permission.name,
            "description": permission.description,
            "resource": _convert_enum_to_string(permission.resource),
            "action": _convert_enum_to_string(permission.action),
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
        # Normalize filter values to match DB enum (org -> organization, *.*/owner -> manage)
        filter_resource = _normalize_resource_for_db(resource) if resource else None
        filter_action = _normalize_action_for_db(action) if action else None

        permissions, total_count = self.permission_repo.list_permissions(
            skip=skip,
            limit=limit,
            is_active=is_active,
            resource=filter_resource,
            action=filter_action,
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
                    "resource": _convert_enum_to_string(p.resource),
                    "action": _convert_enum_to_string(p.action),
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

    def get_permissions_grouped_by_category(
        self, organization_id: UUID | None = None, module: str | None = None
    ) -> dict:
        """
        Get permissions grouped by category for UI display.

        Args:
            organization_id: Optional organization ID to filter permissions
            module: Optional module filter

        Returns:
            Dictionary with categories and uncategorized permissions
        """
        logger.debug("Fetching permissions grouped by category")

        # Get all active permissions
        permissions, _ = self.permission_repo.list_permissions(
            skip=0,
            limit=10000,  # Get all permissions
            is_active=True,
            module=module,
        )

        # Group by category
        categories_dict: dict[str, list] = {}
        uncategorized = []

        for perm in permissions:
            perm_dict = {
                "id": perm.id,
                "code": perm.code,
                "name": perm.name,
                "description": perm.description,
                "resource": _convert_enum_to_string(perm.resource),
                "action": _convert_enum_to_string(perm.action),
                "module": perm.module,
                "category": perm.category,
                "is_active": perm.is_active,
                "extra_data": perm.extra_data,
                "created_at": perm.created_at,
                "updated_at": perm.updated_at,
            }

            # Determine category name
            category_name = perm.category or perm.module or "Other"

            # Map module to category name for UI
            if perm.module:
                module_to_category = {
                    "identity": "Identity & Access",
                    "core": "Business Operations",
                    "crm": "CRM & Sales",
                    "sales": "Sales & Orders",
                    "procurement": "Procurement",
                    "inventory": "Inventory",
                    "warehouse": "Inventory",
                    "accounting": "Accounting",
                    "billing": "Billing & Subscriptions",
                    "subscription": "Billing & Subscriptions",
                    "payment": "Billing & Subscriptions",
                    # legacy — keep for backward compat with existing DB rows
                    "platform": "Business Operations",
                }
                category_name = module_to_category.get(
                    perm.module.lower(), perm.category or perm.module or "Other"
                )

            if category_name and category_name != "Other":
                if category_name not in categories_dict:
                    categories_dict[category_name] = []
                categories_dict[category_name].append(perm_dict)
            else:
                uncategorized.append(perm_dict)

        # Convert to list format
        categories = []
        for category_name, perms in sorted(categories_dict.items()):
            # Determine icon based on category
            icon_map = {
                "Identity & Access": "shield",
                "Business Operations": "briefcase",
                "CRM & Sales": "users",
                "Sales & Orders": "shopping-cart",
                "Procurement": "truck",
                "Inventory": "box",
                "Inventory Management": "box",
                "Accounting": "calculator",
                "Billing & Subscriptions": "credit-card",
            }
            icon = icon_map.get(category_name)

            categories.append(
                {
                    "name": category_name,
                    "icon": icon,
                    "module": perms[0].get("module") if perms else None,
                    "permissions": perms,
                }
            )

        return {
            "categories": categories,
            "uncategorized": uncategorized,
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
            raise PermissionNotFoundException(
                f"Permission with ID {permission_id} not found"
            )

        # Remove None values from update_data
        filtered_data = {k: v for k, v in update_data.items() if v is not None}

        # Convert string values to enum types if present
        if "resource" in filtered_data:
            filtered_data["resource"] = _convert_string_to_resource_type(
                filtered_data["resource"]
            )
        if "action" in filtered_data:
            filtered_data["action"] = _convert_string_to_action_type(
                filtered_data["action"]
            )

        permission = self.permission_repo.update_permission(permission, filtered_data)
        logger.info(f"Permission updated: {permission.id}")

        return {
            "id": permission.id,
            "code": permission.code,
            "name": permission.name,
            "description": permission.description,
            "resource": _convert_enum_to_string(permission.resource),
            "action": _convert_enum_to_string(permission.action),
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
            raise PermissionNotFoundException(
                f"Permission with ID {permission_id} not found"
            )

        if self.permission_repo.check_permission_used_in_roles(permission_id):
            logger.warning(f"Cannot delete permission {permission_id} - used in roles")
            raise RolePermissionAlreadyAssignedException(
                "Cannot delete permission with active role assignments"
            )

        self.permission_repo.delete_permission(permission)
        logger.info(f"Permission deleted: {permission_id}")

    def get_or_create_permission_by_code(
        self, code: str, name: str | None = None, description: str | None = None
    ) -> Permission:
        """
        Get existing permission by code, or create it if it doesn't exist.

        Useful for ensuring wildcard permissions exist before assigning to roles.

        Args:
            code: Permission code (e.g., "user.*", "*.*", "user.read")
            name: Permission name (auto-generated if not provided)
            description: Permission description

        Returns:
            Permission object
        """
        existing = self.permission_repo.get_permission_by_code(code)
        if existing:
            return existing

        # Auto-generate name if not provided
        if not name:
            if code == "*.*":
                name = "Full access (all resources and actions)"
            elif code.endswith(".*"):
                resource = code.split(".")[0]
                name = f"All {resource} actions"
            else:
                resource, action = code.split(".", 1)
                name = f"{action.capitalize()} {resource}"

        permission_data = {
            "code": code,
            "name": name,
            "description": description,
        }
        # Resource and action will be auto-derived in create_permission
        self.create_permission(permission_data)
        return self.permission_repo.get_permission_by_code(code)

    @staticmethod
    def get_resource_prefix_for_code(code: str) -> str:
        """
        Extract resource prefix from permission code.

        Examples:
            "user.read" -> "user"
            "org.create" -> "org"
            "user.*" -> "user"
            "*.*" -> "*"

        Returns:
            Resource prefix string
        """
        resource_prefix, _ = _parse_permission_code(code)
        return resource_prefix or ""

    @staticmethod
    def is_wildcard_permission(code: str) -> bool:
        """
        Check if a permission code is a wildcard.

        Args:
            code: Permission code

        Returns:
            True if code is a wildcard (*.* or resource.*)
        """
        if not code:
            return False
        return code == "*.*" or code.endswith(".*")
