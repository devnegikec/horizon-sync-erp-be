"""Database connection and session management"""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

# Convert postgresql:// to postgresql+asyncpg:// for async support
# Handle SQLite for testing
if settings.database_url.startswith("sqlite"):
    # For SQLite, check if it already has the driver specified
    if "+aiosqlite" not in settings.database_url:
        # For SQLite, use aiosqlite for async
        async_database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        # Already has the driver
        async_database_url = settings.database_url
else:
    async_database_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

# Create async database engine
if settings.database_url.startswith("sqlite"):
    async_engine = create_async_engine(
        async_database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )
else:
    async_engine = create_async_engine(
        async_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        echo=settings.debug,  # Log SQL queries in debug mode
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create synchronous engine for migrations and non-async operations
if settings.database_url.startswith("sqlite"):
    sync_engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )
else:
    sync_engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        echo=settings.debug,
    )

# Create synchronous session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Base class for models
Base = declarative_base()


# Import models here so Alembic can detect them
def import_models():
    """Import all models to ensure they're registered with Base.metadata"""
    from app.models import database  # noqa: F401


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session.
    Yields a database session and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """
    Dependency function to get synchronous database session.
    Used for migrations and non-async operations.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
