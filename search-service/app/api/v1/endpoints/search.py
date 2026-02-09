"""Search API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.search import SearchQuery, SearchResponse
from app.models.user import UserContext
from app.schemas.search import (
    SearchRequestSchema,
    SearchResponseSchema,
    SearchResultSchema,
)
from app.search_engine import PostgreSQLSearchEngine

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "/global",
    response_model=SearchResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Global search across all entity types",
    description=(
        "Perform a global search across all entity types. "
        "Returns results from items, customers, suppliers, warehouses, and stock entries. "
        "Requires 'search.global' permission."
    ),
)
async def global_search(
    request: SearchRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.global")),
) -> SearchResponseSchema:
    """
    Perform a global search across all entity types.
    
    Args:
        request: Search request parameters
        db: Database session
        current_user: Current authenticated user with search.global permission
        
    Returns:
        SearchResponseSchema with results and metadata
        
    Raises:
        HTTPException: If query is invalid or search fails
    """
    try:
        # Create search engine
        search_engine = PostgreSQLSearchEngine(db)
        
        # Build search query
        search_query = SearchQuery(
            query_text=request.query,
            entity_types=request.entity_types,
            filters=request.filters,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
        )
        
        # Execute search
        response: SearchResponse = await search_engine.global_search(
            query=search_query,
            user_context=current_user
        )
        
        # Convert to response schema
        return SearchResponseSchema(
            results=[
                SearchResultSchema(
                    entity_id=result.entity_id,
                    entity_type=result.entity_type,
                    title=result.title,
                    snippet=result.snippet,
                    relevance_score=result.relevance_score,
                    metadata=result.metadata,
                )
                for result in response.results
            ],
            total_count=response.total_count,
            page=response.page,
            page_size=response.page_size,
            total_pages=response.total_pages,
            has_next_page=response.has_next_page,
            has_previous_page=response.has_previous_page,
            query_time_ms=response.query_time_ms,
            suggestions=response.suggestions,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "INVALID_QUERY"}
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Search failed", "code": "SEARCH_ERROR"}
        ) from e


@router.post(
    "/{entity_type}",
    response_model=SearchResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Local search within a specific entity type",
    description=(
        "Perform a local search within a specific entity type. "
        "Supports field-specific filters and entity-type validation. "
        "Requires 'search.local' permission."
    ),
)
async def local_search(
    entity_type: str,
    request: SearchRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.local")),
) -> SearchResponseSchema:
    """
    Perform a local search within a specific entity type.
    
    Args:
        entity_type: Type of entity to search (items, customers, suppliers, etc.)
        request: Search request parameters
        db: Database session
        current_user: Current authenticated user with search.local permission
        
    Returns:
        SearchResponseSchema with results and metadata
        
    Raises:
        HTTPException: If entity_type is invalid, query is invalid, or search fails
    """
    try:
        # Create search engine
        search_engine = PostgreSQLSearchEngine(db)
        
        # Build search query
        search_query = SearchQuery(
            query_text=request.query,
            entity_types=request.entity_types,
            filters=request.filters,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
        )
        
        # Execute search
        response: SearchResponse = await search_engine.local_search(
            entity_type=entity_type,
            query=search_query,
            user_context=current_user
        )
        
        # Convert to response schema
        return SearchResponseSchema(
            results=[
                SearchResultSchema(
                    entity_id=result.entity_id,
                    entity_type=result.entity_type,
                    title=result.title,
                    snippet=result.snippet,
                    relevance_score=result.relevance_score,
                    metadata=result.metadata,
                )
                for result in response.results
            ],
            total_count=response.total_count,
            page=response.page,
            page_size=response.page_size,
            total_pages=response.total_pages,
            has_next_page=response.has_next_page,
            has_previous_page=response.has_previous_page,
            query_time_ms=response.query_time_ms,
            suggestions=response.suggestions,
        )
        
    except ValueError as e:
        # Handle invalid entity type or query
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "INVALID_REQUEST"}
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Search failed", "code": "SEARCH_ERROR"}
        ) from e
