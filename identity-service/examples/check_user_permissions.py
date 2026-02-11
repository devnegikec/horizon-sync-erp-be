#!/usr/bin/env python3
"""
Example script demonstrating how to check user permissions via the API.

This script shows how to:
1. Get the current user's permissions in an organization
2. Check if a user has specific permissions
3. Use permissions to control UI/navigation access
"""

import sys

import requests


class PermissionsClient:
    """Client for interacting with the user permissions API"""

    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def get_my_permissions(self, organization_id: str) -> dict:
        """
        Get current user's permissions in an organization.

        Args:
            organization_id: UUID of the organization

        Returns:
            Dict with user_id, organization_id, permissions, roles, has_access
        """
        url = f"{self.base_url}/api/v1/users/me/permissions"
        params = {"organization_id": organization_id}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        return response.json()

    def get_user_permissions(self, user_id: str, organization_id: str) -> dict:
        """
        Get a specific user's permissions in an organization.
        Requires user.read permission.

        Args:
            user_id: UUID of the user
            organization_id: UUID of the organization

        Returns:
            Dict with user_id, organization_id, permissions, roles, has_access
        """
        url = f"{self.base_url}/api/v1/users/{user_id}/permissions"
        params = {"organization_id": organization_id}

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        return response.json()

    def has_permission(self, permissions: list[str], required: str) -> bool:
        """
        Check if a permission list includes a specific permission.
        Supports wildcard permissions (e.g., user.*, *.*)

        Args:
            permissions: List of permission codes
            required: Required permission code

        Returns:
            True if permission is granted
        """
        if required in permissions:
            return True

        # Check for wildcard permissions
        resource, action = required.split(".", 1)

        # Check resource.* wildcard
        if f"{resource}.*" in permissions:
            return True

        # Check *.* wildcard (system admin)
        if "*.*" in permissions:
            return True

        return False


def display_user_permissions(my_perms: dict):
    """Display user permission details"""
    print(f"\nUser ID: {my_perms['user_id']}")
    print(f"Organization ID: {my_perms['organization_id']}")
    print(f"Has Access: {my_perms['has_access']}")
    print(f"Roles: {', '.join(my_perms['roles'])}")
    print(f"\nPermissions ({len(my_perms['permissions'])}):")
    for perm in sorted(my_perms["permissions"]):
        print(f"  - {perm}")


def check_specific_permissions(client: PermissionsClient, user_permissions: list[str]):
    """Check and display specific permissions"""
    print("\n" + "=" * 60)
    print("Permission Checks:")
    print("=" * 60)

    permissions_to_check = [
        "user.read",
        "user.create",
        "item.read",
        "item.create",
        "invoice.read",
        "invoice.create",
    ]

    for perm in permissions_to_check:
        has_perm = client.has_permission(user_permissions, perm)
        status = "✓" if has_perm else "✗"
        print(f"{status} {perm}")


def show_navigation_items(client: PermissionsClient, user_permissions: list[str]):
    """Display navigation items based on permissions"""
    print("\n" + "=" * 60)
    print("Navigation Items (based on permissions):")
    print("=" * 60)

    nav_items = {
        "Users": "user.read",
        "Items": "item.read",
        "Invoices": "invoice.read",
        "Customers": "customer.read",
        "Reports": "report.read",
        "Settings": "org.update",
    }

    for nav_item, required_perm in nav_items.items():
        if client.has_permission(user_permissions, required_perm):
            print(f"  ✓ Show: {nav_item}")
        else:
            print(f"  ✗ Hide: {nav_item}")


def check_other_user_permissions(
    client: PermissionsClient, user_permissions: list[str], organization_id: str
):
    """Check another user's permissions if current user has user.read permission"""
    if not client.has_permission(user_permissions, "user.read"):
        return

    print("\n" + "=" * 60)
    print("Checking another user's permissions...")
    print("=" * 60)

    OTHER_USER_ID = "22222222-2222-2222-2222-222222222222"

    try:
        other_perms = client.get_user_permissions(OTHER_USER_ID, organization_id)
        print(f"\nUser ID: {other_perms['user_id']}")
        print(f"Has Access: {other_perms['has_access']}")
        print(f"Roles: {', '.join(other_perms['roles'])}")
        print(f"Permissions: {len(other_perms['permissions'])}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"User {OTHER_USER_ID} not found in organization")
        else:
            raise


def main():
    """Example usage of the permissions API"""
    BASE_URL = "http://localhost:8000"
    ACCESS_TOKEN = "your-access-token-here"
    ORGANIZATION_ID = "11111111-1111-1111-1111-111111111111"

    client = PermissionsClient(BASE_URL, ACCESS_TOKEN)

    try:
        print("Fetching current user's permissions...")
        my_perms = client.get_my_permissions(ORGANIZATION_ID)

        display_user_permissions(my_perms)
        check_specific_permissions(client, my_perms["permissions"])
        show_navigation_items(client, my_perms["permissions"])
        check_other_user_permissions(client, my_perms["permissions"], ORGANIZATION_ID)

    except requests.exceptions.HTTPError as e:
        print(f"\nError: {e}")
        if e.response is not None:
            print(f"Response: {e.response.json()}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
