"""Unit tests for role endpoints and service"""

import pytest
from uuid import UUID

from app.core.exceptions import (
    DuplicateRoleException,
    RoleHasUsersException,
    RoleNotFoundException,
    RolePermissionAlreadyAssignedException,
    SystemRoleModificationException,
)


class TestRoleService:
    """Tests for RoleService"""

    @pytest.fixture
    def organization_id(self):
        """Get or create test organization"""
        return UUID("11111111-1111-1111-1111-111111111111")

    @pytest.fixture
    def test_organization(self, db_session, organization_id):
        """Create a test organization"""
        from app.models.organization import Organization

        org = Organization(
            id=organization_id,
            name="Test Organization",
            slug="test-org",
            owner_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        db_session.add(org)
        db_session.commit()
        return org

    def test_create_role_success(self, db_session, test_organization):
        """Test successful role creation"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)

        role_data = {
            "name": "Admin",
            "code": "admin",
            "description": "Administrator role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 0,
            "is_active": True,
            "extra_data": {},
        }

        result = service.create_role(role_data, test_organization.id)

        assert result["id"] is not None
        assert result["name"] == "Admin"
        assert result["code"] == "admin"

    def test_create_duplicate_role(self, db_session, test_organization):
        """Test creating duplicate role"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)

        role_data = {
            "name": "Manager",
            "code": "manager",
            "description": "Manager role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 1,
            "is_active": True,
            "extra_data": {},
        }

        service.create_role(role_data, test_organization.id)

        with pytest.raises(DuplicateRoleException):
            service.create_role(role_data, test_organization.id)

    def test_get_role_by_id(self, db_session, test_organization):
        """Test getting role by ID"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)

        role_data = {
            "name": "Viewer",
            "code": "viewer",
            "description": "Viewer role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 2,
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_role(role_data, test_organization.id)
        retrieved = service.get_role_by_id(created["id"])

        assert retrieved["id"] == created["id"]
        assert retrieved["code"] == "viewer"

    def test_get_role_not_found(self, db_session):
        """Test getting non-existent role"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)
        fake_id = UUID("00000000-0000-0000-0000-000000000000")

        with pytest.raises(RoleNotFoundException):
            service.get_role_by_id(fake_id)

    def test_list_roles(self, db_session, test_organization):
        """Test listing roles"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)

        for i in range(3):
            role_data = {
                "name": f"Role {i}",
                "code": f"role_{i}",
                "description": f"Test role {i}",
                "is_system": False,
                "is_default": False,
                "hierarchy_level": i,
                "is_active": True,
                "extra_data": {},
            }
            service.create_role(role_data, test_organization.id)

        result = service.list_roles(
            organization_id=test_organization.id,
            skip=0,
            limit=10,
        )

        assert result["total"] >= 3

    def test_update_role(self, db_session, test_organization):
        """Test updating role"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)

        role_data = {
            "name": "Editor",
            "code": "editor",
            "description": "Editor role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 1,
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_role(role_data, test_organization.id)

        update_data = {
            "name": "Advanced Editor",
            "description": "Updated description",
        }

        updated = service.update_role(created["id"], update_data)

        assert updated["name"] == "Advanced Editor"

    def test_cannot_update_system_role(self, db_session, test_organization):
        """Test that system roles cannot be updated"""
        from app.services.role_service import RoleService
        from app.models.role import Role

        service = RoleService(db_session)

        role = Role(
            id=UUID("33333333-3333-3333-3333-333333333333"),
            organization_id=test_organization.id,
            name="System Admin",
            code="system_admin",
            description="System administrator role",
            is_system=True,
            is_default=False,
            hierarchy_level=0,
            is_active=True,
            extra_data={},
        )
        db_session.add(role)
        db_session.commit()

        with pytest.raises(SystemRoleModificationException):
            service.update_role(role.id, {"name": "Changed Name"})

    def test_delete_role(self, db_session, test_organization):
        """Test deleting role"""
        from app.services.role_service import RoleService

        service = RoleService(db_session)

        role_data = {
            "name": "Guest",
            "code": "guest",
            "description": "Guest role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 3,
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_role(role_data, test_organization.id)
        service.delete_role(created["id"])

        with pytest.raises(RoleNotFoundException):
            service.get_role_by_id(created["id"])

    def test_cannot_delete_system_role(self, db_session, test_organization):
        """Test that system roles cannot be deleted"""
        from app.services.role_service import RoleService
        from app.models.role import Role

        service = RoleService(db_session)

        role = Role(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            organization_id=test_organization.id,
            name="System Role",
            code="system_role",
            description="System role",
            is_system=True,
            is_default=False,
            hierarchy_level=0,
            is_active=True,
            extra_data={},
        )
        db_session.add(role)
        db_session.commit()

        with pytest.raises(SystemRoleModificationException):
            service.delete_role(role.id)

    def test_assign_permission_to_role(self, db_session, test_organization):
        """Test assigning permission to role"""
        from app.services.role_service import RoleService
        from app.models.role import Role, Permission

        service = RoleService(db_session)

        role = Role(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            organization_id=test_organization.id,
            name="Test Role",
            code="test_role",
            description="Test role",
            is_system=False,
            is_default=False,
            hierarchy_level=1,
            is_active=True,
            extra_data={},
        )
        db_session.add(role)

        permission = Permission(
            id=UUID("66666666-6666-6666-6666-666666666666"),
            code="user:read",
            name="Read User",
            description="Read user permission",
            resource="users",
            action="read",
            module="auth",
            category="user_management",
            is_active=True,
            extra_data={},
        )
        db_session.add(permission)
        db_session.commit()

        result = service.assign_permission_to_role(
            role.id,
            permission.id,
            {"test": "condition"},
        )

        assert result["role_id"] == role.id
        assert result["permission_id"] == permission.id
        assert result["conditions"]["test"] == "condition"

    def test_cannot_assign_duplicate_permission(self, db_session, test_organization):
        """Test that duplicate permission assignment fails"""
        from app.services.role_service import RoleService
        from app.models.role import Role, Permission

        service = RoleService(db_session)

        role = Role(
            id=UUID("77777777-7777-7777-7777-777777777777"),
            organization_id=test_organization.id,
            name="Test Role",
            code="test_role_dup",
            description="Test role",
            is_system=False,
            is_default=False,
            hierarchy_level=1,
            is_active=True,
            extra_data={},
        )
        db_session.add(role)

        permission = Permission(
            id=UUID("88888888-8888-8888-8888-888888888888"),
            code="user:write",
            name="Write User",
            description="Write user permission",
            resource="users",
            action="write",
            module="auth",
            category="user_management",
            is_active=True,
            extra_data={},
        )
        db_session.add(permission)
        db_session.commit()

        service.assign_permission_to_role(role.id, permission.id)

        with pytest.raises(RolePermissionAlreadyAssignedException):
            service.assign_permission_to_role(role.id, permission.id)

    def test_remove_permission_from_role(self, db_session, test_organization):
        """Test removing permission from role"""
        from app.services.role_service import RoleService
        from app.models.role import Role, Permission

        service = RoleService(db_session)

        role = Role(
            id=UUID("99999999-9999-9999-9999-999999999999"),
            organization_id=test_organization.id,
            name="Test Role",
            code="test_role_remove",
            description="Test role",
            is_system=False,
            is_default=False,
            hierarchy_level=1,
            is_active=True,
            extra_data={},
        )
        db_session.add(role)

        permission = Permission(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            code="user:delete",
            name="Delete User",
            description="Delete user permission",
            resource="users",
            action="delete",
            module="auth",
            category="admin",
            is_active=True,
            extra_data={},
        )
        db_session.add(permission)
        db_session.commit()

        service.assign_permission_to_role(role.id, permission.id)
        service.remove_permission_from_role(role.id, permission.id)

        # Try to get permission again - should return empty list
        result = service.get_role_permissions(role.id)
        assert result["total"] == 0

    def test_bulk_assign_permissions(self, db_session, test_organization):
        """Test bulk assigning permissions to role"""
        from app.services.role_service import RoleService
        from app.models.role import Role, Permission

        service = RoleService(db_session)

        role = Role(
            id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            organization_id=test_organization.id,
            name="Test Role",
            code="test_role_bulk",
            description="Test role",
            is_system=False,
            is_default=False,
            hierarchy_level=1,
            is_active=True,
            extra_data={},
        )
        db_session.add(role)
        db_session.commit()

        permission_ids = []
        for i in range(3):
            permission = Permission(
                code=f"test:action{i}",
                name=f"Test Action {i}",
                description=f"Test action {i}",
                resource="test",
                action=f"action{i}",
                module="test",
                category="test",
                is_active=True,
                extra_data={},
            )
            db_session.add(permission)
            db_session.flush()
            permission_ids.append(permission.id)

        db_session.commit()

        result = service.bulk_assign_permissions_to_role(
            role.id,
            permission_ids,
            "replace",
        )

        assert result["assigned_count"] == 3


class TestRoleEndpoints:
    """Tests for Role API endpoints"""

    def test_list_roles_endpoint(self, client):
        """Test GET /roles endpoint"""
        response = client.get("/api/v1/roles")

        assert response.status_code == 200
        assert "data" in response.json()
        assert "total" in response.json()

    def test_create_role_endpoint(self, client):
        """Test POST /roles endpoint"""
        role_data = {
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "name": "Test Role",
            "code": "test_role",
            "description": "Test role for endpoint",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 1,
            "is_active": True,
            "extra_data": {},
        }

        response = client.post(
            "/api/v1/roles",
            json=role_data,
        )

        assert response.status_code == 201

    def test_get_role_endpoint(self, client, db_session):
        """Test GET /roles/{id} endpoint"""
        from app.services.role_service import RoleService
        from app.models.organization import Organization
        from uuid import UUID

        org = Organization(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            name="Test Org",
            slug="test-org",
            owner_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        db_session.add(org)
        db_session.commit()

        service = RoleService(db_session)

        role_data = {
            "name": "Test Role",
            "code": "test_role_get",
            "description": "Test role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 1,
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_role(role_data, org.id)

        response = client.get(f"/api/v1/roles/{created['id']}")

        assert response.status_code == 200

    def test_update_role_endpoint(self, client, db_session):
        """Test PUT /roles/{id} endpoint"""
        from app.services.role_service import RoleService
        from app.models.organization import Organization
        from uuid import UUID

        org = Organization(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            name="Test Org",
            slug="test-org",
            owner_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        db_session.add(org)
        db_session.commit()

        service = RoleService(db_session)

        role_data = {
            "name": "Test Role",
            "code": "test_role_update",
            "description": "Test role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 1,
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_role(role_data, org.id)

        update_data = {
            "name": "Updated Role",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/roles/{created['id']}",
            json=update_data,
        )

        assert response.status_code == 200

    def test_delete_role_endpoint(self, client, db_session):
        """Test DELETE /roles/{id} endpoint"""
        from app.services.role_service import RoleService
        from app.models.organization import Organization
        from uuid import UUID

        org = Organization(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            name="Test Org",
            slug="test-org",
            owner_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        db_session.add(org)
        db_session.commit()

        service = RoleService(db_session)

        role_data = {
            "name": "Test Role",
            "code": "test_role_delete",
            "description": "Test role",
            "is_system": False,
            "is_default": False,
            "hierarchy_level": 1,
            "is_active": True,
            "extra_data": {},
        }

        created = service.create_role(role_data, org.id)

        response = client.delete(f"/api/v1/roles/{created['id']}")

        assert response.status_code == 204
