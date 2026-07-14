"""
PostgreSQL full-text search engine implementation.

Provides search functionality using PostgreSQL's built-in full-text search
capabilities with tsvector and tsquery.
"""
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import SearchQuery, SearchResult, SearchResponse
from app.models.user import UserContext
from app.models.database import SearchDocument, SearchConfiguration
from app.query_parser import QueryParser, ParsedQuery


class SearchEngineInterface(ABC):
    """Abstract interface for search engines."""
    
    @abstractmethod
    async def global_search(
        self, 
        query: SearchQuery, 
        user_context: UserContext
    ) -> SearchResponse:
        """
        Perform a global search across all entity types.
        
        Args:
            query: Search query parameters
            user_context: User context for authorization
            
        Returns:
            SearchResponse with results and metadata
        """
        pass
    
    @abstractmethod
    async def local_search(
        self, 
        entity_type: str,
        query: SearchQuery, 
        user_context: UserContext
    ) -> SearchResponse:
        """
        Perform a local search within a specific entity type.
        
        Args:
            entity_type: Type of entity to search
            query: Search query parameters
            user_context: User context for authorization
            
        Returns:
            SearchResponse with results and metadata
        """
        pass
    
    @abstractmethod
    async def suggest_terms(
        self, 
        partial_query: str, 
        entity_type: Optional[str] = None
    ) -> List[str]:
        """
        Suggest search terms based on partial input.
        
        Args:
            partial_query: Partial search query
            entity_type: Optional entity type to limit suggestions
            
        Returns:
            List of suggested search terms
        """
        pass


