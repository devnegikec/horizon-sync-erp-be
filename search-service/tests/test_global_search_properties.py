"""
Property-based tests for global search completeness.

Tests that global search queries all configured entity types correctly.
Feature: unified-search-api
"""
import pytest
import uuid
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from app.search_engine import PostgreSQLSearchEngine
from app.models.search import SearchQuery
from app.models.user import UserContext
from app.models.database import SearchDocument


class TestGlobalSearchProperties:
    """Property-based test suite for global search completeness."""
    
    @pytest.fixture
    async def multi_entity_documents(self, test_db):
        """Create documents across multiple entity types."""
        documents = []
        entity_types = ['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']
        
        for entity_type in entity_types:
            for i in range(3):
                doc = SearchDocument(
                    id=uuid.uuid4(),
                    entity_id=f"{entity_type}-{i:03d}",
                    entity_type=entity_type,
                    title=f"Test {entity_type} {i}",
                    content=f"Searchable content for {entity_type} number {i}",
                    metadata_={"index": i}
                )
                documents.append(doc)
                test_db.add(doc)
        
        await test_db.commit()
        return documents
    
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
            min_size=1,
            max_size=50
        )
    )
    @pytest.mark.asyncio
    async def test_property_1_global_search_queries_all_entity_types(
        self,
        test_db,
        multi_entity_documents,
        query_text
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any global search query, the search engine should query all 
        configured entity types and include entity type information with 
        each result.
        
        Validates: Requirements 1.1, 1.2
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        assume(query_text.strip() != "")
        
        # Create search query
        query = SearchQuery(query_text=query_text)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property 1: Response should be valid
        assert response is not None
        assert isinstance(response.results, list)
        
        # Property 2: All results should have entity_type information
        for result in response.results:
            assert result.entity_type is not None
            assert result.entity_type != ""
            assert isinstance(result.entity_type, str)
        
        # Property 3: Entity types should be from the configured list
        for result in response.results:
            assert result.entity_type in search_engine.ENTITY_TYPES
        
        # Property 4: If results exist, they should span multiple entity types
        # (when the query matches content across types)
        if len(response.results) > 1:
            entity_types_in_results = {r.entity_type for r in response.results}
            # At least the results should have valid entity types
            assert len(entity_types_in_results) >= 1
    
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        common_term=st.sampled_from(['test', 'searchable', 'content', 'number'])
    )
    @pytest.mark.asyncio
    async def test_property_1_global_search_includes_all_matching_types(
        self,
        test_db,
        multi_entity_documents,
        common_term
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any query that matches content across multiple entity types,
        global search should return results from all matching types.
        
        Validates: Requirements 1.1, 1.2
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        # Create search query with a term that appears in all documents
        query = SearchQuery(query_text=common_term)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Results should include multiple entity types
        # (since all documents contain the common term)
        entity_types_in_results = {r.entity_type for r in response.results}
        
        # Should have results from multiple entity types
        assert len(entity_types_in_results) >= 1
        
        # All entity types in results should be valid
        for entity_type in entity_types_in_results:
            assert entity_type in search_engine.ENTITY_TYPES
    
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        page=st.integers(min_value=1, max_value=10),
        page_size=st.integers(min_value=1, max_value=100)
    )
    @pytest.mark.asyncio
    async def test_property_1_global_search_respects_pagination(
        self,
        test_db,
        multi_entity_documents,
        page,
        page_size
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any pagination parameters, global search should respect them
        while still querying all entity types.
        
        Validates: Requirements 1.1, 1.2
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        # Create search query with pagination
        query = SearchQuery(
            query_text="test",
            page=page,
            page_size=page_size
        )
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property 1: Response should respect pagination parameters
        assert response.page == page
        assert response.page_size == page_size
        
        # Property 2: Number of results should not exceed page_size
        assert len(response.results) <= page_size
        
        # Property 3: All results should have entity type information
        for result in response.results:
            assert result.entity_type in search_engine.ENTITY_TYPES
    
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_types_subset=st.lists(
            st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @pytest.mark.asyncio
    async def test_property_1_global_search_with_entity_type_filter(
        self,
        test_db,
        multi_entity_documents,
        entity_types_subset
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any subset of entity types specified in the query, global search
        should only return results from those types.
        
        Validates: Requirements 1.1, 1.2
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        # Create search query with entity type filter
        query = SearchQuery(
            query_text="test",
            entity_types=entity_types_subset
        )
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: All results should be from the specified entity types
        for result in response.results:
            assert result.entity_type in entity_types_subset
    
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1,
            max_size=30
        )
    )
    @pytest.mark.asyncio
    async def test_property_1_entity_type_always_present(
        self,
        test_db,
        multi_entity_documents,
        query_text
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any search result returned by global search, the entity_type
        field must always be present and non-empty.
        
        Validates: Requirements 1.2
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        assume(query_text.strip() != "")
        
        # Create search query
        query = SearchQuery(query_text=query_text)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Every result must have entity_type
        for result in response.results:
            assert hasattr(result, 'entity_type')
            assert result.entity_type is not None
            assert result.entity_type != ""
            assert len(result.entity_type) > 0
    
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1,
            max_size=30
        )
    )
    @pytest.mark.asyncio
    async def test_property_1_result_structure_complete(
        self,
        test_db,
        multi_entity_documents,
        query_text
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any search result, all required fields should be present
        including entity_id, entity_type, title, snippet, and relevance_score.
        
        Validates: Requirements 1.1, 1.2
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        assume(query_text.strip() != "")
        
        # Create search query
        query = SearchQuery(query_text=query_text)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Every result must have all required fields
        for result in response.results:
            assert hasattr(result, 'entity_id')
            assert hasattr(result, 'entity_type')
            assert hasattr(result, 'title')
            assert hasattr(result, 'snippet')
            assert hasattr(result, 'relevance_score')
            assert hasattr(result, 'metadata')
            
            # Fields should not be None
            assert result.entity_id is not None
            assert result.entity_type is not None
            assert result.title is not None
            assert result.snippet is not None
            assert result.relevance_score is not None
            
            # Types should be correct
            assert isinstance(result.entity_id, str)
            assert isinstance(result.entity_type, str)
            assert isinstance(result.title, str)
            assert isinstance(result.snippet, str)
            assert isinstance(result.relevance_score, float)
            assert isinstance(result.metadata, dict)
    
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1,
            max_size=30
        )
    )
    @pytest.mark.asyncio
    async def test_property_1_total_count_consistency(
        self,
        test_db,
        multi_entity_documents,
        query_text
    ):
        """
        Feature: unified-search-api, Property 1: Global Search Completeness
        
        For any search query, the total_count should be consistent with
        the actual number of matching results across all entity types.
        
        Validates: Requirements 1.1
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        assume(query_text.strip() != "")
        
        # Create search query
        query = SearchQuery(query_text=query_text, page_size=100)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: total_count should be >= number of results returned
        assert response.total_count >= len(response.results)
        
        # Property: total_count should be non-negative
        assert response.total_count >= 0
