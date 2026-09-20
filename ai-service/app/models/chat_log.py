"""ChatLog model for SOP Copilot audit trail.

Every question + retrieved chunks + generated answer is logged for compliance review.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ChatLog(Base):
    """Audit log of copilot interactions."""

    __tablename__ = "chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Context
    user_id = Column(UUID(as_uuid=True), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(64), nullable=True)  # browser session / thread

    # Question
    question = Column(Text, nullable=False)

    # Retrieval
    retrieved_chunks = Column(JSONB, default=list)  # list of {chunk_id, source, score, content_preview}
    retrieval_time_ms = Column(Float, nullable=True)

    # Generation
    answer = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    generation_time_ms = Column(Float, nullable=True)

    # Citations extracted from answer
    citations = Column(JSONB, default=list)  # list of {source_id, section}

    # Guardrail flags
    blocked = Column(String(50), nullable=True)  # reason if blocked, else null

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
