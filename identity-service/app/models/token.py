"""Token related database models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class RefreshToken(Base):
    """Refresh token model for managing user sessions"""

    __tablename__ = "refresh_tokens"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    token_family = Column(String(255), index=True)

    # Device information
    device_id = Column(String(255))
    device_name = Column(String(255))
    device_type = Column(String(50))
    os_info = Column(String(100))
    browser_info = Column(String(100))

    # Request information
    ip_address = Column(String(45))
    user_agent = Column(Text)

    # Token lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True))
    revoked_reason = Column(String(100))
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_used_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
