"""Simple test to verify models work without pytest"""

import os
import sys

# Set environment variables
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from uuid import uuid4

from app.models.search import SearchQuery, SearchResponse, SearchResult
from app.models.user import UserContext


def test_search_query():
    """Test SearchQuery model"""
    print("Testing SearchQuery...")
    query = SearchQuery(query_text="test", page=1, page_size=20)
    assert query.query_text == "test"
    assert query.page == 1
    assert query.page_size == 20
    print("✓ SearchQuery works")


def test_search_result():
    """Test SearchResult model"""
    print("Testing SearchResult...")
    result = SearchResult(
        entity_id="123",
        entity_type="items",
        title="Test Item",
        snippet="Test snippet",
        relevance_score=0.9,
    )
    assert result.entity_id == "123"
    assert result.entity_type == "items"
    print("✓ SearchResult works")


def test_search_response():
    """Test SearchResponse model"""
    print("Testing SearchResponse...")
    response = SearchResponse(
        results=[],
        total_count=50,
        page=1,
        page_size=20,
        query_time_ms=100,
    )
    assert response.total_count == 50
    assert response.total_pages == 3
    assert response.has_next_page is True
    assert response.has_previous_page is False
    print("✓ SearchResponse works")


def test_user_context():
    """Test UserContext model"""
    print("Testing UserContext...")
    context = UserContext(
        user_id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        user_type="user",
        permissions=["search.global"],
    )
    assert context.has_permission("search.global") is True
    assert context.has_permission("search.admin") is False
    print("✓ UserContext works")


def test_user_context_wildcards():
    """Test UserContext wildcard permissions"""
    print("Testing UserContext wildcards...")
    context = UserContext(
        user_id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        user_type="user",
        permissions=["search.*"],
    )
    assert context.has_permission("search.global") is True
    assert context.has_permission("search.local") is True
    assert context.has_permission("item.read") is False
    print("✓ UserContext wildcards work")


def test_system_admin_permissions():
    """Test system admin has all permissions"""
    print("Testing system admin permissions...")
    context = UserContext(
        user_id=uuid4(),
        email="admin@example.com",
        organization_id=uuid4(),
        user_type="system_admin",
        permissions=[],
    )
    assert context.has_permission("search.global") is True
    assert context.has_permission("anything") is True
    print("✓ System admin permissions work")


if __name__ == "__main__":
    print("Running simple model tests...\n")
    try:
        test_search_query()
        test_search_result()
        test_search_response()
        test_user_context()
        test_user_context_wildcards()
        test_system_admin_permissions()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
