"""Tests for the has_permission function in core-service dependencies."""

import pytest

from app.dependencies import has_permission


class TestHasPermissionEdgeCases:
    """Test empty/None inputs."""

    def test_empty_permissions_returns_false(self):
        assert has_permission([], "item.read") is False

    def test_none_permission_returns_false(self):
        assert has_permission(["item.read"], "") is False

    def test_both_empty_returns_false(self):
        assert has_permission([], "") is False


class TestHasPermissionExactMatch:
    """Test exact permission matching."""

    def test_exact_match(self):
        assert has_permission(["item.read"], "item.read") is True

    def test_no_match(self):
        assert has_permission(["item.read"], "item.create") is False

    def test_exact_match_system_admin_perm(self):
        assert has_permission(["system_admin.users_read"], "system_admin.users_read") is True


class TestHasPermissionSystemAdminMaster:
    """Test system_admin.master grants all system_admin.* permissions."""

    def test_master_grants_users_read(self):
        assert has_permission(["system_admin.master"], "system_admin.users_read") is True

    def test_master_grants_organizations_create(self):
        assert has_permission(["system_admin.master"], "system_admin.organizations_create") is True

    def test_master_grants_billing_manage(self):
        assert has_permission(["system_admin.master"], "system_admin.billing_manage") is True

    def test_master_grants_reporting_delete(self):
        assert has_permission(["system_admin.master"], "system_admin.reporting_delete") is True

    def test_master_does_not_grant_non_system_admin(self):
        assert has_permission(["system_admin.master"], "item.read") is False

    def test_master_does_not_grant_warehouse_perm(self):
        assert has_permission(["system_admin.master"], "warehouse.create") is False


class TestHasPermissionManageExpansion:
    """Test _manage expansion: domain_manage grants domain_{read,create,update,delete}."""

    def test_users_manage_grants_users_read(self):
        assert has_permission(["system_admin.users_manage"], "system_admin.users_read") is True

    def test_users_manage_grants_users_create(self):
        assert has_permission(["system_admin.users_manage"], "system_admin.users_create") is True

    def test_users_manage_grants_users_update(self):
        assert has_permission(["system_admin.users_manage"], "system_admin.users_update") is True

    def test_users_manage_grants_users_delete(self):
        assert has_permission(["system_admin.users_manage"], "system_admin.users_delete") is True

    def test_users_manage_does_not_grant_orgs_read(self):
        assert has_permission(["system_admin.users_manage"], "system_admin.organizations_read") is False

    def test_orgs_manage_grants_orgs_update(self):
        assert has_permission(["system_admin.organizations_manage"], "system_admin.organizations_update") is True

    def test_billing_manage_grants_billing_create(self):
        assert has_permission(["system_admin.billing_manage"], "system_admin.billing_create") is True


class TestHasPermissionResourceWildcard:
    """Test resource.* wildcard matching (existing behavior preserved)."""

    def test_resource_wildcard_grants_action(self):
        assert has_permission(["warehouse.*"], "warehouse.read") is True

    def test_resource_wildcard_grants_any_action(self):
        assert has_permission(["item.*"], "item.delete") is True

    def test_resource_wildcard_does_not_cross_resources(self):
        assert has_permission(["item.*"], "warehouse.read") is False


class TestHasPermissionGlobalWildcardRemoved:
    """Test that *.* wildcard no longer grants access."""

    def test_global_wildcard_no_longer_grants_access(self):
        assert has_permission(["*.*"], "item.read") is False

    def test_global_wildcard_no_longer_grants_system_admin(self):
        assert has_permission(["*.*"], "system_admin.users_read") is False
