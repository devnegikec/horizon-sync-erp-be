"""Account model definition for Chart of Accounts"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import AccountStatus, AccountType
from app.models.types import UUID


class Account(Base):
    """Account model for Chart of Accounts"""

    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(200), nullable=False)
    account_type = Column(
        Enum(
            AccountType,
            name="accounttype",
            create_type=False,
        ),
        nullable=False,
        index=True,
    )

    # Hierarchy
    parent_account_id = Column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, index=True
    )

    # Currency and Status
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(
        Enum(
            AccountStatus,
            name="accountstatus",
            create_type=False,
        ),
        nullable=False,
        default=AccountStatus.ACTIVE,
        index=True,
    )

    # Posting Configuration
    is_posting_account = Column(Boolean, nullable=False, default=True)

    # Description
    description = Column(Text, nullable=True)

    # Audit fields
    created_by = Column(String(100), nullable=False)
    updated_by = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    parent_account = relationship("Account", remote_side=[id], backref="child_accounts")

    __table_args__ = (
        UniqueConstraint('organization_id', 'account_code', name='unique_account_code_per_org'),
    )

    def __repr__(self):
        return f"<Account(id={self.id}, code='{self.account_code}', name='{self.account_name}', type='{self.account_type}')>"
