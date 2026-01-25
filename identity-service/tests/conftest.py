"""Pytest configuration and fixtures"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import UUID
from datetime import datetime, timedelta

from app.database import Base, get_db
from app.main import app
from app.dependencies import get_current_active_user
from app.models.user import User
from app.models.base import UserType, UserStatus
from app.core.security import create_token

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
def test_user(db_session):
    """Create a test user"""
    user = User(
        id=UUID("99999999-9999-9999-9999-999999999999"),
        email="test@example.com",
        password_hash="$2b$12$test_hash",
        first_name="Test",
        last_name="User",
        user_type=UserType.SYSTEM_ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    return user


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
def client(db_session, test_user, access_token):
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
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "Test123!@#",
        "first_name": "Test",
        "last_name": "User",
    }

