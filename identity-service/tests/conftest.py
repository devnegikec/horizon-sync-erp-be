"""Pytest configuration and fixtures"""

import os
from datetime import datetime, timedelta
from uuid import UUID, uuid4

# Set required environment variables BEFORE importing app modules
# This is needed when running tests locally (outside Docker)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min-32-chars")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserStatus, UserType  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.role import Role, RoleHierarchy  # noqa: E402
from app.models.token import Permission  # noqa: E402
from app.core.security import create_token, hash_password  # noqa: E402
from app.dependencies import get_current_active_user  # noqa: E402

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_organization(db_session):
    """Create a test organization"""
    org = Organization(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Organization",
        description="Test Org for Unit Tests",
        slug="test-org",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def test_user(db_session, test_organization):
    """Create a test user with system admin role"""
    user = User(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        email="test@example.com",
        password_hash=hash_password("Test123!@#"),
        first_name="Test",
        last_name="User",
        user_type=UserType.SYSTEM_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
        organization_id=test_organization.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_without_permission(db_session, test_organization):
    """Create a test user without special permissions"""
    user = User(
        id=UUID("88888888-8888-8888-8888-888888888888"),
        email="noPerms@example.com",
        password_hash=hash_password("Test123!@#"),
        first_name="NoPermission",
        last_name="User",
        user_type=UserType.ORG_USER,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
        organization_id=test_organization.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_other_org(db_session):
    """Create a test user in a different organization"""
    org = Organization(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        name="Other Organization",
        description="Another Org for Testing",
        slug="other-org",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    
    user = User(
        id=UUID("77777777-7777-7777-7777-777777777777"),
        email="other@example.com",
        password_hash=hash_password("Test123!@#"),
        first_name="Other",
        last_name="User",
        user_type=UserType.ORG_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
        organization_id=org.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_permissions(db_session):
    """Create test permissions for roles - matching DB dump schema"""
    permissions = []
    # Permissions structure: (code, name, resource, action)
    permission_codes = [
        ("user.create", "Create User", "user", "create"),
        ("user.read", "Read User", "user", "read"),
        ("user.update", "Update User", "user", "update"),
        ("user.delete", "Delete User", "user", "delete"),
        ("user.manage", "Manage Users", "user", "manage"),
        ("org.create", "Create Org", "organization", "create"),
        ("org.read", "Read Org", "organization", "read"),
        ("org.update", "Update Org", "organization", "update"),
        ("org.delete", "Delete Org", "organization", "delete"),
        ("org.manage", "Manage Orgs", "organization", "manage"),
        ("role.create", "Create Role", "role", "create"),
        ("role.read", "Read Role", "role", "read"),
        ("role.update", "Update Role", "role", "update"),
        ("role.delete", "Delete Role", "role", "delete"),
        ("role.manage", "Manage Roles", "role", "manage"),
    ]
    
    for code, name, resource, action in permission_codes:
        perm = Permission(
            id=uuid4(),
            code=code,
            name=name,
            description=f"Permission to {name.lower()}",
            resource=resource,
            action=action,
            module="identity",
            is_active=True,
        )
        db_session.add(perm)
        permissions.append(perm)
    
    db_session.commit()
    return {perm.code: perm for perm in permissions}


@pytest.fixture
def test_system_role(db_session, test_organization, test_permissions):
    """Create a system role matching DB dump - system_admin"""
    role = Role(
        id=UUID("452a9306-3aeb-45da-9051-b0b312ad5ac0"),
        code="system_admin",
        name="System Administrator",
        description="Full system access",
        hierarchy_level=100,
        is_system=True,
        is_active=True,
        organization_id=test_organization.id,
    )
    db_session.add(role)
    db_session.commit()
    
    # Add all permissions to system admin role
    for perm in test_permissions.values():
        role.permissions.append(perm)
    
    db_session.commit()
    return role


@pytest.fixture
def test_org_role(db_session, test_organization, test_permissions):
    """Create an organization role matching DB dump - org_admin"""
    role = Role(
        id=UUID("3e24101a-db60-497d-87d2-ba31ac302204"),
        code="org_admin",
        name="Organization Administrator",
        description="Org-level admin access",
        hierarchy_level=50,
        is_system=True,
        is_active=True,
        organization_id=test_organization.id,
    )
    db_session.add(role)
    db_session.commit()
    
    # Add org and role management permissions
    org_perms = ["org.create", "org.read", "org.update", "org.delete", "org.manage",
                 "role.create", "role.read", "role.update", "role.delete", "role.manage"]
    for perm_code in org_perms:
        if perm_code in test_permissions:
            role.permissions.append(test_permissions[perm_code])
    
    db_session.commit()
    return role


@pytest.fixture
def test_limited_role(db_session, test_organization, test_permissions):
    """Create an organization role matching DB dump - user role"""
    role = Role(
        id=UUID("267b57d0-2801-49c9-8d40-b6291ff37de0"),
        code="user",
        name="User",
        description="Standard user access",
        hierarchy_level=10,
        is_system=True,
        is_active=True,
        is_default=True,
        organization_id=test_organization.id,
    )
    db_session.add(role)
    db_session.commit()
    
    # Add only user read permission
    if "user.read" in test_permissions:
        role.permissions.append(test_permissions["user.read"])
    
    db_session.commit()
    return role


@pytest.fixture
def access_token(test_user):
    """Create a valid access token for test user"""
    token = create_token(
        subject=str(test_user.id),
        token_type="access",
        expires_delta=timedelta(hours=1),
    )
    return token


@pytest.fixture
def access_token_other_user(test_user_other_org):
    """Create a valid access token for other user"""
    token = create_token(
        subject=str(test_user_other_org.id),
        token_type="access",
        expires_delta=timedelta(hours=1),
    )
    return token


@pytest.fixture
def expired_token(test_user):
    """Create an expired access token"""
    token = create_token(
        subject=str(test_user.id),
        token_type="access",
        expires_delta=timedelta(seconds=-1),  # Already expired
    )
    return token


@pytest.fixture
def client(db_session, test_user):
    """Create a test client with database session override"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_active_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client_no_override(db_session):
    """Create a test client WITHOUT dependency overrides (for auth testing)"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "Test123!@#",
        "first_name": "Test",
        "last_name": "User",
    }
