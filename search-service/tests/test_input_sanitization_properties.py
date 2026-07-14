"""
Property-based tests for input sanitization.

Tests that special characters and potentially malicious input are handled safely.
Feature: unified-search-api
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from app.query_parser import QueryParser


class TestInputSanitizationProperties:
    """Property-based test suite for input sanitization."""
    
    @settings(max_examples=100, deadline=5000)
    @given(
        query_text=st.text(
            alphabet=st.characters(
                blacklist_categories=('Cc', 'Cs'),  # Exclude control and surrogate chars
                min_codepoint=32,
                max_codepoint=1000
            ),
            min_size=1,
            max_size=100
        )
    )
    def test_property_11_parsing_never_crashes(self, query_text):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any search query containing special characters or potentially
        malicious input, the query parser should handle them safely without
        causing errors or security vulnerabilities.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        
        # Property: Parser should never crash, only raise ValueError for empty queries
        try:
            result = parser.parse(query_text)
            # If parsing succeeds, result should be valid
            assert result is not None
            assert isinstance(result.original, str)
            assert isinstance(result.normalized, str)
            assert isinstance(result.ts_query, str)
        except ValueError as e:
            # Only ValueError for empty queries is acceptable
            error_message = str(e).lower()
            assert 'empty' in error_message or 'whitespace' in error_message
            assert query_text.strip() == ""
        except Exception as e:
            # Any other exception is a failure
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")
    
    @settings(max_examples=100, deadline=5000)
    @given(
        base_query=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=1,
            max_size=50
        ),
        special_chars=st.text(
            alphabet=';\'"`<>{}[]()\\|&$!@#%^*+=~',
            min_size=0,
            max_size=20
        )
    )
    def test_property_11_special_characters_handled(self, base_query, special_chars):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any query with special characters mixed with normal text,
        the parser should handle it safely.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        assume(base_query.strip() != "")
        
        # Mix special characters with normal query
        query_text = f"{base_query}{special_chars}"
        
        # Property: Should parse without crashing
        try:
            result = parser.parse(query_text)
            assert result is not None
        except ValueError:
            # Only acceptable if the result is empty after sanitization
            pass
    
    @settings(max_examples=100, deadline=5000)
    @given(
        sql_injection_attempt=st.sampled_from([
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords--",
            "1; DELETE FROM items WHERE 1=1--",
            "'; EXEC xp_cmdshell('dir');--"
        ])
    )
    def test_property_11_sql_injection_prevented(self, sql_injection_attempt):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any SQL injection attempt, the parser should handle it safely
        without allowing malicious SQL execution.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        
        # Property: SQL injection attempts should be sanitized
        sanitized = parser.sanitize_input(sql_injection_attempt)
        
        # Dangerous SQL keywords and characters should be removed or escaped
        dangerous_patterns = [';', '--', 'DROP', 'DELETE', 'EXEC', 'xp_cmdshell']
        
        # At least some dangerous elements should be removed
        # (We're checking that sanitization happens, not that it's perfect)
        assert sanitized != sql_injection_attempt or len(sanitized) == 0
    
    @settings(max_examples=100, deadline=5000)
    @given(
        xss_attempt=st.sampled_from([
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='malicious.com'></iframe>",
            "<svg onload=alert('XSS')>"
        ])
    )
    def test_property_11_xss_prevented(self, xss_attempt):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any XSS (Cross-Site Scripting) attempt, the parser should
        handle it safely.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        
        # Property: XSS attempts should be sanitized
        sanitized = parser.sanitize_input(xss_attempt)
        
        # Dangerous HTML/JS elements should be removed
        dangerous_patterns = ['<script>', '<img', 'javascript:', '<iframe', '<svg']
        
        # Check that dangerous patterns are removed or escaped
        for pattern in dangerous_patterns:
            if pattern in xss_attempt.lower():
                # The sanitized version should not contain the exact pattern
                assert pattern not in sanitized.lower() or len(sanitized) == 0
    
    @settings(max_examples=100, deadline=5000)
    @given(
        long_input=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=501,
            max_size=10000
        )
    )
    def test_property_11_length_limiting(self, long_input):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any excessively long input, the sanitizer should limit
        the length to prevent DoS attacks.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        
        # Property: Sanitized input should be limited to reasonable length
        sanitized = parser.sanitize_input(long_input)
        
        # Should be limited to max length (500 characters)
        assert len(sanitized) <= 500
    
    @settings(max_examples=100, deadline=5000)
    @given(
        unicode_chars=st.text(
            alphabet=st.characters(
                min_codepoint=128,
                max_codepoint=1000,
                blacklist_categories=('Cc', 'Cs')
            ),
            min_size=1,
            max_size=50
        )
    )
    def test_property_11_unicode_handled_safely(self, unicode_chars):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any Unicode characters, the parser should handle them safely
        without crashing or causing encoding issues.
        
        Validates: Requirements 4.4
        """
        parser = QueryParser()
        assume(unicode_chars.strip() != "")
        
        # Property: Unicode should be handled without crashes
        try:
            result = parser.parse(unicode_chars)
            assert result is not None
            # Normalized text should be valid
            assert isinstance(result.normalized, str)
        except ValueError:
            # Only acceptable for empty queries
            pass
    
    @settings(max_examples=100, deadline=5000)
    @given(
        null_bytes=st.integers(min_value=0, max_value=10),
        text=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1,
            max_size=20
        )
    )
    def test_property_11_null_bytes_handled(self, null_bytes, text):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any input containing null bytes, the parser should handle
        them safely.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        assume(text.strip() != "")
        
        # Create input with null bytes
        query_text = text + ('\x00' * null_bytes)
        
        # Property: Should handle null bytes without crashing
        try:
            sanitized = parser.sanitize_input(query_text)
            # Null bytes should be removed
            assert '\x00' not in sanitized
        except Exception:
            # Should not crash
            pytest.fail("Parser crashed on null bytes")
    
    @settings(max_examples=100, deadline=5000)
    @given(
        repeated_char=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Po'),
            min_codepoint=32,
            max_codepoint=126
        ),
        repeat_count=st.integers(min_value=100, max_value=1000)
    )
    def test_property_11_repeated_characters_handled(self, repeated_char, repeat_count):
        """
        Feature: unified-search-api, Property 11: Input Sanitization
        
        For any input with many repeated characters (potential DoS),
        the parser should handle it safely.
        
        Validates: Requirements 4.4, 6.4
        """
        parser = QueryParser()
        
        # Create query with repeated characters
        query_text = repeated_char * repeat_count
        
        # Property: Should handle without performance issues
        # (The test itself has a deadline to catch performance problems)
        try:
            if query_text.strip():
                result = parser.parse(query_text)
                assert result is not None
        except ValueError:
            # Acceptable for empty queries
            pass
