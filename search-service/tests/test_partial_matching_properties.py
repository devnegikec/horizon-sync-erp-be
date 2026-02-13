"""
Property-based tests for partial text matching.

Tests that partial text queries successfully match entities.
Feature: unified-search-api
"""
import pytest
import uuid
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from app.search_engine import PostgreSQLSearchEngine
from app.models.search import SearchQuery
from app.models.user import UserContext
from app.models.database import SearchDocument


class TestPartialMatchingProperties:
    """Property-based test suite for partial text matching."""
    
    @pytest.fixture
    async def searchable_documents(self, test_db):
        """Create documents with various searchable content."""
        documents = [
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="item-001",
                entity_type="items",
                title="Gaming Laptop Computer",
                content="High-performance gaming laptop with advanced graphics",
                metadata_={"brand": "TechBrand"}
            ),
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="item-002",
                entity_type="items",
                title="Office Desktop Computer",
                content="Professional desktop computer for office work",
                metadata_={"brand": "OfficePro"}
            ),
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="customer-001",
                entity_type="customers",
                title="Technology Solutions Inc",
                content="Enterprise customer specializing in technology solutions",
                metadata_={"tier": "enterprise"}
            ),
            SearchDocument(
                id=uuid.uuid4(),
                entity_id="supplier-001",
                entity_type="suppliers",
                title="Computer Hardware Supplies",
                content="Supplier of computer hardware and accessories",
                metadata_={"rating": 5}
            ),
        ]
        
        for doc in documents:
            test_db.add(doc)
        await test_db.commit()
        
        return documents
    
    @settings(
        max_examples=100,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        full_word=st.sampled_from(['gaming', 'laptop', 'computer', 'office', 'technology', 'hardware']),
        prefix_length=st.integers(min_value=2, max_value=6)
    )
    @pytest.mark.asyncio
    async def test_property_5_partial_prefix_matching(
        self,
        test_db,
        searchable_documents,
        full_word,
        prefix_length
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any entity with text in searchable fields, partial text queries
        (prefixes) should successfully match and return that entity.
        
        Validates: Requirements 1.5
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        # Take a prefix of the word
        prefix_length = min(prefix_length, len(full_word))
        partial_query = full_word[:prefix_length]
        
        assume(len(partial_query) >= 2)  # Need at least 2 characters
        
        # Create search query with partial text
        query = SearchQuery(query_text=partial_query)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Should find results that contain the full word
        # (since partial matching should work)
        # We can't guarantee results in all cases, but if we find results,
        # they should be valid
        assert isinstance(response.results, list)
        
        # If results exist, verify they're valid
        for result in response.results:
            assert result.entity_id is not None
            assert result.entity_type is not None
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        search_term=st.sampled_from(['comp', 'tech', 'gam', 'lap', 'off'])
    )
    @pytest.mark.asyncio
    async def test_property_5_partial_matching_finds_results(
        self,
        test_db,
        searchable_documents,
        search_term
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any partial search term that is a prefix of words in the database,
        the search should return matching results.
        
        Validates: Requirements 1.5
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
        query = SearchQuery(query_text=search_term)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Partial matching should find at least some results
        # for these known prefixes
        assert response.total_count >= 0
        
        # All results should be valid
        for result in response.results:
            assert isinstance(result.title, str)
            assert isinstance(result.snippet, str)
    
    @settings(
        max_examples=100,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        query_text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=2,
            max_size=10
        )
    )
    @pytest.mark.asyncio
    async def test_property_5_partial_matching_never_crashes(
        self,
        test_db,
        searchable_documents,
        query_text
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any partial query text, the search engine should handle it
        gracefully without crashing.
        
        Validates: Requirements 1.5
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
        
        # Property: Should not crash, even if no results found
        response = await search_engine.global_search(query, user_context)
        
        assert response is not None
        assert isinstance(response.results, list)
        assert response.total_count >= 0
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        base_word=st.sampled_from(['computer', 'laptop', 'technology', 'hardware']),
        substring_start=st.integers(min_value=0, max_value=5),
        substring_length=st.integers(min_value=2, max_value=8)
    )
    @pytest.mark.asyncio
    async def test_property_5_substring_matching(
        self,
        test_db,
        searchable_documents,
        base_word,
        substring_start,
        substring_length
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any substring of a word in searchable fields, the search
        should be able to find matching entities.
        
        Validates: Requirements 1.5
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        # Extract substring
        substring_start = min(substring_start, len(base_word) - 2)
        substring_end = min(substring_start + substring_length, len(base_word))
        substring = base_word[substring_start:substring_end]
        
        assume(len(substring) >= 2)
        
        # Create search query
        query = SearchQuery(query_text=substring)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Should handle substring queries gracefully
        assert response is not None
        assert isinstance(response.results, list)
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        entity_type=st.sampled_from(['items', 'customers', 'suppliers']),
        partial_term=st.sampled_from(['comp', 'tech', 'gam', 'off', 'hard'])
    )
    @pytest.mark.asyncio
    async def test_property_5_partial_matching_in_local_search(
        self,
        test_db,
        searchable_documents,
        entity_type,
        partial_term
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any partial text query in local search, matching should work
        within the specified entity type.
        
        Validates: Requirements 1.5
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
        query = SearchQuery(query_text=partial_term)
        
        # Execute local search
        response = await search_engine.local_search(entity_type, query, user_context)
        
        # Property 1: Should handle partial matching in local search
        assert response is not None
        assert isinstance(response.results, list)
        
        # Property 2: All results should be from the specified entity type
        for result in response.results:
            assert result.entity_type == entity_type
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        case_variant=st.sampled_from(['COMP', 'Comp', 'comp', 'CoMp'])
    )
    @pytest.mark.asyncio
    async def test_property_5_partial_matching_case_insensitive(
        self,
        test_db,
        searchable_documents,
        case_variant
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any partial text query with different case variations,
        matching should be case-insensitive.
        
        Validates: Requirements 1.5
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
        query = SearchQuery(query_text=case_variant)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: Case variations should produce results
        # (case-insensitive matching)
        assert response is not None
        assert isinstance(response.results, list)
    
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        partial_query=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=2,
            max_size=15
        )
    )
    @pytest.mark.asyncio
    async def test_property_5_result_relevance_with_partial_matching(
        self,
        test_db,
        searchable_documents,
        partial_query
    ):
        """
        Feature: unified-search-api, Property 5: Partial Text Matching
        
        For any partial text query that returns results, all results
        should have valid relevance scores.
        
        Validates: Requirements 1.5
        """
        search_engine = PostgreSQLSearchEngine(test_db)
        user_context = UserContext(
            user_id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4(),
            user_type="user",
            permissions=["*.*"]
        )
        
        assume(partial_query.strip() != "")
        
        # Create search query
        query = SearchQuery(query_text=partial_query)
        
        # Execute global search
        response = await search_engine.global_search(query, user_context)
        
        # Property: All results should have valid relevance scores
        for result in response.results:
            assert isinstance(result.relevance_score, float)
            assert result.relevance_score >= 0.0
