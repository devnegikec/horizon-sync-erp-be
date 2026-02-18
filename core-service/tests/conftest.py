"""Pytest configuration and fixtures"""

import os
import uuid

# Set required environment variables BEFORE importing app modules
# This is needed when running tests locally (outside Docker)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min-32-chars")
os.environ.setdefault("IDENTITY_SERVICE_URL", "http://localhost:8000")
os.environ.setdefault("DB_POOL_SIZE", "5")
os.environ.setdefault("DB_MAX_OVERFLOW", "10")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.dependencies import CurrentUser, get_current_active_user  # noqa: E402
from app.main import app  # noqa: E402

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
        db.execute(text("PRAGMA foreign_keys = OFF"))
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


@pytest.fixture
def test_item_group_data(mock_current_user):
    """Sample item group data for testing"""
    return {
        "name": "Test Electronics",
        "code": "TEST-ELEC-001",
        "description": "Test item group for electronics",
        "default_valuation_method": "FIFO",
        "default_uom": "Nos",
        "is_active": True,
    }


@pytest.fixture
def test_item_price_data(mock_current_user):
    """Sample item price data for testing"""
    return {
        "price": "99.99",
        "currency": "USD",
        "min_qty": 1,
        "extra_data": {"notes": "Test price"},
    }


@pytest.fixture
def sample_organization_id(mock_current_user):
    """Sample organization ID for testing"""
    return mock_current_user.organization_id


@pytest.fixture
def sample_user_id(mock_current_user):
    """Sample user ID for testing"""
    return mock_current_user.id


@pytest.fixture
def sample_item_id(db_session, mock_current_user):
    """Create a sample item and return its ID"""
    from app.models.item import Item
    
    item = Item(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        item_code="TEST-ITEM-001",
        item_name="Test Item",
        item_type="stock",
        uom="Nos",
        maintain_stock=True,
        standard_rate=100.00,
        valuation_rate=75.00,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item.id


@pytest.fixture
def sample_account_head_id():
    """Sample account head ID for testing"""
    return uuid.uuid4()
def auth_headers():
    """Return headers with Authorization for testing"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def sample_organization(mock_current_user):
    """Create a sample organization for testing"""
    # Return a simple object with an id attribute
    class Organization:
        def __init__(self, id):
            self.id = id
    
    return Organization(id=mock_current_user.organization_id)


@pytest.fixture
def sample_account(db_session, mock_current_user):
    """Create a sample account for testing"""
    from app.models.chart_of_account import Account
    from app.models.base import AccountType, AccountStatus
    
    account = Account(
        account_code="1000-01",
        account_name="Test Asset Account",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sample_parent_account(db_session, mock_current_user):
    """Create a sample parent account with children for testing"""
    from app.models.chart_of_account import Account
    from app.models.base import AccountType, AccountStatus
    
    # Create parent account
    parent = Account(
        account_code="1000-00",
        account_name="Parent Asset Account",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=False,  # Parent accounts cannot be posting accounts
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add(parent)
    db_session.flush()
    
    # Create child account
    child = Account(
        account_code="1000-01-CHILD",
        account_name="Child Asset Account",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        parent_account_id=parent.id,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add(child)
    db_session.commit()
    db_session.refresh(parent)
    return parent