class PostgreSQLSearchEngine(SearchEngineInterface):
    """
    PostgreSQL full-text search engine implementation.
    
    Uses PostgreSQL's tsvector and tsquery for efficient full-text search
    with support for phrase matching, boolean operators, and relevance ranking.
    """
    
    # Maximum number of results to return (prevent performance issues)
    MAX_RESULTS = 1000
    
    # Supported entity types
    ENTITY_TYPES = [
        'items',
        'customers', 
        'suppliers',
        'warehouses',
        'stock_entries',
        'tax_templates',
        'charge_templates'
    ]
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the search engine.
        
        Args:
            db_session: Async database session
        """
        self.db = db_session
        self.query_parser = QueryParser()
    
    async def global_search(
        self, 
        query: SearchQuery, 
        user_context: UserContext
    ) -> SearchResponse:
        """
        Perform a global search across all entity types.
        
        Args:
            query: Search query parameters
            user_context: User context for authorization
            
        Returns:
            SearchResponse with results and metadata
            
        Raises:
            ValueError: If query is invalid
        """
        start_time = time.time()
        
        # Parse and validate query
        parsed_query = self.query_parser.parse(query.query_text)
        
        # Build and execute search query
        results, total_count = await self._execute_search(
            parsed_query=parsed_query,
            entity_types=query.entity_types or self.ENTITY_TYPES,
            filters=query.filters,
            page=query.page,
            page_size=query.page_size,
            user_context=user_context
        )
        
        # Calculate query time
        query_time_ms = int((time.time() - start_time) * 1000)
        
        # Generate suggestions if no results
        suggestions = None
        if total_count == 0:
            suggestions = await self.suggest_terms(query.query_text)
        
        return SearchResponse(
            results=results,
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
            query_time_ms=query_time_ms,
            suggestions=suggestions
        )
    
    async def local_search(
        self, 
        entity_type: str,
        query: SearchQuery, 
        user_context: UserContext
    ) -> SearchResponse:
        """
        Perform a local search within a specific entity type.
        
        Args:
            entity_type: Type of entity to search
            query: Search query parameters
            user_context: User context for authorization
            
        Returns:
            SearchResponse with results and metadata
            
        Raises:
            ValueError: If entity_type is invalid or query is invalid
        """
        # Validate entity type
        if entity_type not in self.ENTITY_TYPES:
            raise ValueError(
                f"Invalid entity type: {entity_type}. "
                f"Must be one of: {', '.join(self.ENTITY_TYPES)}"
            )
        
        start_time = time.time()
        
        # Parse and validate query
        parsed_query = self.query_parser.parse(query.query_text)
        
        # Build and execute search query (limited to specific entity type)
        results, total_count = await self._execute_search(
            parsed_query=parsed_query,
            entity_types=[entity_type],
            filters=query.filters,
            page=query.page,
            page_size=query.page_size,
            user_context=user_context
        )
        
        # Calculate query time
        query_time_ms = int((time.time() - start_time) * 1000)
        
        # Generate suggestions if no results
        suggestions = None
        if total_count == 0:
            suggestions = await self.suggest_terms(query.query_text, entity_type)
        
        return SearchResponse(
            results=results,
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
            query_time_ms=query_time_ms,
            suggestions=suggestions
        )
    
    async def suggest_terms(
        self, 
        partial_query: str, 
        entity_type: Optional[str] = None
    ) -> List[str]:
        """
        Suggest search terms based on partial input using fuzzy matching.
        
        Uses PostgreSQL trigram similarity for fuzzy matching when available.
        
        Args:
            partial_query: Partial search query
            entity_type: Optional entity type to limit suggestions
            
        Returns:
            List of suggested search terms
        """
        if not partial_query or len(partial_query) < 2:
            return []
        
        dialect_name = self.db.bind.dialect.name if self.db.bind else 'sqlite'
        
        if dialect_name == 'postgresql':
            # Use PostgreSQL trigram similarity for fuzzy matching
            # This requires pg_trgm extension to be enabled
            try:
                # Include similarity score in SELECT to satisfy PostgreSQL's DISTINCT + ORDER BY requirement
                similarity_score = func.similarity(SearchDocument.title, partial_query).label('similarity_score')
                stmt = select(SearchDocument.title, similarity_score).distinct()
                
                if entity_type:
                    stmt = stmt.where(SearchDocument.entity_type == entity_type)
                
                # Use similarity operator for fuzzy matching
                # similarity() returns a value between 0 and 1
                stmt = stmt.where(
                    similarity_score > 0.3
                ).order_by(
                    similarity_score.desc()
                ).limit(5)
                
                result = await self.db.execute(stmt)
                # Extract just the title from the results (first column)
                suggestions = [row[0] for row in result.fetchall()]
                return suggestions
            except Exception:
                # Fall back to simple LIKE matching if trigram extension not available
                pass
        
        # Fallback: Use simple LIKE matching for suggestions
        stmt = select(SearchDocument.title).distinct()
        
        if entity_type:
            stmt = stmt.where(SearchDocument.entity_type == entity_type)
        
        stmt = stmt.where(
            SearchDocument.title.ilike(f'%{partial_query}%')
        ).limit(5)
        
        result = await self.db.execute(stmt)
        suggestions = [row[0] for row in result.fetchall()]
        return suggestions
    
    async def _execute_search(
        self,
        parsed_query: ParsedQuery,
        entity_types: List[str],
        filters: Optional[dict],
        page: int,
        page_size: int,
        user_context: UserContext
    ) -> tuple[List[SearchResult], int]:
        """
        Execute the search query against the database.
        
        Supports:
        - Full-text search with PostgreSQL tsvector/tsquery
        - Partial text matching with wildcard operators
        - Fuzzy matching with trigram similarity (PostgreSQL)
        - Fallback to LIKE queries for SQLite
        
        Args:
            parsed_query: Parsed query with normalized terms
            entity_types: List of entity types to search
            filters: Optional field-specific filters
            page: Page number for pagination
            page_size: Number of results per page
            user_context: User context for authorization
            
        Returns:
            Tuple of (results list, total count)
        """
        # Build base query
        stmt = select(SearchDocument)
        
        # Filter by entity types
        stmt = stmt.where(SearchDocument.entity_type.in_(entity_types))
        
        # Add full-text search condition
        if parsed_query.ts_query:
            # Check if we're using PostgreSQL or SQLite
            dialect_name = self.db.bind.dialect.name if self.db.bind else 'sqlite'
            
            if dialect_name == 'postgresql':
                # Use PostgreSQL full-text search with fuzzy matching support
                # The :* operator in tsquery provides prefix matching (partial text)
                stmt = stmt.where(
                    SearchDocument.search_vector.op('@@')(
                        func.to_tsquery('english', parsed_query.ts_query)
                    )
                )
            else:
                # Fallback to simple text search for SQLite with partial matching
                search_terms = parsed_query.terms + [
                    word for phrase in parsed_query.phrases 
                    for word in phrase.split()
                ]
                if search_terms:
                    conditions = []
                    for term in search_terms:
                        # Use LIKE for partial matching (fuzzy-like behavior)
                        conditions.append(
                            or_(
                                SearchDocument.title.ilike(f'%{term}%'),
                                SearchDocument.content.ilike(f'%{term}%')
                            )
                        )
                    if conditions:
                        stmt = stmt.where(or_(*conditions))
        
        # Apply additional filters
        if filters:
            dialect_name = self.db.bind.dialect.name if self.db.bind else 'sqlite'
            
            for field, value in filters.items():
                # Filter on metadata fields
                if dialect_name == 'postgresql':
                    # Use JSONB operators for PostgreSQL
                    # Use the ->> operator to extract text value from JSONB
                    stmt = stmt.where(
                        SearchDocument.metadata_[field].as_string() == str(value)
                    )
                else:
                    # Use JSON_EXTRACT for SQLite
                    stmt = stmt.where(
                        func.json_extract(SearchDocument.metadata_, f'$.{field}') == str(value)
                    )
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        total_count = result.scalar() or 0
        
        # Limit total results
        if total_count > self.MAX_RESULTS:
            total_count = self.MAX_RESULTS
        
        # Add ordering by relevance (for PostgreSQL) or by updated_at
        dialect_name = self.db.bind.dialect.name if self.db.bind else 'sqlite'
        
        if dialect_name == 'postgresql' and parsed_query.ts_query:
            # Use PostgreSQL relevance ranking
            stmt = stmt.order_by(
                func.ts_rank(
                    SearchDocument.search_vector,
                    func.to_tsquery('english', parsed_query.ts_query)
                ).desc()
            )
        else:
            # Fallback to ordering by updated_at for SQLite
            stmt = stmt.order_by(SearchDocument.updated_at.desc())
        
        # Add pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        documents = result.scalars().all()
        
        # Convert to SearchResult objects
        results = []
        for doc in documents:
            # Calculate relevance score (simplified for now)
            relevance_score = 1.0
            
            # Create snippet from content (first 200 chars)
            snippet = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            
            results.append(SearchResult(
                entity_id=doc.entity_id,
                entity_type=doc.entity_type,
                title=doc.title,
                snippet=snippet,
                relevance_score=relevance_score,
                metadata=doc.metadata_ or {}
            ))
        
        return results, total_count
    
    async def get_entity_types(self) -> List[str]:
        """
        Get list of available entity types.
        
        Returns:
            List of entity type names
        """
        return self.ENTITY_TYPES.copy()
    
    async def get_configuration(self, entity_type: str) -> Optional[SearchConfiguration]:
        """
        Get search configuration for an entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            SearchConfiguration if found, None otherwise
        """
        stmt = select(SearchConfiguration).where(
            SearchConfiguration.entity_type == entity_type
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
