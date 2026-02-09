"""Search API request and response schemas"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class SearchRequestSchema(BaseModel):
    """
    Search request schema for API validation.
    
    Attributes:
        query: Search query text (required, 1-500 characters)
        entity_types: Optional list of entity types to search
        filters: Optional field-specific filters
        page: Page number (default: 1, min: 1)
        page_size: Results per page (default: 20, min: 1, max: 100)
        sort_by: Optional field to sort by
    """
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query text"
    )
    entity_types: Optional[list[str]] = Field(
        None,
        description="List of entity types to search (None = all types)"
    )
    filters: Optional[dict[str, Any]] = Field(
        None,
        description="Field-specific filters"
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number for pagination"
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of results per page"
    )
    sort_by: Optional[str] = Field(
        None,
        description="Field name to sort results by"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty or whitespace only"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator('entity_types')
    @classmethod
    def validate_entity_types(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate entity types if provided"""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("entity_types must be a list")
            if len(v) == 0:
                raise ValueError("entity_types cannot be empty if provided")
            # Remove duplicates
            return list(set(v))
        return v


class SearchResultSchema(BaseModel):
    """
    Individual search result schema.
    
    Attributes:
        entity_id: Unique identifier of the entity
        entity_type: Type of entity
        title: Display title
        snippet: Text snippet with matches
        relevance_score: Relevance score for ranking
        metadata: Additional entity-specific data
    """
    
    entity_id: str = Field(..., description="Unique identifier of the entity")
    entity_type: str = Field(..., description="Type of entity")
    title: str = Field(..., description="Display title for the result")
    snippet: str = Field(..., description="Text snippet with highlighted matches")
    relevance_score: float = Field(..., description="Relevance score for ranking")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entity-specific metadata"
    )


class SearchResponseSchema(BaseModel):
    """
    Search response schema.
    
    Attributes:
        results: List of search results
        total_count: Total number of matching results
        page: Current page number
        page_size: Number of results per page
        total_pages: Total number of pages
        has_next_page: Whether there are more pages
        has_previous_page: Whether there are previous pages
        query_time_ms: Query execution time in milliseconds
        suggestions: Optional list of suggested search terms
    """
    
    results: list[SearchResultSchema] = Field(
        ...,
        description="List of search results"
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of matching results"
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number"
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of results per page"
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages"
    )
    has_next_page: bool = Field(
        ...,
        description="Whether there are more pages"
    )
    has_previous_page: bool = Field(
        ...,
        description="Whether there are previous pages"
    )
    query_time_ms: int = Field(
        ...,
        ge=0,
        description="Query execution time in milliseconds"
    )
    suggestions: Optional[list[str]] = Field(
        None,
        description="Optional list of suggested search terms"
    )


class ErrorResponseSchema(BaseModel):
    """
    Error response schema.
    
    Attributes:
        message: Error message
        status_code: HTTP status code
        code: Error code identifier
        details: Optional additional error details
    """
    
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    code: str = Field(..., description="Error code identifier")
    details: Optional[dict[str, Any]] = Field(
        None,
        description="Optional additional error details"
    )
