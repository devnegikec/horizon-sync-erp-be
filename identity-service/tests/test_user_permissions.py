"""Tests for user permissions endpoints"""

import pytest
from uuid import UUID

from app.models.role import Permission, Role, RolePermission, UserOrganizationRole


class TestGetMyPermissions:
    """Test GET /api/v1/users/me/permissions endpoint"""

    def test_get_my_permissions_success(
        self,
        client_no_override,
        db_session,
        test_user,
        test_organization,
        test_limited_role,
        test_permissions,
        auth_headers,
    ):
        """Test getting current user's permissions in an organization"""
        # Assign user to organization with role
        user_org_role = UserOrganizationRole(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=test_limited_role.id,
            is_active=True,
        )
        db_session.add(user_org_role)
        db_session.commit()

        # Make request
        response = client_no_override.get(
            f"/api/v1/users/me/permissions?organization_id={test_organization.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["organization_id"] == str(test_organization.id)
        assert data["has_access"] is True
        assert "user.read" in data["permissions"]
        assert test_limited_role.name in data["roles"]

    def test_get_my_permissions_no_access(
        self,
        client_no_override,
        db_session,
        test_user,
        auth_headers,
    ):
        """Test getting permissions for organization user doesn't belong to"""
        # Create a different organization
        from app.models.organization import Organization

        other_org = Organization(
            name="Other Org",
            slug="other-org",
            is_active=True,
        )
        db_session.add(other_org)
        db_session.commit()

        # Make request
        response = client_no_override.get(
            f"/api/v1/users/me/permissions?organization_id={other_org.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["organization_id"] == str(other_org.id)
        assert data["has_access"] is False
        assert data["permissions"] == []
        assert data["roles"] == []

    def test_get_my_permissions_unauthenticated(self, client_no_override, test_organization):
        """Test getting permissions without authentication"""
        response = client_no_override.get(
            f"/api/v1/users/me/permissions?organization_id={test_organization.id}"
        )

        assert response.status_code == 401

    def test_get_my_permissions_missing_org_id(self, client_no_override, auth_headers):
        """Test getting permissions without organization_id parameter"""
        response = client_no_override.get(
            "/api/v1/users/me/permissions",
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error


class TestGetUserPermissions:
    """Test GET /api/v1/users/{user_id}/permissions endpoint"""

    def test_get_user_permissions_success(
        self,
        client_no_override,
        db_session,
        test_user,
        test_organization,
        test_org_role,
        test_permissions,
        auth_headers,
    ):
        """Test getting another user's permissions (requires user.read)"""
        # Create another user
        from app.models.user import User

        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.flush()

        # Assign both users to organization with org_role (has user.read)
        for user in [test_user, other_user]:
            user_org_role = UserOrganizationRole(
                user_id=user.id,
                organization_id=test_organization.id,
                role_id=test_org_role.id,
                is_active=True,
            )
            db_session.add(user_org_role)

        db_session.commit()

        # Make request
        response = client_no_override.get(
            f"/api/v1/users/{other_user.id}/permissions?organization_id={test_organization.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(other_user.id)
        assert data["organization_id"] == str(test_organization.id)
        assert data["has_access"] is True
        assert test_org_role.name in data["roles"]

    def test_get_user_permissions_no_permission(
        self,
        client_no_override,
        db_session,
        test_user,
        test_organization,
        test_limited_role,
        auth_headers,
    ):
        """Test getting user permissions without user.read permission"""
        # Create another user
        from app.models.user import User

        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.flush()

        # Assign both users to organization with limited role (no user.read for management)
        for user in [test_user, other_user]:
            user_org_role = UserOrganizationRole(
                user_id=user.id,
                organization_id=test_organization.id,
                role_id=test_limited_role.id,
                is_active=True,
            )
            db_session.add(user_org_role)

        db_session.commit()

        # Make request
        response = client_no_override.get(
            f"/api/v1/users/{other_user.id}/permissions?organization_id={test_organization.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_get_user_permissions_target_not_in_org(
        self,
        client_no_override,
        db_session,
        test_user,
        test_organization,
        test_org_role,
        test_permissions,
        auth_headers,
    ):
        """Test getting permissions for user not in the organization"""
        # Create another user (not in organization)
        from app.models.user import User

        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.flush()

        # Only assign test_user to organization with org_role (has user.read)
        user_org_role = UserOrganizationRole(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=test_org_role.id,
            is_active=True,
        )
        db_session.add(user_org_role)
        db_session.commit()

        # Make request
        response = client_no_override.get(
            f"/api/v1/users/{other_user.id}/permissions?organization_id={test_organization.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_access"] is False
        assert data["permissions"] == []
        assert data["roles"] == []

    def test_get_user_permissions_requester_not_in_org(
        self,
        client_no_override,
        db_session,
        test_user,
        test_limited_role,
        test_permissions,
        auth_headers,
    ):
        """Test getting permissions when requester is not in the organization"""
        # Create another organization
        from app.models.organization import Organization

        other_org = Organization(
            name="Other Org",
            slug="other-org",
            is_active=True,
        )
        db_session.add(other_org)
        db_session.flush()

        # Create another user in the other org
        from app.models.user import User

        other_user = User(
            email="other@example.com",
            first_name="Other",
            last_name="User",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.flush()

        user_org_role = UserOrganizationRole(
            user_id=other_user.id,
            organization_id=other_org.id,
            role_id=test_limited_role.id,
            is_active=True,
        )
        db_session.add(user_org_role)
        db_session.commit()

        # Make request (test_user is not in other_org)
        response = client_no_override.get(
            f"/api/v1/users/{other_user.id}/permissions?organization_id={other_org.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "don't have access" in response.json()["detail"]
