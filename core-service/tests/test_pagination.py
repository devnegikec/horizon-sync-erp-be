"""Unit tests for pagination utility"""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.core.pagination import (
    apply_pagination,
    create_pagination_meta,
    PaginationParams,
)


# Create test model
Base = declarative_base()


class TestModel(Base):
    """Test model for pagination"""

    __tablename__ = "test_items"

    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    priority = Column(String)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Add test data
    test_items = [
        TestModel(
            id=str(uuid4()),
            name=f"Item {i}",
            created_at=datetime(2024, 1, i + 1),
            priority="high" if i % 2 == 0 else "low",
        )
        for i in range(25)
    ]
    session.add_all(test_items)
    session.commit()

    yield session

    session.close()


class TestPaginationParams:
    """Test PaginationParams model"""

    def test_default_values(self):
        """Test default pagination parameters"""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by is None
        assert params.sort_order == "desc"

    def test_custom_values(self):
        """Test custom pagination parameters"""
        params = PaginationParams(
            page=2, page_size=10, sort_by="name", sort_order="asc"
        )
        assert params.page == 2
        assert params.page_size == 10
        assert params.sort_by == "name"
        assert params.sort_order == "asc"

    def test_page_validation(self):
        """Test page number validation"""
        with pytest.raises(ValueError):
            PaginationParams(page=0)

        with pytest.raises(ValueError):
            PaginationParams(page=-1)

    def test_page_size_validation(self):
        """Test page size validation"""
        with pytest.raises(ValueError):
            PaginationParams(page_size=0)

        with pytest.raises(ValueError):
            PaginationParams(page_size=101)

    def test_sort_order_validation(self):
        """Test sort order validation"""
        with pytest.raises(ValueError):
            PaginationParams(sort_order="invalid")


class TestApplyPagination:
    """Test apply_pagination function"""

    def test_basic_pagination(self, db_session):
        """Test basic pagination without sorting"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query, TestModel, page=1, page_size=10
        )

        assert len(items) == 10
        assert total == 25

    def test_second_page(self, db_session):
        """Test second page pagination"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query, TestModel, page=2, page_size=10
        )

        assert len(items) == 10
        assert total == 25

    def test_last_page_partial(self, db_session):
        """Test last page with partial results"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query, TestModel, page=3, page_size=10
        )

        assert len(items) == 5
        assert total == 25

    def test_page_beyond_total(self, db_session):
        """Test page number beyond total pages"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query, TestModel, page=10, page_size=10
        )

        assert len(items) == 0
        assert total == 25

    def test_sort_by_name_asc(self, db_session):
        """Test sorting by name ascending"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query, TestModel, page=1, page_size=5, sort_by="name", sort_order="asc"
        )

        assert len(items) == 5
        assert items[0].name == "Item 0"
        assert items[1].name == "Item 1"

    def test_sort_by_created_at_desc(self, db_session):
        """Test sorting by created_at descending (default)"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query, TestModel, page=1, page_size=5, sort_by="created_at", sort_order="desc"
        )

        assert len(items) == 5
        # Most recent first
        assert items[0].created_at > items[1].created_at

    def test_sort_by_invalid_field(self, db_session):
        """Test sorting by invalid field falls back to created_at"""
        query = db_session.query(TestModel)
        items, total = apply_pagination(
            query,
            TestModel,
            page=1,
            page_size=5,
            sort_by="nonexistent_field",
            sort_order="desc",
        )

        assert len(items) == 5
        assert total == 25
        # Should still return results with default sorting

    def test_empty_results(self, db_session):
        """Test pagination with no results"""
        query = db_session.query(TestModel).filter(TestModel.name == "Nonexistent")
        items, total = apply_pagination(
            query, TestModel, page=1, page_size=10
        )

        assert len(items) == 0
        assert total == 0

    def test_single_item(self, db_session):
        """Test pagination with single item"""
        query = db_session.query(TestModel).filter(TestModel.name == "Item 0")
        items, total = apply_pagination(
            query, TestModel, page=1, page_size=10
        )

        assert len(items) == 1
        assert total == 1


class TestCreatePaginationMeta:
    """Test create_pagination_meta function"""

    def test_first_page(self):
        """Test pagination metadata for first page"""
        meta = create_pagination_meta(page=1, page_size=10, total_count=25)

        assert meta.page == 1
        assert meta.page_size == 10
        assert meta.total_items == 25
        assert meta.total_pages == 3
        assert meta.has_next is True
        assert meta.has_prev is False

    def test_middle_page(self):
        """Test pagination metadata for middle page"""
        meta = create_pagination_meta(page=2, page_size=10, total_count=25)

        assert meta.page == 2
        assert meta.page_size == 10
        assert meta.total_items == 25
        assert meta.total_pages == 3
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_last_page(self):
        """Test pagination metadata for last page"""
        meta = create_pagination_meta(page=3, page_size=10, total_count=25)

        assert meta.page == 3
        assert meta.page_size == 10
        assert meta.total_items == 25
        assert meta.total_pages == 3
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_single_page(self):
        """Test pagination metadata for single page"""
        meta = create_pagination_meta(page=1, page_size=10, total_count=5)

        assert meta.page == 1
        assert meta.page_size == 10
        assert meta.total_items == 5
        assert meta.total_pages == 1
        assert meta.has_next is False
        assert meta.has_prev is False

    def test_empty_results(self):
        """Test pagination metadata for empty results"""
        meta = create_pagination_meta(page=1, page_size=10, total_count=0)

        assert meta.page == 1
        assert meta.page_size == 10
        assert meta.total_items == 0
        assert meta.total_pages == 0
        assert meta.has_next is False
        assert meta.has_prev is False

    def test_exact_page_boundary(self):
        """Test pagination metadata when total is exact multiple of page_size"""
        meta = create_pagination_meta(page=2, page_size=10, total_count=20)

        assert meta.page == 2
        assert meta.page_size == 10
        assert meta.total_items == 20
        assert meta.total_pages == 2
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_large_dataset(self):
        """Test pagination metadata with large dataset"""
        meta = create_pagination_meta(page=5, page_size=20, total_count=1000)

        assert meta.page == 5
        assert meta.page_size == 20
        assert meta.total_items == 1000
        assert meta.total_pages == 50
        assert meta.has_next is True
        assert meta.has_prev is True
