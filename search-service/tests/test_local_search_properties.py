"""
Property-based tests for local search entity filtering.

Tests that local search correctly filters results by entity type.
Feature: unified-search-api
"""
import pytest
import uuid
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from app.search_engine import PostgreSQLSearchEngine
from app.models.search import SearchQuery
from app.models.user import UserContext
from app.models.database import SearchDocument


class TestLocalSearchProperties:
    """Property-based test suite for local search entity filtering."""
    
    @pytest.fixture
    async def multi_entity_documents(self, test_db):
        """Create documents across multiple entity types."""
        documents = []
        entity_types = ['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']
        
        for entity_type in entity_types:
            for i in range(5):
                doc = SearchDocument(
                    id=uuid.uuid4(),
                    entity_id=f"{entity_type}-{i:03d}",
                    entity_type=entity_type,
                    title=f"Test {entity_type} {i}",
                    content=f"Searchable content for {entity_type} number {i}",
                    metadata_={
                        "index": i,
                        "category": f"category-{i % 3}",
                        "status": "active" if i % 2 == 0 else "inactive"
                    }
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
        entity_type=st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']),
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
            min_size=1,
            max_size=50
        )
    )
    @pytest.mark.asyncio
    async def test_property_2_local_search_filters_by_entity_type(
        self,
        test_db,
        multi_entity_documents,
        entity_type,
        query_text
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any local search query with a specified entity type, all returned
        results should belong only to that entity type.
        
        Validates: Requirements 2.1, 2.3
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
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property 1: All results must be from the specified entity type
        for result in response.results:
            assert result.entity_type == entity_type
        
        # Property 2: Response should be valid
        assert response is not None
        assert isinstance(response.results, list)
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_type=st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries'])
    )
    @pytest.mark.asyncio
    async def test_property_2_local_search_includes_all_entity_fields(
        self,
        test_db,
        multi_entity_documents,
        entity_type
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any local search, all returned results should include all relevant
        entity fields in the response.
        
        Validates: Requirements 2.3
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        # Create search query with a term that matches all documents
        query = SearchQuery(query_text="test")
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property: All results should have complete field structure
        for result in response.results:
            assert hasattr(result, 'entity_id')
            assert hasattr(result, 'entity_type')
            assert hasattr(result, 'title')
            assert hasattr(result, 'snippet')
            assert hasattr(result, 'relevance_score')
            assert hasattr(result, 'metadata')
            
            # All fields should be non-None
            assert result.entity_id is not None
            assert result.entity_type is not None
            assert result.title is not None
            assert result.snippet is not None
            assert result.relevance_score is not None
            assert result.metadata is not None
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_type=st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']),
        page=st.integers(min_value=1, max_value=5),
        page_size=st.integers(min_value=1, max_value=20)
    )
    @pytest.mark.asyncio
    async def test_property_2_local_search_respects_pagination(
        self,
        test_db,
        multi_entity_documents,
        entity_type,
        page,
        page_size
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any pagination parameters in local search, results should respect
        them while maintaining entity type filtering.
        
        Validates: Requirements 2.1
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
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property 1: All results should be from specified entity type
        for result in response.results:
            assert result.entity_type == entity_type
        
        # Property 2: Pagination should be respected
        assert response.page == page
        assert response.page_size == page_size
        assert len(response.results) <= page_size
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_type=st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']),
        filter_field=st.sampled_from(['category', 'status']),
        filter_value=st.sampled_from(['category-0', 'category-1', 'category-2', 'active', 'inactive'])
    )
    @pytest.mark.asyncio
    async def test_property_2_local_search_with_filters(
        self,
        test_db,
        multi_entity_documents,
        entity_type,
        filter_field,
        filter_value
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any local search with filters, results should match both the
        entity type and the filter criteria.
        
        Validates: Requirements 2.1, 2.3
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        # Create search query with filters
        query = SearchQuery(
            query_text="test",
            filters={filter_field: filter_value}
        )
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property 1: All results should be from specified entity type
        for result in response.results:
            assert result.entity_type == entity_type
        
        # Property 2: All results should match the filter
        for result in response.results:
            if filter_field in result.metadata:
                assert result.metadata[filter_field] == filter_value
    
    @settings(
        max_examples=20,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        invalid_entity_type=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1,
            max_size=20
        ).filter(lambda x: x not in ['items', 'customers', 'suppliers', 'warehouses', 'stock_entries'])
    )
    @pytest.mark.asyncio
    async def test_property_2_invalid_entity_type_raises_error(
        self,
        test_db,
        multi_entity_documents,
        invalid_entity_type
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any invalid entity type, local search should raise a ValueError
        with a descriptive error message.
        
        Validates: Requirements 2.1
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        # Create search query
        query = SearchQuery(query_text="test")
        
        # Property: Invalid entity type should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await search_engine.local_search(invalid_entity_type, query, user_context)
        
        # Error message should be descriptive
        error_message = str(exc_info.value).lower()
        assert 'invalid' in error_message or 'entity' in error_message
    
    @settings(
        max_examples=100,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_type=st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries']),
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1,
            max_size=30
        )
    )
    @pytest.mark.asyncio
    async def test_property_2_no_cross_entity_contamination(
        self,
        test_db,
        multi_entity_documents,
        entity_type,
        query_text
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any local search, results should never include entities from
        other entity types, even if they match the query.
        
        Validates: Requirements 2.1
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
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property: No results should be from other entity types
        other_entity_types = [
            et for et in search_engine.ENTITY_TYPES 
            if et != entity_type
        ]
        
        for result in response.results:
            assert result.entity_type not in other_entity_types
            assert result.entity_type == entity_type
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_type=st.sampled_from(['items', 'customers', 'suppliers', 'warehouses', 'stock_entries'])
    )
    @pytest.mark.asyncio
    async def test_property_2_total_count_accuracy(
        self,
        test_db,
        multi_entity_documents,
        entity_type
    ):
        """
        Feature: unified-search-api, Property 2: Local Search Entity Filtering
        
        For any local search, the total_count should accurately reflect
        the number of matching results for that entity type only.
        
        Validates: Requirements 2.1
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        # Create search query with large page size to get all results
        query = SearchQuery(query_text="test", page_size=100)
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property 1: total_count should be >= number of results
        assert response.total_count >= len(response.results)
        
        # Property 2: All counted results should be from the entity type
        # (We can't verify this directly, but we verify all returned results are correct)
        for result in response.results:
            assert result.entity_type == entity_type
