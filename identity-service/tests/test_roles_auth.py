"""Unit tests for role API endpoints with authentication and authorization"""

from uuid import uuid4

from fastapi import status


class TestListRoles:
    """Tests for GET /roles endpoint"""

    def test_list_roles_without_token(self, client_no_override):
        """Test that list_roles returns 401 without auth token"""
        response = client_no_override.get("/api/v1/roles")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_roles_with_expired_token(
        self, client_no_override, db_session, expired_token
    ):
        """Test that list_roles returns 401 with expired token"""
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client_no_override.get("/api/v1/roles", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_roles_with_valid_token_but_no_permission(
        self, client_no_override, db_session, test_user_without_permission, access_token
    ):
        """Test that list_roles returns 403 without roles:read permission"""
        # Override to use user without permission
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.get("/api/v1/roles", headers=headers)

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_roles_with_valid_auth(self, client, test_organization):
        """Test that list_roles returns 200 with valid authentication"""
        response = client.get("/api/v1/roles")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_roles_with_org_filter(self, client, test_organization):
        """Test list_roles with organization filter"""
        response = client.get(
            "/api/v1/roles", params={"organization_id": str(test_organization.id)}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data


class TestGetRole:
    """Tests for GET /roles/{role_id} endpoint"""

    def test_get_role_without_token(self, client_no_override, test_org_role):
        """Test that get_role returns 401 without auth token"""
        response = client_no_override.get(f"/api/v1/roles/{test_org_role.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_role_with_valid_auth(self, client, test_org_role):
        """Test that get_role returns 200 with valid authentication"""
        response = client.get(f"/api/v1/roles/{test_org_role.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == test_org_role.code

    def test_get_role_from_different_org(
        self,
        client_no_override,
        db_session,
        test_user_other_org,
        test_org_role,
        access_token_other_user,
    ):
        """Test that user cannot get role from different organization"""
        from app.database import get_db
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_other_org

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user
        client_no_override.app.dependency_overrides[get_db] = override_get_db

        headers = {"Authorization": f"Bearer {access_token_other_user}"}
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}", headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_nonexistent_role(self, client):
        """Test that get_role returns 404 for nonexistent role"""
        response = client.get(f"/api/v1/roles/{uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateRole:
    """Tests for POST /roles endpoint"""

    def test_create_role_without_token(self, client_no_override, test_organization):
        """Test that create_role returns 401 without auth token"""
        role_data = {
            "code": "new_role",
            "name": "New Role",
            "organization_id": str(test_organization.id),
        }
        response = client_no_override.post("/api/v1/roles", json=role_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_role_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_organization,
        access_token,
    ):
        """Test that create_role returns 403 without roles:create permission"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        role_data = {
            "code": "new_role",
            "name": "New Role",
            "organization_id": str(test_organization.id),
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.post(
            "/api/v1/roles", json=role_data, headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_role_in_different_org(
        self,
        client_no_override,
        db_session,
        test_user_other_org,
        test_organization,
        access_token_other_user,
    ):
        """Test that user cannot create role in different organization"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_other_org

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        role_data = {
            "code": "new_role",
            "name": "New Role",
            "organization_id": str(test_organization.id),
        }
        headers = {"Authorization": f"Bearer {access_token_other_user}"}
        response = client_no_override.post(
            "/api/v1/roles", json=role_data, headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_role_success(self, client, test_organization):
        """Test successful role creation with proper auth"""
        role_data = {
            "code": "new_role",
            "name": "New Role",
            "description": "A new test role",
            "organization_id": str(test_organization.id),
        }
        response = client.post("/api/v1/roles", json=role_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["code"] == "new_role"
        assert data["name"] == "New Role"

    def test_create_duplicate_role_code(self, client, test_organization, test_org_role):
        """Test that duplicate role code returns 409"""
        role_data = {
            "code": test_org_role.code,  # Same code as existing role
            "name": "Duplicate Role",
            "organization_id": str(test_organization.id),
        }
        response = client.post("/api/v1/roles", json=role_data)
        assert response.status_code == status.HTTP_409_CONFLICT


class TestUpdateRole:
    """Tests for PUT /roles/{role_id} endpoint"""

    def test_update_role_without_token(self, client_no_override, test_org_role):
        """Test that update_role returns 401 without auth token"""
        update_data = {"name": "Updated Role"}
        response = client_no_override.put(
            f"/api/v1/roles/{test_org_role.id}", json=update_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_role_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        access_token,
    ):
        """Test that update_role returns 403 without roles:update permission"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        update_data = {"name": "Updated Role"}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.put(
            f"/api/v1/roles/{test_org_role.id}", json=update_data, headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_system_role_as_non_admin(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_system_role,
        access_token,
    ):
        """Test that non-admin cannot update system roles"""
        from app.dependencies import get_current_active_user

        # Give the user role management permission but not system admin
        test_user_without_permission.user_type = "ORG_ADMIN"
        db_session.commit()

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        update_data = {"name": "Hacked System Role"}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.put(
            f"/api/v1/roles/{test_system_role.id}", json=update_data, headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_role_success(self, client, test_org_role):
        """Test successful role update with proper auth"""
        update_data = {
            "name": "Updated Role Name",
            "description": "Updated description",
        }
        response = client.put(f"/api/v1/roles/{test_org_role.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Role Name"


class TestDeleteRole:
    """Tests for DELETE /roles/{role_id} endpoint"""

    def test_delete_role_without_token(self, client_no_override, test_org_role):
        """Test that delete_role returns 401 without auth token"""
        response = client_no_override.delete(f"/api/v1/roles/{test_org_role.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_role_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        access_token,
    ):
        """Test that delete_role returns 403 without roles:delete permission"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.delete(
            f"/api/v1/roles/{test_org_role.id}", headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_system_role_as_non_admin(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_system_role,
        access_token,
    ):
        """Test that non-admin cannot delete system roles"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.delete(
            f"/api/v1/roles/{test_system_role.id}", headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_role_success(self, client, test_org_role):
        """Test successful role deletion with proper auth"""
        response = client.delete(f"/api/v1/roles/{test_org_role.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestGetRolePermissions:
    """Tests for GET /roles/{role_id}/permissions endpoint"""

    def test_get_role_permissions_without_token(
        self, client_no_override, test_org_role
    ):
        """Test that get_role_permissions returns 401 without auth token"""
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}/permissions"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_role_permissions_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        access_token,
    ):
        """Test that get_role_permissions returns 403 without roles:read permission"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}/permissions", headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_role_permissions_success(self, client, test_org_role):
        """Test successful retrieval of role permissions"""
        response = client.get(f"/api/v1/roles/{test_org_role.id}/permissions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_role_permissions_from_different_org(
        self,
        client_no_override,
        db_session,
        test_user_other_org,
        test_org_role,
        access_token_other_user,
    ):
        """Test that user cannot get permissions from different org's role"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_other_org

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token_other_user}"}
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}/permissions", headers=headers
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAssignPermissionToRole:
    """Tests for POST /roles/{role_id}/permissions endpoint"""

    def test_assign_permission_without_token(
        self, client_no_override, test_org_role, test_permissions
    ):
        """Test that assign_permission returns 401 without auth token"""
        perm_data = {"permission_id": str(test_permissions["role.read"].id)}
        response = client_no_override.post(
            f"/api/v1/roles/{test_org_role.id}/permissions", json=perm_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_assign_permission_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        test_permissions,
        access_token,
    ):
        """Test that assign_permission returns 403 without roles:manage_perms"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        perm_data = {"permission_id": str(test_permissions["role.read"].id)}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.post(
            f"/api/v1/roles/{test_org_role.id}/permissions",
            json=perm_data,
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_permission_to_system_role_as_non_admin(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_system_role,
        test_permissions,
        access_token,
    ):
        """Test that non-admin cannot modify system role permissions"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        perm_data = {"permission_id": str(test_permissions["role.read"].id)}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.post(
            f"/api/v1/roles/{test_system_role.id}/permissions",
            json=perm_data,
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_permission_success(self, client, test_org_role, test_permissions):
        """Test successful permission assignment"""
        perm_data = {"permission_id": str(test_permissions["roles:read"].id)}
        response = client.post(
            f"/api/v1/roles/{test_org_role.id}/permissions", json=perm_data
        )
        assert response.status_code == status.HTTP_201_CREATED


class TestRemovePermissionFromRole:
    """Tests for DELETE /roles/{role_id}/permissions/{permission_id} endpoint"""

    def test_remove_permission_without_token(
        self, client_no_override, test_org_role, test_permissions
    ):
        """Test that remove_permission returns 401 without auth token"""
        response = client_no_override.delete(
            f"/api/v1/roles/{test_org_role.id}/permissions/{test_permissions['roles:read'].id}"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_remove_permission_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        test_permissions,
        access_token,
    ):
        """Test that remove_permission returns 403 without roles:manage_perms"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.delete(
            f"/api/v1/roles/{test_org_role.id}/permissions/{test_permissions['roles:read'].id}",
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_remove_permission_from_system_role_as_non_admin(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_system_role,
        test_permissions,
        access_token,
    ):
        """Test that non-admin cannot modify system role permissions"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.delete(
            f"/api/v1/roles/{test_system_role.id}/permissions/{test_permissions['roles:read'].id}",
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestBulkAssignPermissions:
    """Tests for POST /roles/{role_id}/permissions/bulk endpoint"""

    def test_bulk_assign_without_token(
        self, client_no_override, test_org_role, test_permissions
    ):
        """Test that bulk_assign returns 401 without auth token"""
        bulk_data = {
            "permission_ids": [str(test_permissions["role.read"].id)],
            "mode": "add",
        }
        response = client_no_override.post(
            f"/api/v1/roles/{test_org_role.id}/permissions/bulk", json=bulk_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_bulk_assign_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        test_permissions,
        access_token,
    ):
        """Test that bulk_assign returns 403 without roles:manage_perms"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        bulk_data = {
            "permission_ids": [str(test_permissions["role.read"].id)],
            "mode": "add",
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.post(
            f"/api/v1/roles/{test_org_role.id}/permissions/bulk",
            json=bulk_data,
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_assign_to_system_role_as_non_admin(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_system_role,
        test_permissions,
        access_token,
    ):
        """Test that non-admin cannot bulk assign to system roles"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        bulk_data = {
            "permission_ids": [str(test_permissions["role.read"].id)],
            "mode": "add",
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.post(
            f"/api/v1/roles/{test_system_role.id}/permissions/bulk",
            json=bulk_data,
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetRoleUsers:
    """Tests for GET /roles/{role_id}/users endpoint"""

    def test_get_role_users_without_token(
        self, client_no_override, test_org_role, test_organization
    ):
        """Test that get_role_users returns 401 without auth token"""
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}/users",
            params={"organization_id": str(test_organization.id)},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_role_users_without_permission(
        self,
        client_no_override,
        db_session,
        test_user_without_permission,
        test_org_role,
        test_organization,
        access_token,
    ):
        """Test that get_role_users returns 403 without roles:view_users permission"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_without_permission

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}/users",
            params={"organization_id": str(test_organization.id)},
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_role_users_from_different_org(
        self,
        client_no_override,
        db_session,
        test_user_other_org,
        test_org_role,
        test_organization,
        access_token_other_user,
    ):
        """Test that user cannot get users from different org's role"""
        from app.dependencies import get_current_active_user

        def override_get_current_active_user():
            return test_user_other_org

        client_no_override.app.dependency_overrides[
            get_current_active_user
        ] = override_get_current_active_user

        headers = {"Authorization": f"Bearer {access_token_other_user}"}
        response = client_no_override.get(
            f"/api/v1/roles/{test_org_role.id}/users",
            params={"organization_id": str(test_organization.id)},
            headers=headers,
        )

        # Clean up
        client_no_override.app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_role_users_success(self, client, test_org_role, test_organization):
        """Test successful retrieval of role users"""
        response = client.get(
            f"/api/v1/roles/{test_org_role.id}/users",
            params={"organization_id": str(test_organization.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
