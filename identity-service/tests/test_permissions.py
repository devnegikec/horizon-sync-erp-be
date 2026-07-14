"""Unit tests for permission endpoints and service"""

from uuid import UUID

import pytest

from app.core.exceptions import (
    DuplicatePermissionException,
    PermissionNotFoundException,
)


class TestPermissionService:
    """Tests for PermissionService"""

    def test_create_permission_success(self, db_session):
        """Test successful permission creation"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "user:create",
            "name": "Create User",
            "description": "Permission to create users",
            "resource": "users",
            "action": "create",
            "module": "auth",
            "category": "user_management",
            "is_active": True,
            "extra_data": {},
        }

        result = service.create_permission(permission_data)

        assert result["id"] is not None
        assert result["code"] == "user:create"
        assert result["name"] == "Create User"
        assert result["is_active"] is True

    def test_create_duplicate_permission(self, db_session):
        """Test creating duplicate permission"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "user:create",
            "name": "Create User",
            "description": "Permission to create users",
            "resource": "users",
            "action": "create",
            "module": "auth",
            "category": "user_management",
            "is_active": True,
            "extra_data": {},
        }

        service.create_permission(permission_data)

        with pytest.raises(DuplicatePermissionException):
            service.create_permission(permission_data)

    def test_get_permission_by_id(self, db_session):
        """Test getting permission by ID"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "user:read",
            "name": "Read User",
            "description": "Permission to read users",
            "resource": "users",
            "action": "read",
            "module": "auth",
            "category": "user_management",
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_permission(permission_data)
        retrieved = service.get_permission_by_id(created["id"])

        assert retrieved["id"] == created["id"]
        assert retrieved["code"] == "user:read"

    def test_get_permission_not_found(self, db_session):
        """Test getting non-existent permission"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)
        fake_id = UUID("00000000-0000-0000-0000-000000000000")

        with pytest.raises(PermissionNotFoundException):
            service.get_permission_by_id(fake_id)

    def test_list_permissions(self, db_session):
        """Test listing permissions"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        for i in range(5):
            permission_data = {
                "code": f"permission:{i}",
                "name": f"Permission {i}",
                "description": f"Test permission {i}",
                "resource": "users",
                "action": "read",
                "module": "auth",
                "category": "test",
                "is_active": True,
                "extra_data": {},
            }
            service.create_permission(permission_data)

        result = service.list_permissions(skip=0, limit=10)

        assert result["total"] == 5
        assert len(result["data"]) == 5

    def test_list_permissions_with_filters(self, db_session):
        """Test listing permissions with filters"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "user:create",
            "name": "Create User",
            "description": "Create user permission",
            "resource": "users",
            "action": "create",
            "module": "auth",
            "category": "admin",
            "is_active": True,
            "extra_data": {},
        }

        service.create_permission(permission_data)

        result = service.list_permissions(
            resource="users",
            action="create",
        )

        assert result["total"] >= 1

    def test_update_permission(self, db_session):
        """Test updating permission"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "user:update",
            "name": "Update User",
            "description": "Update user permission",
            "resource": "users",
            "action": "update",
            "module": "auth",
            "category": "user_management",
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_permission(permission_data)

        update_data = {
            "name": "Modify User",
            "description": "Updated description",
        }

        updated = service.update_permission(created["id"], update_data)

        assert updated["name"] == "Modify User"
        assert updated["description"] == "Updated description"

    def test_delete_permission(self, db_session):
        """Test deleting permission"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "user:delete",
            "name": "Delete User",
            "description": "Delete user permission",
            "resource": "users",
            "action": "delete",
            "module": "auth",
            "category": "admin",
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_permission(permission_data)
        service.delete_permission(created["id"])

        with pytest.raises(PermissionNotFoundException):
            service.get_permission_by_id(created["id"])


class TestPermissionEndpoints:
    """Tests for Permission API endpoints"""

    def test_list_permissions_endpoint(self, client):
        """Test GET /permissions endpoint"""
        response = client.get("/api/v1/permissions")

        assert response.status_code == 200
        assert "data" in response.json()
        assert "total" in response.json()

    def test_create_permission_endpoint(self, client, db_session):
        """Test POST /permissions endpoint"""
        permission_data = {
            "code": "test:create",
            "name": "Test Create",
            "description": "Test permission",
            "resource": "test",
            "action": "create",
            "module": "test",
            "category": "test",
            "is_active": True,
            "extra_data": {},
        }

        response = client.post(
            "/api/v1/permissions",
            json=permission_data,
        )

        assert response.status_code == 201
        assert response.json()["code"] == "test:create"

    def test_get_permission_endpoint(self, client, db_session):
        """Test GET /permissions/{id} endpoint"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "test:read",
            "name": "Test Read",
            "description": "Test permission",
            "resource": "test",
            "action": "read",
            "module": "test",
            "category": "test",
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_permission(permission_data)

        response = client.get(f"/api/v1/permissions/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == str(created["id"])

    def test_update_permission_endpoint(self, client, db_session):
        """Test PUT /permissions/{id} endpoint"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "test:update",
            "name": "Test Update",
            "description": "Test permission",
            "resource": "test",
            "action": "update",
            "module": "test",
            "category": "test",
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_permission(permission_data)

        update_data = {
            "name": "Updated Test",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/permissions/{created['id']}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Test"

    def test_delete_permission_endpoint(self, client, db_session):
        """Test DELETE /permissions/{id} endpoint"""
        from app.services.permission_service import PermissionService

        service = PermissionService(db_session)

        permission_data = {
            "code": "test:delete",
            "name": "Test Delete",
            "description": "Test permission",
            "resource": "test",
            "action": "delete",
            "module": "test",
            "category": "test",
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_permission(permission_data)

        response = client.delete(f"/api/v1/permissions/{created['id']}")

        assert response.status_code == 204
