"""Account audit log model for tracking account changes"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, String, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AuditAction(str, Enum):
    """Audit action types"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STATUS_CHANGE = "STATUS_CHANGE"


class AccountAuditLog(Base):
    """Account audit log model for compliance tracking"""

    __tablename__ = "account_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    action = Column(String(20), nullable=False)
    user_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True
    )
    changes = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    audit_metadata = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationship (no backref to avoid cascade issues on account deletion)
    account = relationship("Account")

    def __repr__(self):
        return f"<AccountAuditLog(id={self.id}, account_id={self.account_id}, action='{self.action}', timestamp='{self.timestamp}')>"
