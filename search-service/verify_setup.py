"""Verify the search service setup is correct"""

import os
import sys

# Set environment variables
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("✓ Environment variables set")

# Test imports
try:
    from app.config import settings

    print(f"✓ Config loaded: {settings.app_name}")
except Exception as e:
    print(f"❌ Config failed: {e}")
    sys.exit(1)

try:
    from app.models.search import SearchQuery, SearchResponse, SearchResult

    print("✓ Search models imported")
except Exception as e:
    print(f"❌ Search models failed: {e}")
    sys.exit(1)

try:
    from app.models.user import UserContext

    print("✓ User models imported")
except Exception as e:
    print(f"❌ User models failed: {e}")
    sys.exit(1)

try:
    from app.security import decode_token

    print("✓ Security module imported")
except Exception as e:
    print(f"❌ Security module failed: {e}")
    sys.exit(1)

try:
    from app.logging_config import get_logger

    logger = get_logger(__name__)
    print("✓ Logging configured")
except Exception as e:
    print(f"❌ Logging failed: {e}")
    sys.exit(1)

# Test model creation
try:
    query = SearchQuery(query_text="test", page=1, page_size=20)
    print(f"✓ SearchQuery created: {query.query_text}")
except Exception as e:
    print(f"❌ SearchQuery creation failed: {e}")
    sys.exit(1)

try:
    result = SearchResult(
        entity_id="123",
        entity_type="items",
        title="Test",
        snippet="Test snippet",
        relevance_score=0.9,
    )
    print(f"✓ SearchResult created: {result.title}")
except Exception as e:
    print(f"❌ SearchResult creation failed: {e}")
    sys.exit(1)

try:
    response = SearchResponse(
        results=[result],
        total_count=1,
        page=1,
        page_size=20,
        query_time_ms=100,
    )
    print(f"✓ SearchResponse created: {response.total_count} results")
except Exception as e:
    print(f"❌ SearchResponse creation failed: {e}")
    sys.exit(1)

try:
    from uuid import uuid4

    context = UserContext(
        user_id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        user_type="user",
        permissions=["search.global"],
    )
    print(f"✓ UserContext created: {context.email}")
except Exception as e:
    print(f"❌ UserContext creation failed: {e}")
    sys.exit(1)

print("\n✅ All core components verified successfully!")
print("\nProject structure:")
print("  ✓ Configuration management")
print("  ✓ Data models (SearchQuery, SearchResult, SearchResponse)")
print("  ✓ User context and permissions")
print("  ✓ Security (JWT handling)")
print("  ✓ Logging infrastructure")
print("\nTask 1 implementation complete!")
