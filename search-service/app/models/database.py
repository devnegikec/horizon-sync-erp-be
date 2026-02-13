"""Database models for search functionality"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Computed,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PG_UUID
from sqlalchemy.types import JSON, TypeDecorator
from sqlalchemy.sql import func

from app.database import Base


# Create a UUID type that works with both PostgreSQL and SQLite
class UUID(TypeDecorator):
    """Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value


class SearchDocument(Base):
    """
    Search documents table with full-text search support.
    
    This table stores searchable content for all entity types with
    PostgreSQL full-text search capabilities using tsvector columns
    and GIN indexes for optimal performance.
    
    Attributes:
        id: Unique identifier for the search document
        entity_id: ID of the entity in its source table
        entity_type: Type of entity (items, customers, suppliers, etc.)
        title: Primary title/name of the entity
        content: Full searchable content
        metadata: Additional entity-specific data stored as JSONB
        search_vector: Generated tsvector column for full-text search (PostgreSQL only)
        created_at: Timestamp when the document was created
        updated_at: Timestamp when the document was last updated
    """

    __tablename__ = "search_documents"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    # Use JSON for SQLite, JSONB for PostgreSQL
    metadata_ = Column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True)
    
    # Full-text search vector - will be generated in migration (PostgreSQL only)
    # This is a generated column that combines title, content, and metadata tags
    # with different weights (A=highest, B=medium, C=lower)
    # For SQLite, this will just be a nullable text column
    # Mark as Computed so SQLAlchemy doesn't try to insert into it
    search_vector = Column(
        Text().with_variant(TSVECTOR, "postgresql"), 
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(content, '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(metadata->>'tags', '')), 'C')",
            persisted=True
        ),
        nullable=True
    )
    
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Unique constraint on entity_id and entity_type combination
    __table_args__ = (
        UniqueConstraint("entity_id", "entity_type", name="uq_entity_id_type"),
        # GIN index for full-text search on search_vector
        Index("idx_search_documents_vector", "search_vector", postgresql_using="gin"),
        # Index on entity_type for filtering
        Index("idx_search_documents_entity_type", "entity_type"),
        # Index on updated_at for synchronization queries
        Index("idx_search_documents_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<SearchDocument(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id})>"


class SearchConfiguration(Base):
    """
    Entity-specific search configurations.
    
    This table stores configuration for how each entity type should be
    searched, including which fields are searchable, boost factors for
    relevance scoring, and available filters.
    
    Attributes:
        entity_type: Type of entity (primary key)
        searchable_fields: JSONB array of field names that are searchable
        boost_factors: JSONB object mapping fields to boost multipliers
        filters: JSONB object defining available filter options
        created_at: Timestamp when the configuration was created
    """

    __tablename__ = "search_configurations"

    entity_type = Column(String, primary_key=True)
    searchable_fields = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    boost_factors = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    filters = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<SearchConfiguration(entity_type={self.entity_type})>"
