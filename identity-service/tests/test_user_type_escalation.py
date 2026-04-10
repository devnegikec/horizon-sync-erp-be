"""Tests for user_type escalation guards in user endpoints (Task 4.2)"""

import os
from datetime import datetime
from uuid import UUID, uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min-32-chars")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.main import app
from app.models.base import UserStatus, UserType
from app.models.organization import Organization
from app.models.role import UserOrganizationRole
from app.models.user import User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Map PostgreSQL-specific types to SQLite-compatible types
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.close()


# Monkey-patch JSONB to JSON for SQLite compatibility
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON

_original_compile = None
try:
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
    if not hasattr(SQLiteTypeCompiler, 'visit_JSONB'):
        SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
except Exception:
    pass

TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_org(db_session):
    org = Organization(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Org",
        slug="test-org",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def test_role(db_session, test_org):
    from app.models.role import Role
    role = Role(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        code="test_role",
        name="Test Role",
        is_system=True,
        is_active=True,
        organization_id=test_org.id,
    )
    db_session.add(role)
    db_session.commit()
    return role


@pytest.fixture
def caller_user(db_session, test_org, test_role):
    """A system admin caller user."""
    user = User(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        email="caller@example.com",
        password_hash=hash_password("Test123!@#"),
        first_name="Caller",
        last_name="Admin",
        user_type=UserType.SYSTEM_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
    )
    db_session.add(user)
    uor = UserOrganizationRole(user_id=user.id, organization_id=test_org.id, role_id=test_role.id)
    db_session.add(uor)
    db_session.commit()
    return user


def _make_current_user(user_id, permissions, user_type=UserType.SYSTEM_ADMIN):
    return CurrentUser(
        id=user_id,
        email="caller@example.com",
        first_name="Caller",
        last_name="Admin",
        display_name=None,
        user_type=user_type,
        status=UserStatus.ACTIVE,
        is_active=True,
        permissions=permissions,
    )


def _setup_overrides(db_session, caller_id, permissions, user_type=UserType.SYSTEM_ADMIN):
    def override_db():
        yield db_session

    def override_user():
        return _make_current_user(caller_id, permissions, user_type)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_user


# ===================================================================
# create_user escalation guard tests
# ===================================================================

class TestCreateUserEscalationGuard:

    def test_create_system_admin_with_master_succeeds(self, db_session, test_org, caller_user):
        """Super admin (system_admin.master) CAN create a system_admin user."""
        _setup_overrides(db_session, caller_user.id, ["user.create", "system_admin.master"])
        try:
            with TestClient(app) as client:
                resp = client.post("/api/v1/identity/users", json={
                    "email": "newadmin@example.com",
                    "password": "StrongPass1!",
                    "first_name": "New",
                    "last_name": "Admin",
                    "user_type": "system_admin",
                })
            assert resp.status_code == 201, resp.text
            assert resp.json()["user_type"] == "system_admin"
        finally:
            app.dependency_overrides.clear()

    def test_create_system_admin_without_master_returns_403(self, db_session, test_org, caller_user):
        """Caller WITHOUT system_admin.master gets 403 when creating system_admin user."""
        _setup_overrides(db_session, caller_user.id, ["user.create", "system_admin.users_create"])
        try:
            with TestClient(app) as client:
                resp = client.post("/api/v1/identity/users", json={
                    "email": "newadmin@example.com",
                    "password": "StrongPass1!",
                    "first_name": "New",
                    "last_name": "Admin",
                    "user_type": "system_admin",
                })
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_create_regular_user_without_master_succeeds(self, db_session, test_org, caller_user):
        """Creating a non-system_admin user does NOT require system_admin.master."""
        _setup_overrides(db_session, caller_user.id, ["user.create"])
        try:
            with TestClient(app) as client:
                resp = client.post("/api/v1/identity/users", json={
                    "email": "regular@example.com",
                    "password": "StrongPass1!",
                    "first_name": "Regular",
                    "last_name": "User",
                    "user_type": "user",
                })
            assert resp.status_code == 201, resp.text
            assert resp.json()["user_type"] == "user"
        finally:
            app.dependency_overrides.clear()

    def test_create_user_no_type_field_succeeds(self, db_session, test_org, caller_user):
        """Creating a user without specifying user_type succeeds (no escalation check)."""
        _setup_overrides(db_session, caller_user.id, ["user.create"])
        try:
            with TestClient(app) as client:
                resp = client.post("/api/v1/identity/users", json={
                    "email": "noType@example.com",
                    "password": "StrongPass1!",
                    "first_name": "No",
                    "last_name": "Type",
                })
            assert resp.status_code == 201, resp.text
        finally:
            app.dependency_overrides.clear()


# ===================================================================
# update_user escalation guard tests
# ===================================================================

class TestUpdateUserEscalationGuard:

    def _create_target(self, db_session, test_org, test_role, user_type):
        target = User(
            id=uuid4(),
            email=f"target-{uuid4().hex[:6]}@example.com",
            password_hash=hash_password("Pass1234!"),
            first_name="Target",
            last_name="User",
            user_type=user_type,
            status=UserStatus.ACTIVE,
            is_active=True,
            email_verified=True,
        )
        db_session.add(target)
        uor = UserOrganizationRole(user_id=target.id, organization_id=test_org.id, role_id=test_role.id)
        db_session.add(uor)
        db_session.commit()
        return target

    def test_promote_to_system_admin_with_master_succeeds(self, db_session, test_org, test_role, caller_user):
        target = self._create_target(db_session, test_org, test_role, UserType.USER)
        _setup_overrides(db_session, caller_user.id, ["user.update", "user.read", "system_admin.master"])
        try:
            with TestClient(app) as client:
                resp = client.patch(f"/api/v1/identity/users/{target.id}", json={"user_type": "system_admin"})
            assert resp.status_code == 200, resp.text
            assert resp.json()["user_type"] == "system_admin"
        finally:
            app.dependency_overrides.clear()

    def test_promote_to_system_admin_without_master_returns_403(self, db_session, test_org, test_role, caller_user):
        target = self._create_target(db_session, test_org, test_role, UserType.USER)
        _setup_overrides(db_session, caller_user.id, ["user.update", "user.read", "system_admin.users_update"])
        try:
            with TestClient(app) as client:
                resp = client.patch(f"/api/v1/identity/users/{target.id}", json={"user_type": "system_admin"})
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_demote_from_system_admin_with_master_succeeds(self, db_session, test_org, test_role, caller_user):
        target = self._create_target(db_session, test_org, test_role, UserType.SYSTEM_ADMIN)
        _setup_overrides(db_session, caller_user.id, ["user.update", "user.read", "system_admin.master"])
        try:
            with TestClient(app) as client:
                resp = client.patch(f"/api/v1/identity/users/{target.id}", json={"user_type": "user"})
            assert resp.status_code == 200, resp.text
            assert resp.json()["user_type"] == "user"
        finally:
            app.dependency_overrides.clear()

    def test_demote_from_system_admin_without_master_returns_403(self, db_session, test_org, test_role, caller_user):
        target = self._create_target(db_session, test_org, test_role, UserType.SYSTEM_ADMIN)
        _setup_overrides(db_session, caller_user.id, ["user.update", "user.read", "system_admin.users_update"])
        try:
            with TestClient(app) as client:
                resp = client.patch(f"/api/v1/identity/users/{target.id}", json={"user_type": "user"})
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_update_non_type_field_no_escalation_check(self, db_session, test_org, test_role, caller_user):
        """Updating fields other than user_type does NOT trigger escalation guard."""
        target = self._create_target(db_session, test_org, test_role, UserType.USER)
        _setup_overrides(db_session, caller_user.id, ["user.update", "user.read"])
        try:
            with TestClient(app) as client:
                resp = client.patch(f"/api/v1/identity/users/{target.id}", json={"first_name": "Updated"})
            assert resp.status_code == 200, resp.text
            assert resp.json()["first_name"] == "Updated"
        finally:
            app.dependency_overrides.clear()
