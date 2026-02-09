"""
Unit tests for QueryParser.

Tests specific examples and edge cases for query parsing functionality.
"""
import pytest
from app.query_parser import QueryParser, ParsedQuery


class TestQueryParser:
    """Test suite for QueryParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create a QueryParser instance for testing."""
        return QueryParser()
    
    def test_parse_simple_query(self, parser):
        """Test parsing a simple single-term query."""
        result = parser.parse("laptop")
        
        assert result.original == "laptop"
        assert result.normalized == "laptop"
        assert "laptop" in result.terms
        assert len(result.phrases) == 0
    
    def test_parse_multi_term_query(self, parser):
        """Test parsing a query with multiple terms."""
        result = parser.parse("laptop computer")
        
        assert result.original == "laptop computer"
        assert result.normalized == "laptop computer"
        assert "laptop" in result.terms
        assert "computer" in result.terms
    
    def test_parse_quoted_phrase(self, parser):
        """Test parsing a query with quoted phrases."""
        result = parser.parse('"gaming laptop"')
        
        assert len(result.phrases) == 1
        assert "gaming laptop" in result.phrases
    
    def test_parse_mixed_phrase_and_terms(self, parser):
        """Test parsing a query with both phrases and individual terms."""
        result = parser.parse('"gaming laptop" 16GB RAM')
        
        assert "gaming laptop" in result.phrases
        assert "16gb" in result.terms
        assert "ram" in result.terms
    
    def test_normalize_case_insensitive(self, parser):
        """Test case-insensitive normalization."""
        result = parser.parse("LAPTOP Laptop laptop")
        
        assert result.normalized == "laptop laptop laptop"
    
    def test_normalize_accent_removal(self, parser):
        """Test accent/diacritic removal."""
        result = parser.parse("café naïve résumé")
        
        assert result.normalized == "cafe naive resume"
    
    def test_normalize_whitespace(self, parser):
        """Test whitespace normalization."""
        result = parser.parse("laptop    computer   ")
        
        assert result.normalized == "laptop computer"
    
    def test_parse_boolean_and_operator(self, parser):
        """Test parsing AND boolean operator."""
        result = parser.parse("laptop AND computer")
        
        assert "AND" in result.operators
        assert "laptop" in result.terms
        assert "computer" in result.terms
    
    def test_parse_boolean_or_operator(self, parser):
        """Test parsing OR boolean operator."""
        result = parser.parse("laptop OR tablet")
        
        assert "OR" in result.operators
        assert "laptop" in result.terms
        assert "tablet" in result.terms
    
    def test_parse_boolean_not_operator(self, parser):
        """Test parsing NOT boolean operator."""
        result = parser.parse("laptop NOT refurbished")
        
        assert "NOT" in result.operators
        assert "laptop" in result.terms
        assert "refurbished" in result.terms
    
    def test_parse_mixed_boolean_operators(self, parser):
        """Test parsing multiple boolean operators."""
        result = parser.parse("laptop AND computer OR tablet")
        
        assert "AND" in result.operators
        assert "OR" in result.operators
    
    def test_stop_words_filtered(self, parser):
        """Test that stop words are filtered out."""
        result = parser.parse("the laptop and the computer")
        
        # 'the' and 'and' should be filtered as stop words
        assert "the" not in result.terms
        assert "and" not in result.terms
        assert "laptop" in result.terms
        assert "computer" in result.terms
    
    def test_empty_query_raises_error(self, parser):
        """Test that empty queries raise ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            parser.parse("")
    
    def test_whitespace_only_query_raises_error(self, parser):
        """Test that whitespace-only queries raise ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            parser.parse("   ")
    
    def test_sanitize_input_removes_dangerous_chars(self, parser):
        """Test input sanitization removes potentially dangerous characters."""
        dangerous_input = "laptop; DROP TABLE users;--"
        sanitized = parser.sanitize_input(dangerous_input)
        
        assert ";" not in sanitized
        assert "DROP" in sanitized  # Letters are kept
        assert "TABLE" in sanitized
    
    def test_sanitize_input_limits_length(self, parser):
        """Test input sanitization limits query length."""
        long_input = "a" * 1000
        sanitized = parser.sanitize_input(long_input)
        
        assert len(sanitized) <= 500
    
    def test_build_tsquery_simple_term(self, parser):
        """Test tsquery generation for simple term."""
        result = parser.parse("laptop")
        
        # Should include prefix matching with :*
        assert "laptop:*" in result.ts_query
    
    def test_build_tsquery_phrase(self, parser):
        """Test tsquery generation for quoted phrase."""
        result = parser.parse('"gaming laptop"')
        
        # Phrases should use <-> for adjacent word matching
        assert "<->" in result.ts_query
        assert "gaming" in result.ts_query
        assert "laptop" in result.ts_query
    
    def test_build_tsquery_multiple_terms(self, parser):
        """Test tsquery generation for multiple terms."""
        result = parser.parse("laptop computer")
        
        # Multiple terms should be joined with & (AND)
        assert "&" in result.ts_query
        assert "laptop:*" in result.ts_query
        assert "computer:*" in result.ts_query
    
    def test_special_characters_handled_safely(self, parser):
        """Test that special characters don't cause errors."""
        # Should not raise exceptions
        result = parser.parse("laptop@#$%computer")
        assert result is not None
    
    def test_unicode_characters_handled(self, parser):
        """Test that Unicode characters are handled properly."""
        result = parser.parse("laptop 日本語 компьютер")
        assert result is not None
        assert result.normalized is not None
    
    def test_extract_multiple_phrases(self, parser):
        """Test extraction of multiple quoted phrases."""
        result = parser.parse('"gaming laptop" and "high performance"')
        
        assert len(result.phrases) == 2
        assert "gaming laptop" in result.phrases
        assert "high performance" in result.phrases
    
    def test_empty_quotes_handled(self, parser):
        """Test that empty quotes don't cause issues."""
        result = parser.parse('laptop "" computer')
        
        # Empty phrases should be filtered or handled gracefully
        assert result is not None
    
    def test_nested_quotes_handled(self, parser):
        """Test handling of nested or malformed quotes."""
        # Should handle gracefully without crashing
        result = parser.parse('laptop "gaming "high" performance" computer')
        assert result is not None
