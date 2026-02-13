"""
Query parser for search functionality.

Handles text normalization, phrase extraction, and boolean operator parsing.
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Set, Optional


@dataclass
class ParsedQuery:
    """Represents a parsed search query."""
    original: str
    normalized: str
    ts_query: str
    phrases: List[str]
    terms: List[str]
    operators: List[str]


class QueryParser:
    """
    Parses and normalizes search queries for full-text search.
    
    Supports:
    - Case-insensitive and accent-insensitive normalization
    - Quoted phrase extraction
    - Boolean operators (AND, OR, NOT)
    """
    
    # Boolean operators supported
    BOOLEAN_OPERATORS = {'AND', 'OR', 'NOT'}
    
    # Common stop words (minimal set for now)
    STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 
        'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 
        'that', 'the', 'to', 'was', 'will', 'with'
    }
    
    def __init__(self):
        """Initialize the query parser."""
        pass
    
    def parse(self, query_text: str) -> ParsedQuery:
        """
        Parse and normalize a search query.
        
        Args:
            query_text: Raw search query string
            
        Returns:
            ParsedQuery object with normalized components
            
        Raises:
            ValueError: If query is empty or contains only whitespace
        """
        # Validate query
        if not query_text or not query_text.strip():
            raise ValueError("Query cannot be empty or contain only whitespace")
        
        # Normalize the query text
        normalized = self._normalize_text(query_text)
        
        # Extract quoted phrases
        phrases = self._extract_phrases(query_text)
        
        # Parse boolean operators and terms
        terms, operators = self._parse_boolean_operators(normalized, phrases)
        
        # Build PostgreSQL tsquery
        ts_query = self._build_tsquery(phrases, terms, operators)
        
        return ParsedQuery(
            original=query_text,
            normalized=normalized,
            ts_query=ts_query,
            phrases=phrases,
            terms=terms,
            operators=operators
        )
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent matching.
        
        - Converts to lowercase
        - Removes accents/diacritics
        - Normalizes whitespace
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text string
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove accents using Unicode normalization
        # NFD = Canonical Decomposition
        text = unicodedata.normalize('NFD', text)
        # Filter out combining characters (accents)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        
        # Normalize whitespace (collapse multiple spaces)
        text = ' '.join(text.split())
        
        return text
    
    def _extract_phrases(self, text: str) -> List[str]:
        """
        Extract quoted phrases from query text.
        
        Args:
            text: Query text potentially containing quoted phrases
            
        Returns:
            List of extracted phrases (without quotes)
        """
        # Match text within double quotes
        phrase_pattern = r'"([^"]+)"'
        phrases = re.findall(phrase_pattern, text)
        
        # Normalize each phrase
        return [self._normalize_text(phrase) for phrase in phrases]
    
    def _parse_boolean_operators(
        self, 
        normalized_text: str, 
        phrases: List[str]
    ) -> tuple[List[str], List[str]]:
        """
        Parse boolean operators and extract search terms.
        
        Args:
            normalized_text: Normalized query text
            phrases: Already extracted phrases to exclude from term parsing
            
        Returns:
            Tuple of (terms, operators) lists
        """
        # Remove quoted phrases from text to avoid double-processing
        text_without_phrases = normalized_text
        for phrase in phrases:
            text_without_phrases = text_without_phrases.replace(f'"{phrase}"', '')
        
        # Split into tokens
        tokens = text_without_phrases.split()
        
        terms = []
        operators = []
        
        for token in tokens:
            token_upper = token.upper()
            if token_upper in self.BOOLEAN_OPERATORS:
                operators.append(token_upper)
            elif token and token not in self.STOP_WORDS:
                # Only add non-empty, non-stop-word terms
                terms.append(token)
        
        return terms, operators
    
    def _build_tsquery(
        self, 
        phrases: List[str], 
        terms: List[str], 
        operators: List[str]
    ) -> str:
        """
        Build PostgreSQL tsquery string from parsed components.
        
        Args:
            phrases: Extracted quoted phrases
            terms: Individual search terms
            operators: Boolean operators
            
        Returns:
            PostgreSQL tsquery-compatible string
        """
        query_parts = []
        
        # Add phrases (use <-> for phrase matching)
        for phrase in phrases:
            # Split phrase into words and join with <-> for adjacent word matching
            phrase_words = phrase.split()
            if phrase_words:
                phrase_query = ' <-> '.join(phrase_words)
                query_parts.append(f'({phrase_query})')
        
        # Add individual terms
        for term in terms:
            # Add prefix matching support with :*
            query_parts.append(f'{term}:*')
        
        # If no operators specified, default to AND behavior
        if not operators:
            return ' & '.join(query_parts) if query_parts else ''
        
        # Build query with operators
        # This is a simplified implementation
        # For complex boolean logic, a more sophisticated parser would be needed
        result_parts = []
        operator_map = {'AND': '&', 'OR': '|', 'NOT': '!'}
        
        for i, part in enumerate(query_parts):
            result_parts.append(part)
            if i < len(operators):
                op = operator_map.get(operators[i], '&')
                result_parts.append(op)
        
        return ' '.join(result_parts)
    
    def sanitize_input(self, text: str) -> str:
        """
        Sanitize input to prevent injection attacks.
        
        Args:
            text: Raw input text
            
        Returns:
            Sanitized text safe for database queries
        """
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove SQL comment sequences
        text = text.replace('--', '')
        text = text.replace('/*', '')
        text = text.replace('*/', '')
        
        # Remove potentially dangerous characters
        # Keep alphanumeric, spaces, quotes, and basic punctuation
        safe_pattern = r'[^a-zA-Z0-9\s\'".,!?-]'
        sanitized = re.sub(safe_pattern, '', text)
        
        # Limit length to prevent DoS
        max_length = 500
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
