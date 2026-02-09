"""
Property-based tests for empty query rejection.

Tests that empty or whitespace-only queries are properly rejected.
Feature: unified-search-api
"""
import pytest
from hypothesis import given, strategies as st, settings
from app.query_parser import QueryParser


class TestEmptyQueryProperties:
    """Property-based test suite for empty query rejection."""
    
    @settings(max_examples=100, deadline=5000)
    @given(
        whitespace_chars=st.lists(
            st.sampled_from([' ', '\t', '\n', '\r', '\f', '\v']),
            min_size=0,
            max_size=20
        )
    )
    def test_property_4_empty_query_rejection(self, whitespace_chars):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For any search query that is empty or contains only whitespace characters,
        the query parser should reject the query and return an appropriate error.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Create a query with only whitespace
        query_text = ''.join(whitespace_chars)
        
        # Property: Empty or whitespace-only queries should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parser.parse(query_text)
        
        # Property: Error message should be descriptive
        error_message = str(exc_info.value).lower()
        assert 'empty' in error_message or 'whitespace' in error_message
    
    @settings(max_examples=100, deadline=5000)
    @given(
        prefix_whitespace=st.text(
            alphabet=st.characters(whitelist_categories=('Zs',)),
            min_size=0,
            max_size=10
        ),
        suffix_whitespace=st.text(
            alphabet=st.characters(whitelist_categories=('Zs',)),
            min_size=0,
            max_size=10
        ),
        content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                min_codepoint=32,
                max_codepoint=126
            ),
            min_size=1,
            max_size=50
        )
    )
    def test_property_4_non_empty_query_accepted(
        self, 
        prefix_whitespace, 
        suffix_whitespace, 
        content
    ):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For any query with actual content (even if surrounded by whitespace),
        the parser should successfully parse it.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Skip if content is only whitespace
        if not content.strip():
            return
        
        # Create query with content surrounded by whitespace
        query_text = f"{prefix_whitespace}{content}{suffix_whitespace}"
        
        # Property: Non-empty queries should parse successfully
        result = parser.parse(query_text)
        assert result is not None
        assert result.original == query_text
    
    @settings(max_examples=100, deadline=5000)
    @given(
        empty_string=st.just('')
    )
    def test_property_4_empty_string_rejected(self, empty_string):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For an empty string, the parser should reject it with ValueError.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Property: Empty string should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parser.parse(empty_string)
        
        error_message = str(exc_info.value).lower()
        assert 'empty' in error_message or 'whitespace' in error_message
    
    @settings(max_examples=100, deadline=5000)
    @given(
        space_count=st.integers(min_value=1, max_value=100)
    )
    def test_property_4_multiple_spaces_rejected(self, space_count):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For any number of spaces, the parser should reject it as empty.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Create query with only spaces
        query_text = ' ' * space_count
        
        # Property: Space-only queries should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parser.parse(query_text)
        
        error_message = str(exc_info.value).lower()
        assert 'empty' in error_message or 'whitespace' in error_message
    
    @settings(max_examples=100, deadline=5000)
    @given(
        tab_count=st.integers(min_value=1, max_value=50)
    )
    def test_property_4_tabs_only_rejected(self, tab_count):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For any number of tabs, the parser should reject it as empty.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Create query with only tabs
        query_text = '\t' * tab_count
        
        # Property: Tab-only queries should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parser.parse(query_text)
        
        error_message = str(exc_info.value).lower()
        assert 'empty' in error_message or 'whitespace' in error_message
    
    @settings(max_examples=100, deadline=5000)
    @given(
        newline_count=st.integers(min_value=1, max_value=50)
    )
    def test_property_4_newlines_only_rejected(self, newline_count):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For any number of newlines, the parser should reject it as empty.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Create query with only newlines
        query_text = '\n' * newline_count
        
        # Property: Newline-only queries should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parser.parse(query_text)
        
        error_message = str(exc_info.value).lower()
        assert 'empty' in error_message or 'whitespace' in error_message
    
    @settings(max_examples=100, deadline=5000)
    @given(
        mixed_whitespace=st.lists(
            st.sampled_from([' ', '\t', '\n', '\r']),
            min_size=1,
            max_size=30
        )
    )
    def test_property_4_mixed_whitespace_rejected(self, mixed_whitespace):
        """
        Feature: unified-search-api, Property 4: Empty Query Rejection
        
        For any combination of different whitespace characters,
        the parser should reject it as empty.
        
        Validates: Requirements 1.4
        """
        parser = QueryParser()
        
        # Create query with mixed whitespace
        query_text = ''.join(mixed_whitespace)
        
        # Property: Mixed whitespace queries should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            parser.parse(query_text)
        
        error_message = str(exc_info.value).lower()
        assert 'empty' in error_message or 'whitespace' in error_message
