"""Pytest configuration and fixtures for search service tests"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest

# Set test environment variables before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """
    Create a test database session.

    Creates a fresh database for each test function.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base
    # Import models to register them with Base.metadata
    import app.models.database  # noqa: F401
    
    # Debug: print what tables are registered
    print(f"Registered tables: {list(Base.metadata.tables.keys())}")

    # Create async engine for testing with StaticPool to maintain connection
    # This ensures the in-memory database persists for the entire test
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use StaticPool instead of NullPool
        echo=False,  # Disable SQL logging for cleaner output
    )

    # Create tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("Tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise

    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Yield session
    async with async_session() as session:
        try:
            yield session
        finally:
            # Rollback any pending transactions
            if session.in_transaction():
                await session.rollback()

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
def client(test_db) -> Generator:
    """
    Create a test client with database dependency override.
    """
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(test_db) -> AsyncGenerator:
    """
    Create an async test client with database dependency override.
    """
    from httpx import ASGITransport, AsyncClient
    from uuid import uuid4
    
    from app.database import get_db
    from app.dependencies import get_current_user
    from app.main import app
    from app.models.user import UserContext

    async def override_get_db():
        yield test_db
    
    # Mock user for testing
    async def override_get_current_user():
        return UserContext(
            user_id=uuid4(),
            email="test@example.com",
            organization_id=uuid4(),
            user_type="user",
            permissions=["search.global", "search.local", "*.*"]
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers() -> dict:
    """
    Create authentication headers for testing.
    
    Returns a mock JWT token that bypasses authentication.
    """
    from uuid import uuid4
    from app.security import create_access_token
    from app.models.user import UserContext
    
    # Create a test user context
    test_user = UserContext(
        user_id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        user_type="user",
        permissions=["search.global", "search.local", "*.*"]
    )
    
    # Create access token
    token = create_access_token(
        data={
            "sub": str(test_user.user_id),
            "email": test_user.email,
            "user_type": test_user.user_type,
            "type": "access"
        }
    )
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
async def test_search_documents(test_db):
    """
    Create test search documents in the database.
    """
    from app.models.database import SearchDocument
    
    documents = [
        SearchDocument(
            entity_id="item-1",
            entity_type="items",
            title="Dell Laptop",
            content="High-performance laptop with Intel processor",
            metadata_={"category": "electronics", "price": 999.99}
        ),
        SearchDocument(
            entity_id="item-2",
            entity_type="items",
            title="HP Laptop",
            content="Business laptop with AMD processor",
            metadata_={"category": "electronics", "price": 799.99}
        ),
        SearchDocument(
            entity_id="customer-1",
            entity_type="customers",
            title="Acme Corporation",
            content="Large enterprise customer",
            metadata_={"industry": "technology"}
        ),
        SearchDocument(
            entity_id="supplier-1",
            entity_type="suppliers",
            title="Tech Supplies Inc",
            content="Electronics supplier",
            metadata_={"country": "USA"}
        ),
    ]
    
    for doc in documents:
        test_db.add(doc)
    
    await test_db.commit()
    
    return documents
