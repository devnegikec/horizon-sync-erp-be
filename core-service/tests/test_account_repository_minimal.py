"""Minimal account repository test to verify basic functionality"""

import os
import uuid

# Set environment variables before imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min-32-chars")
os.environ.setdefault("IDENTITY_SERVICE_URL", "http://localhost:8000")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.models.base import AccountStatus, AccountType
from app.repositories.chart_of_account_repository import AccountRepository


# Create test database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def account_repo(db_session):
    """Create an account repository instance"""
    return AccountRepository(db_session)


def test_create_and_get_account(account_repo):
    """Test basic create and retrieve operations"""
    test_data = {
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": AccountType.ASSET,
        "currency": "USD",
        "status": AccountStatus.ACTIVE,
        "is_posting_account": True,
        "description": "Test account",
        "created_by": str(uuid.uuid4()),
        "updated_by": str(uuid.uuid4()),
    }

    # Create account
    account = account_repo.create(test_data)
    assert account.id is not None
    assert account.account_code == "1000-01"

    # Get by ID
    retrieved = account_repo.get_by_id(account.id)
    assert retrieved is not None
    assert retrieved.account_code == "1000-01"

    # Get by code
    retrieved_by_code = account_repo.get_by_code("1000-01")
    assert retrieved_by_code is not None
    assert retrieved_by_code.id == account.id


def test_duplicate_code_fails(account_repo):
    """Test that duplicate account codes are rejected"""
    test_data = {
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": AccountType.ASSET,
        "currency": "USD",
        "status": AccountStatus.ACTIVE,
        "is_posting_account": True,
        "created_by": str(uuid.uuid4()),
        "updated_by": str(uuid.uuid4()),
    }

    account_repo.create(test_data)

    # Try to create duplicate
    duplicate_data = test_data.copy()
    duplicate_data["account_name"] = "Different Name"

    with pytest.raises(IntegrityError):
        account_repo.create(duplicate_data)


def test_list_with_filters(account_repo):
    """Test listing accounts with filters"""
    user_id = str(uuid.uuid4())

    # Create multiple accounts
    for i in range(3):
        data = {
            "account_code": f"1000-0{i+1}",
            "account_name": f"Account {i+1}",
            "account_type": AccountType.ASSET,
            "currency": "USD",
            "status": AccountStatus.ACTIVE,
            "is_posting_account": True,
            "created_by": user_id,
            "updated_by": user_id,
        }
        account_repo.create(data)

    # List all
    all_accounts = account_repo.list_all()
    assert len(all_accounts) == 3

    # Filter by type
    asset_accounts = account_repo.list_all(account_type=AccountType.ASSET)
    assert len(asset_accounts) == 3

    # Search
    search_results = account_repo.list_all(search="Account 1")
    assert len(search_results) == 1


def test_update_account(account_repo):
    """Test updating an account"""
    test_data = {
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": AccountType.ASSET,
        "currency": "USD",
        "status": AccountStatus.ACTIVE,
        "is_posting_account": True,
        "created_by": str(uuid.uuid4()),
        "updated_by": str(uuid.uuid4()),
    }

    account = account_repo.create(test_data)

    # Update
    update_data = {"account_name": "Updated Cash Account"}
    updated = account_repo.update(account, update_data)

    assert updated.account_name == "Updated Cash Account"
    assert updated.account_code == "1000-01"


def test_delete_account(account_repo):
    """Test deleting an account"""
    test_data = {
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": AccountType.ASSET,
        "currency": "USD",
        "status": AccountStatus.ACTIVE,
        "is_posting_account": True,
        "created_by": str(uuid.uuid4()),
        "updated_by": str(uuid.uuid4()),
    }

    account = account_repo.create(test_data)
    account_id = account.id

    # Delete
    account_repo.delete(account)

    # Verify deleted
    retrieved = account_repo.get_by_id(account_id)
    assert retrieved is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
