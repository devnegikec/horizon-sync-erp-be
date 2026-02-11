"""
Test script to verify search functionality with metadata filters.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.search_engine import PostgreSQLSearchEngine
from app.models.search import SearchQuery
from app.models.user import UserContext


async def test_search():
    """Test search with and without filters."""
    # Fix database URL for async driver
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, echo=False)
    session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        search_engine = PostgreSQLSearchEngine(session)
        
        # Create a mock user context
        user_context = UserContext(
            user_id="test-user",
            email="test@example.com",
            organization_id="test-org",
            user_type="system_admin",
            permissions=["search.global", "search.local"]
        )
        
        print("="*60)
        print("TEST 1: Global search without filters")
        print("="*60)
        query1 = SearchQuery(query_text="item")
        result1 = await search_engine.global_search(query1, user_context)
        print(f"Found {result1.total_count} results")
        for r in result1.results[:3]:
            print(f"  - {r.entity_type}: {r.title}")
        
        print("\n" + "="*60)
        print("TEST 2: Local search for items")
        print("="*60)
        query2 = SearchQuery(query_text="laptop")
        result2 = await search_engine.local_search("items", query2, user_context)
        print(f"Found {result2.total_count} results")
        for r in result2.results:
            print(f"  - {r.title}")
            print(f"    Metadata: {r.metadata}")
        
        print("\n" + "="*60)
        print("TEST 3: Search with metadata filter (JSONB test)")
        print("="*60)
        query3 = SearchQuery(
            query_text="item",
            filters={"item_group": "Raw Materials"}
        )
        try:
            result3 = await search_engine.global_search(query3, user_context)
            print(f"Found {result3.total_count} results with item_group=Raw Materials")
            for r in result3.results[:3]:
                print(f"  - {r.title}")
                print(f"    Metadata: {r.metadata}")
            print("\n✅ JSONB filter test PASSED!")
        except Exception as e:
            print(f"\n❌ JSONB filter test FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print("TEST 4: Search with wildcard query")
        print("="*60)
        query4 = SearchQuery(query_text="*")
        result4 = await search_engine.global_search(query4, user_context)
        print(f"Found {result4.total_count} results")
        
    await engine.dispose()
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_search())
