"""Status Transition model definition for audit logging"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class StatusTransition(Base):
    """Status Transition model for tracking document status changes"""

    __tablename__ = "status_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Entity information
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Status change
    previous_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)

    # User who made the transition
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Timestamp
    transitioned_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    def __repr__(self):
        return f"<StatusTransition(entity_type='{self.entity_type}', entity_id={self.entity_id}, {self.previous_status} -> {self.new_status})>"
