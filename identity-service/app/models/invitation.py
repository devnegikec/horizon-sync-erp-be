"""Invitation model for user invitations"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Invitation(Base):
    """Invitation model for inviting users to organizations"""

    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    team_ids = Column(JSONB, default=[])
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(20), default="pending", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    message = Column(Text, nullable=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    role = relationship("Role", foreign_keys=[role_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    accepted_user = relationship("User", foreign_keys=[accepted_user_id])

    def __repr__(self):
        return (
            f"<Invitation(id={self.id}, email='{self.email}', status='{self.status}')>"
        )
