"""Account model definition for Chart of Accounts"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
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
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )

    # Hierarchy
    parent_account_id = Column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True, index=True
    )
    level = Column(Integer, nullable=False, default=1)
    is_group = Column(Boolean, nullable=False, default=False)

    # Currency and Status
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(
        Enum(
            AccountStatus,
            name="accountstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
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
    balances = relationship("AccountBalance", back_populates="account", cascade="all, delete-orphan")
    bank_accounts = relationship("BankAccount", back_populates="gl_account", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('organization_id', 'account_code', name='unique_account_code_per_org'),
    )

    def __repr__(self):
        return f"<Account(id={self.id}, code='{self.account_code}', name='{self.account_name}', type='{self.account_type}')>"

    @property
    def has_bank_accounts(self) -> bool:
        """Check if this account has any linked bank accounts"""
        return len(self.bank_accounts) > 0

    @property
    def active_bank_accounts(self):
        """Get only active bank accounts"""
        return [ba for ba in self.bank_accounts if ba.is_active]

    @property
    def primary_bank_account(self):
        """Get the primary bank account for this GL account"""
        for bank_account in self.active_bank_accounts:
            if bank_account.is_primary:
                return bank_account
        return None

    @property
    def bank_accounts_count(self) -> int:
        """Get count of active bank accounts"""
        return len(self.active_bank_accounts)

    def get_banking_summary(self) -> dict:
        """Get a summary of banking information for this account"""
        primary_bank = self.primary_bank_account
        return {
            "is_bank_enabled": self.has_bank_accounts,
            "bank_accounts_count": self.bank_accounts_count,
            "primary_bank_name": primary_bank.bank_name if primary_bank else None,
            "primary_bank_masked_account": primary_bank.mask_account_number() if primary_bank else None
        }
