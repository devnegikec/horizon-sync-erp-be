"""User context models for authorization"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class UserContext:
    """
    User context for authorization and filtering.

    Attributes:
        user_id: Unique identifier of the user
        email: User's email address
        organization_id: Organization the user belongs to
        user_type: Type of user (system_admin, org_admin, user)
        permissions: List of permission codes the user has
    """

    user_id: UUID
    email: str
    organization_id: UUID
    user_type: str
    permissions: list[str]

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.

        Supports wildcard matching:
        - Exact match: "item.read"
        - Resource wildcard: "item.*" matches all item permissions
        - Global wildcard: "*.*" matches all permissions

        Args:
            permission: Permission code to check (e.g., "item.read")

        Returns:
            True if user has the permission, False otherwise
        """
        if not permission:
            return False

        # System admins have all permissions
        if self.user_type == "system_admin":
            return True

        # Check exact match
        if permission in self.permissions:
            return True

        # Check global wildcard
        if "*.*" in self.permissions:
            return True

        # Check resource wildcard (e.g., "item.*" for "item.read")
        if "." in permission:
            resource = permission.split(".")[0]
            if f"{resource}.*" in self.permissions:
                return True

        return False
