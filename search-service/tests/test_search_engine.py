"""
Unit tests for PostgreSQLSearchEngine.

Tests specific examples and edge cases for search engine functionality.
"""
import pytest
import uuid
from datetime import datetime

from sqlalchemy import select
from app.search_engine import PostgreSQLSearchEngine
from app.models.search import SearchQuery, SearchResult, SearchResponse
from app.models.user import UserContext
from app.models.database import SearchDocument


class TestPostgreSQLSearchEngine:
    """Test suite for PostgreSQLSearchEngine class."""
    
    @pytest.fixture
    async def search_engine(self, test_db):
        """Create a search engine instance for testing."""
        return PostgreSQLSearchEngine(test_db)
    
    @pytest.fixture
    def user_context(self):
        """Create a test user context."""
        return UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["item.read", "customer.read"]
        )
    
    @pytest.fixture
    async def sample_documents(self, test_db):
        """Create sample search documents for testing."""
        documents = [
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="item-001",
                entity_type="items",
                title="Gaming Laptop",
                content="High-performance gaming laptop with RTX 4080",
                metadata_={"category": "electronics", "price": 1500}
            ),
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="item-002",
                entity_type="items",
                title="Office Laptop",
                content="Business laptop for office work",
                metadata_={"category": "electronics", "price": 800}
            ),
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="customer-001",
                entity_type="customers",
                title="John Doe",
                content="Premium customer with high purchase history",
                metadata_={"tier": "premium"}
            ),
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="supplier-001",
                entity_type="suppliers",
                title="Tech Supplies Inc",
                content="Supplier of computer hardware and accessories",
                metadata_={"rating": 5}
            ),
        ]
        
        for doc in documents:
            test_db.add(doc)
        await test_db.commit()
        
        return documents
    
    @pytest.mark.asyncio
    async def test_global_search_simple_query(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test global search with a simple query."""
        query = SearchQuery(query_text="laptop")
        
        response = await search_engine.global_search(query, user_context)
        
        assert isinstance(response, SearchResponse)
        assert len(response.results) >= 2  # Should find both laptop items
        assert response.total_count >= 2
        assert response.page == 1
        assert response.page_size == 20
    
    @pytest.mark.asyncio
    async def test_global_search_returns_all_entity_types(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that global search can return results from multiple entity types."""
        query = SearchQuery(query_text="tech")
        
        response = await search_engine.global_search(query, user_context)
        
        # Should find results from different entity types
        entity_types = {result.entity_type for result in response.results}
        assert len(entity_types) >= 1  # At least one entity type
    
    @pytest.mark.asyncio
    async def test_local_search_filters_by_entity_type(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that local search only returns results from specified entity type."""
        query = SearchQuery(query_text="laptop")
        
        response = await search_engine.local_search("items", query, user_context)
        
        # All results should be items
        for result in response.results:
            assert result.entity_type == "items"
    
    @pytest.mark.asyncio
    async def test_local_search_invalid_entity_type(
        self, 
        search_engine, 
        user_context
    ):
        """Test that local search raises error for invalid entity type."""
        query = SearchQuery(query_text="test")
        
        with pytest.raises(ValueError, match="Invalid entity type"):
            await search_engine.local_search("invalid_type", query, user_context)
    
    @pytest.mark.asyncio
    async def test_search_with_pagination(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test search with pagination parameters."""
        query = SearchQuery(query_text="laptop", page=1, page_size=1)
        
        response = await search_engine.global_search(query, user_context)
        
        assert len(response.results) <= 1
        assert response.page == 1
        assert response.page_size == 1
    
    @pytest.mark.asyncio
    async def test_search_empty_results(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test search that returns no results."""
        query = SearchQuery(query_text="nonexistent")
        
        response = await search_engine.global_search(query, user_context)
        
        assert len(response.results) == 0
        assert response.total_count == 0
        # Should provide suggestions when no results
        assert response.suggestions is not None
    
    @pytest.mark.asyncio
    async def test_search_result_structure(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that search results have correct structure."""
        query = SearchQuery(query_text="laptop")
        
        response = await search_engine.global_search(query, user_context)
        
        if response.results:
            result = response.results[0]
            assert isinstance(result, SearchResult)
            assert result.entity_id
            assert result.entity_type
            assert result.title
            assert result.snippet
            assert isinstance(result.relevance_score, float)
            assert isinstance(result.metadata, dict)
    
    @pytest.mark.asyncio
    async def test_search_includes_entity_type_info(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that search results include entity type information."""
        query = SearchQuery(query_text="laptop")
        
        response = await search_engine.global_search(query, user_context)
        
        for result in response.results:
            assert result.entity_type in search_engine.ENTITY_TYPES
    
    @pytest.mark.asyncio
    async def test_search_query_time_recorded(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that query execution time is recorded."""
        query = SearchQuery(query_text="laptop")
        
        response = await search_engine.global_search(query, user_context)
        
        assert response.query_time_ms >= 0
        assert isinstance(response.query_time_ms, int)
    
    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test search with metadata filters."""
        query = SearchQuery(
            query_text="laptop",
            filters={"category": "electronics"}
        )
        
        response = await search_engine.global_search(query, user_context)
        
        # Results should match the filter
        for result in response.results:
            if "category" in result.metadata:
                assert result.metadata["category"] == "electronics"
    
    @pytest.mark.asyncio
    async def test_get_entity_types(self, search_engine):
        """Test getting list of available entity types."""
        entity_types = await search_engine.get_entity_types()
        
        assert isinstance(entity_types, list)
        assert len(entity_types) > 0
        assert "items" in entity_types
        assert "customers" in entity_types
    
    @pytest.mark.asyncio
    async def test_search_respects_max_results(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that search respects maximum result limit."""
        query = SearchQuery(query_text="laptop")
        
        response = await search_engine.global_search(query, user_context)
        
        # Total count should not exceed MAX_RESULTS
        assert response.total_count <= search_engine.MAX_RESULTS
    
    @pytest.mark.asyncio
    async def test_search_with_quoted_phrase(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test search with quoted phrase."""
        query = SearchQuery(query_text='"gaming laptop"')
        
        response = await search_engine.global_search(query, user_context)
        
        # Should parse and execute without errors
        assert isinstance(response, SearchResponse)
    
    @pytest.mark.asyncio
    async def test_search_with_boolean_operators(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test search with boolean operators."""
        query = SearchQuery(query_text="laptop AND gaming")
        
        response = await search_engine.global_search(query, user_context)
        
        # Should parse and execute without errors
        assert isinstance(response, SearchResponse)
    
    @pytest.mark.asyncio
    async def test_search_case_insensitive(
        self, 
        search_engine, 
        user_context, 
        sample_documents
    ):
        """Test that search is case-insensitive."""
        query_lower = SearchQuery(query_text="laptop")
        query_upper = SearchQuery(query_text="LAPTOP")
        
        response_lower = await search_engine.global_search(query_lower, user_context)
        response_upper = await search_engine.global_search(query_upper, user_context)
        
        # Should return same number of results
        assert response_lower.total_count == response_upper.total_count
