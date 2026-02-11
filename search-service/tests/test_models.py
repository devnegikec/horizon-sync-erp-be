"""Tests for core data models"""

import pytest

from app.models.search import SearchQuery, SearchResponse, SearchResult
from app.models.user import UserContext
from uuid import uuid4


class TestSearchQuery:
    """Tests for SearchQuery model"""

    def test_search_query_creation(self):
        """Test creating a valid search query"""
        query = SearchQuery(
            query_text="test query",
            entity_types=["items", "customers"],
            page=1,
            page_size=20,
        )
        assert query.query_text == "test query"
        assert query.entity_types == ["items", "customers"]
        assert query.page == 1
        assert query.page_size == 20

    def test_search_query_defaults(self):
        """Test search query default values"""
        query = SearchQuery(query_text="test")
        assert query.entity_types is None
        assert query.filters is None
        assert query.page == 1
        assert query.page_size == 20
        assert query.sort_by is None

    def test_search_query_invalid_page(self):
        """Test search query with invalid page number"""
        with pytest.raises(ValueError, match="Page must be >= 1"):
            SearchQuery(query_text="test", page=0)

    def test_search_query_invalid_page_size(self):
        """Test search query with invalid page size"""
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            SearchQuery(query_text="test", page_size=0)

        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            SearchQuery(query_text="test", page_size=101)


class TestSearchResult:
    """Tests for SearchResult model"""

    def test_search_result_creation(self):
        """Test creating a valid search result"""
        result = SearchResult(
            entity_id="123",
            entity_type="items",
            title="Test Item",
            snippet="This is a test item",
            relevance_score=0.95,
            metadata={"code": "ITEM-001"},
        )
        assert result.entity_id == "123"
        assert result.entity_type == "items"
        assert result.title == "Test Item"
        assert result.snippet == "This is a test item"
        assert result.relevance_score == 0.95
        assert result.metadata == {"code": "ITEM-001"}

    def test_search_result_default_metadata(self):
        """Test search result with default metadata"""
        result = SearchResult(
            entity_id="123",
            entity_type="items",
            title="Test Item",
            snippet="Test snippet",
            relevance_score=0.8,
        )
        assert result.metadata == {}


class TestSearchResponse:
    """Tests for SearchResponse model"""

    def test_search_response_creation(self):
        """Test creating a valid search response"""
        results = [
            SearchResult(
                entity_id="1",
                entity_type="items",
                title="Item 1",
                snippet="Snippet 1",
                relevance_score=0.9,
            ),
            SearchResult(
                entity_id="2",
                entity_type="items",
                title="Item 2",
                snippet="Snippet 2",
                relevance_score=0.8,
            ),
        ]
        response = SearchResponse(
            results=results,
            total_count=50,
            page=1,
            page_size=20,
            query_time_ms=150,
        )
        assert len(response.results) == 2
        assert response.total_count == 50
        assert response.page == 1
        assert response.page_size == 20
        assert response.query_time_ms == 150

    def test_search_response_total_pages(self):
        """Test total pages calculation"""
        response = SearchResponse(
            results=[],
            total_count=50,
            page=1,
            page_size=20,
            query_time_ms=100,
        )
        assert response.total_pages == 3  # 50 / 20 = 2.5, rounded up to 3

        response = SearchResponse(
            results=[],
            total_count=40,
            page=1,
            page_size=20,
            query_time_ms=100,
        )
        assert response.total_pages == 2  # 40 / 20 = 2

    def test_search_response_has_next_page(self):
        """Test has_next_page property"""
        response = SearchResponse(
            results=[],
            total_count=50,
            page=1,
            page_size=20,
            query_time_ms=100,
        )
        assert response.has_next_page is True

        response = SearchResponse(
            results=[],
            total_count=50,
            page=3,
            page_size=20,
            query_time_ms=100,
        )
        assert response.has_next_page is False

    def test_search_response_has_previous_page(self):
        """Test has_previous_page property"""
        response = SearchResponse(
            results=[],
            total_count=50,
            page=1,
            page_size=20,
            query_time_ms=100,
        )
        assert response.has_previous_page is False

        response = SearchResponse(
            results=[],
            total_count=50,
            page=2,
            page_size=20,
            query_time_ms=100,
        )
        assert response.has_previous_page is True


class TestUserContext:
    """Tests for UserContext model"""

    def test_user_context_creation(self):
        """Test creating a valid user context"""
        user_id = uuid4()
        org_id = uuid4()
        context = UserContext(
            user_id=user_id,
            email="test@example.com",
            organization_id=org_id,
            user_type="user",
            permissions=["search.global", "search.local"],
        )
        assert context.user_id == user_id
        assert context.email == "test@example.com"
        assert context.organization_id == org_id
        assert context.user_type == "user"
        assert context.permissions == ["search.global", "search.local"]

    def test_user_context_has_permission_exact_match(self):
        """Test permission check with exact match"""
        context = UserContext(
            user_id=uuid4(),
            email="test@example.com",
            organization_id=uuid4(),
            user_type="user",
            permissions=["search.global", "search.local"],
        )
        assert context.has_permission("search.global") is True
        assert context.has_permission("search.local") is True
        assert context.has_permission("search.admin") is False

    def test_user_context_has_permission_wildcard(self):
        """Test permission check with wildcard"""
        context = UserContext(
            user_id=uuid4(),
            email="test@example.com",
            organization_id=uuid4(),
            user_type="user",
            permissions=["search.*"],
        )
        assert context.has_permission("search.global") is True
        assert context.has_permission("search.local") is True
        assert context.has_permission("search.admin") is True
        assert context.has_permission("item.read") is False

    def test_user_context_has_permission_global_wildcard(self):
        """Test permission check with global wildcard"""
        context = UserContext(
            user_id=uuid4(),
            email="test@example.com",
            organization_id=uuid4(),
            user_type="user",
            permissions=["*.*"],
        )
        assert context.has_permission("search.global") is True
        assert context.has_permission("item.read") is True
        assert context.has_permission("anything.anything") is True

    def test_user_context_system_admin_has_all_permissions(self):
        """Test that system admin has all permissions"""
        context = UserContext(
            user_id=uuid4(),
            email="admin@example.com",
            organization_id=uuid4(),
            user_type="system_admin",
            permissions=[],
        )
        assert context.has_permission("search.global") is True
        assert context.has_permission("item.delete") is True
        assert context.has_permission("anything") is True
