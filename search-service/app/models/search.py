"""Core search data models"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SearchQuery:
    """
    Search query parameters.

    Attributes:
        query_text: The search text to query
        entity_types: Optional list of entity types to search (None = all types)
        filters: Optional dictionary of field-specific filters
        page: Page number for pagination (1-indexed)
        page_size: Number of results per page
        sort_by: Optional field name to sort results by
    """

    query_text: str
    entity_types: Optional[list[str]] = None
    filters: Optional[dict[str, Any]] = None
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None

    def __post_init__(self):
        """Validate query parameters"""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")


@dataclass
class SearchResult:
    """
    Individual search result.

    Attributes:
        entity_id: Unique identifier of the entity
        entity_type: Type of entity (items, customers, suppliers, etc.)
        title: Display title for the result
        snippet: Text snippet with highlighted matches
        relevance_score: Relevance score for ranking (higher = more relevant)
        metadata: Additional entity-specific metadata
    """

    entity_id: str
    entity_type: str
    title: str
    snippet: str
    relevance_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """
    Search response containing results and metadata.

    Attributes:
        results: List of search results
        total_count: Total number of matching results (across all pages)
        page: Current page number
        page_size: Number of results per page
        query_time_ms: Query execution time in milliseconds
        suggestions: Optional list of suggested search terms
    """

    results: list[SearchResult]
    total_count: int
    page: int
    page_size: int
    query_time_ms: int
    suggestions: Optional[list[str]] = None

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    @property
    def has_next_page(self) -> bool:
        """Check if there are more pages"""
        return self.page < self.total_pages

    @property
    def has_previous_page(self) -> bool:
        """Check if there are previous pages"""
        return self.page > 1
