"""VectorChunk model for pgvector RAG storage.

Each chunk is a segment of a document (SOP, playbook, etc.) with its embedding
vector stored as a pgvector column for similarity search.
"""

import enum
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.config import settings
from app.database import Base


class ChunkSource(str, enum.Enum):
    """Origin of a knowledge chunk."""
    SOP = "sop"
    PLAYBOOK = "playbook"
    PUT_AWAY_RULE = "put_away_rule"
    LOCATION_HIERARCHY = "location_hierarchy"
    ITEM_MASTER = "item_master"


class VectorChunk(Base):
    """A chunk of knowledge with its embedding vector for RAG retrieval."""

    __tablename__ = "vector_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source document metadata
    source_type = Column(Enum(ChunkSource), nullable=False)
    source_id = Column(String(255), nullable=True)  # e.g. filename, rule ID
    source_title = Column(String(500), nullable=True)
    section = Column(String(255), nullable=True)  # heading / subsection
    chunk_index = Column(Integer, nullable=False, default=0)

    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)  # sha256 for dedup

    # Vector embedding (dimensions from config)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=False)

    # RBAC scope (nullable = global / all orgs)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Full-text search vector (for hybrid search fallback)
    # populated by trigger or application layer
