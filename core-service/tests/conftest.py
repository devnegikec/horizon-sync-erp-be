"""Pytest configuration and fixtures"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.main import app

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
def mock_current_user():
    """Create a mock current user for testing"""
    return CurrentUser(
        id=uuid.uuid4(),
        email="test@example.com",
        organization_id=uuid.uuid4(),
        user_type="user",
        permissions=["item.create", "item.read", "item.update", "item.delete"],
    )


@pytest.fixture
def client(db_session, mock_current_user):
    """Create a test client with database session override"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_user():
        return mock_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_item_data(mock_current_user):
    """Sample item data for testing"""
    return {
        "item_code": "TEST-001",
        "item_name": "Test Item",
        "description": "A test item for unit tests",
        "item_type": "stock",
        "uom": "Nos",
        "maintain_stock": True,
        "standard_rate": "100.00",
        "valuation_rate": "75.00",
    }
