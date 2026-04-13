"""Tests for the system admin roles & permissions seed script."""

import os
import sys
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure env vars are set before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min-32-chars")

from app.core.security import hash_password
from app.database import Base
from app.models import (
    Organization,
    OrganizationStatus,
    OrganizationType,
    Permission,
    Role,
    RolePermission,
    User,
    UserOrganizationRole,
    UserStatus,
    UserType,
)
from app.models.entity_audit_log import EntityAuditLog
from scripts.seed_system_admin_roles import (
    PERMISSION_DEFS,
    ROLE_DEFS,
    _assign_super_admin_to_first_user,
    _get_or_create_master_org,
    _seed_permissions,
    _seed_roles,
)

# Build a separate SQLite engine that only creates the tables we need
# (avoids the JSONB issue in the invitations table)
_SEED_TABLES = [
    Organization.__table__,
    User.__table__,
    Role.__table__,
    Permission.__table__,
    RolePermission.__table__,
    UserOrganizationRole.__table__,
    EntityAuditLog.__table__,
]

_seed_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable FK support on SQLite
@event.listens_for(_seed_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

_SeedSession = sessionmaker(autocommit=False, autoflush=False, bind=_seed_engine)


@pytest.fixture
def db_session():
    """Create a fresh database with only the tables needed for seed tests."""
    Base.metadata.create_all(bind=_seed_engine, tables=_SEED_TABLES)
    session = _SeedSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_seed_engine, tables=_SEED_TABLES)


class TestPermissionDefinitions:
    """Verify the static permission definitions are correct."""

    def test_has_21_permissions(self):
        assert len(PERMISSION_DEFS) == 21

    def test_master_permission_present(self):
        codes = [p["code"] for p in PERMISSION_DEFS]
        assert "system_admin.master" in codes

    def test_all_domains_have_5_permissions(self):
        for domain in ("users", "organizations", "billing", "reporting"):
            domain_perms = [
                p for p in PERMISSION_DEFS if p["code"].startswith(f"system_admin.{domain}_")
            ]
            assert len(domain_perms) == 5, f"Domain '{domain}' should have 5 permissions"

    def test_all_permissions_have_system_admin_module(self):
        for p in PERMISSION_DEFS:
            assert p["module"] == "system_admin"


class TestRoleDefinitions:
    """Verify the static role definitions are correct."""

    def test_has_5_roles(self):
        assert len(ROLE_DEFS) == 5

    def test_role_codes(self):
        codes = {r["code"] for r in ROLE_DEFS}
        expected = {
            "super_admin",
            "system_user_manager",
            "system_org_manager",
            "system_billing_manager",
            "system_reports_viewer",
        }
        assert codes == expected

    def test_super_admin_has_master_permission(self):
        sa = next(r for r in ROLE_DEFS if r["code"] == "super_admin")
        assert sa["permission_codes"] == ["system_admin.master"]

    def test_reports_viewer_has_only_read(self):
        rv = next(r for r in ROLE_DEFS if r["code"] == "system_reports_viewer")
        assert rv["permission_codes"] == ["system_admin.reporting_read"]


class TestGetOrCreateMasterOrg:
    """Test master org find-or-create logic."""

    def test_creates_master_org_when_none_exists(self, db_session):
        org = _get_or_create_master_org(db_session)
        assert org is not None
        assert org.organization_type == OrganizationType.MASTER
        assert org.slug == "master-org"

    def test_returns_existing_master_org(self, db_session):
        existing = Organization(
            name="My Master",
            slug="my-master",
            organization_type=OrganizationType.MASTER,
            status=OrganizationStatus.ACTIVE,
            is_active=True,
        )
        db_session.add(existing)
        db_session.flush()

        org = _get_or_create_master_org(db_session)
        assert org.id == existing.id
        assert org.name == "My Master"


class TestSeedPermissions:
    """Test permission seeding."""

    def test_creates_all_21_permissions(self, db_session):
        perm_map = _seed_permissions(db_session)
        assert len(perm_map) == 21

    def test_idempotent_on_second_run(self, db_session):
        _seed_permissions(db_session)
        db_session.flush()
        perm_map = _seed_permissions(db_session)
        assert len(perm_map) == 21
        # Should still be exactly 21 in the DB
        count = db_session.query(Permission).filter(Permission.module == "system_admin").count()
        assert count == 21


class TestSeedRoles:
    """Test role and role-permission link seeding."""

    def test_creates_5_roles(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        role_map = _seed_roles(db_session, master_org.id, perm_map)
        assert len(role_map) == 5

    def test_roles_are_system_and_linked_to_master_org(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        role_map = _seed_roles(db_session, master_org.id, perm_map)
        for role in role_map.values():
            assert role.is_system is True
            assert role.organization_id == master_org.id

    def test_super_admin_role_linked_to_master_permission(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        role_map = _seed_roles(db_session, master_org.id, perm_map)
        sa_role = role_map["super_admin"]
        links = (
            db_session.query(RolePermission)
            .filter(RolePermission.role_id == sa_role.id)
            .all()
        )
        assert len(links) == 1
        linked_perm = db_session.query(Permission).get(links[0].permission_id)
        assert linked_perm.code == "system_admin.master"

    def test_idempotent_on_second_run(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        _seed_roles(db_session, master_org.id, perm_map)
        db_session.flush()
        role_map = _seed_roles(db_session, master_org.id, perm_map)
        assert len(role_map) == 5
        # Verify no duplicate role-permission links
        total_links = db_session.query(RolePermission).count()
        expected_links = sum(len(r["permission_codes"]) for r in ROLE_DEFS)
        assert total_links == expected_links


class TestAssignSuperAdmin:
    """Test Super Admin role assignment to first system_admin user."""

    def test_assigns_role_to_first_system_admin(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        role_map = _seed_roles(db_session, master_org.id, perm_map)

        user = User(
            email="admin@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Admin",
            last_name="User",
            user_type=UserType.SYSTEM_ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.flush()

        _assign_super_admin_to_first_user(db_session, master_org.id, role_map["super_admin"])

        uor = (
            db_session.query(UserOrganizationRole)
            .filter(UserOrganizationRole.user_id == user.id)
            .first()
        )
        assert uor is not None
        assert uor.role_id == role_map["super_admin"].id
        assert uor.organization_id == master_org.id

    def test_skips_if_user_already_has_role(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        role_map = _seed_roles(db_session, master_org.id, perm_map)

        user = User(
            email="admin@test.com",
            password_hash=hash_password("Test123!"),
            first_name="Admin",
            last_name="User",
            user_type=UserType.SYSTEM_ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            email_verified=True,
            email_verified_at=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.flush()

        # First assignment
        _assign_super_admin_to_first_user(db_session, master_org.id, role_map["super_admin"])
        # Second assignment — should be a no-op
        _assign_super_admin_to_first_user(db_session, master_org.id, role_map["super_admin"])

        count = (
            db_session.query(UserOrganizationRole)
            .filter(UserOrganizationRole.user_id == user.id)
            .count()
        )
        assert count == 1

    def test_skips_if_no_system_admin_user(self, db_session):
        master_org = _get_or_create_master_org(db_session)
        perm_map = _seed_permissions(db_session)
        role_map = _seed_roles(db_session, master_org.id, perm_map)

        # No users in DB — should not raise
        _assign_super_admin_to_first_user(db_session, master_org.id, role_map["super_admin"])

        count = db_session.query(UserOrganizationRole).count()
        assert count == 0
