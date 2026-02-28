"""Bank Account model for banking integration with Chart of Accounts"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID

if TYPE_CHECKING:
    from app.models.chart_of_account import Account


class BankAccount(Base):
    """Bank Account model for linking GL accounts with banking information"""

    __tablename__ = "bank_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    gl_account_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("accounts.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )

    # Banking details (sensitive fields will be encrypted at application level)
    bank_name = Column(String(100), nullable=False)
    account_holder_name = Column(String(200), nullable=False)
    account_number = Column(String(50), nullable=False)      # Will be encrypted
    iban = Column(String(34), nullable=True)                 # Will be encrypted
    swift_code = Column(String(11), nullable=True)           # Will be encrypted
    routing_number = Column(String(20), nullable=True)       # US banks, will be encrypted
    branch_name = Column(String(100), nullable=True)
    branch_code = Column(String(20), nullable=True)
    sort_code = Column(String(10), nullable=True)            # UK banks
    bsb_number = Column(String(10), nullable=True)           # Australian banks

    # Account metadata
    account_type = Column(String(50), nullable=True)         # checking, savings, business
    account_purpose = Column(String(50), nullable=True)      # operating, payroll, tax
    is_primary = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Banking features
    online_banking_enabled = Column(Boolean, default=False)
    mobile_banking_enabled = Column(Boolean, default=False)
    wire_transfer_enabled = Column(Boolean, default=False)
    ach_enabled = Column(Boolean, default=False)

    # Limits and controls
    daily_transfer_limit = Column(Numeric(15, 2), nullable=True)
    monthly_transfer_limit = Column(Numeric(15, 2), nullable=True)
    requires_dual_approval = Column(Boolean, default=False)

    # Integration settings
    bank_api_enabled = Column(Boolean, default=False)
    bank_api_credentials_id = Column(UUID(as_uuid=True), nullable=True)
    last_sync_date = Column(DateTime(timezone=True), nullable=True)
    sync_frequency = Column(String(20), default='manual')

    # Audit fields
    created_by = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(UTC)
    )
    updated_by = Column(String(100), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    gl_account = relationship("Account", back_populates="bank_accounts")
    history = relationship("BankAccountHistory", back_populates="bank_account", cascade="all, delete-orphan")

    __table_args__ = (
        # IBAN must be unique within organization
        UniqueConstraint('organization_id', 'iban', name='unique_iban_per_org'),
    )

    def __repr__(self):
        # Don't expose sensitive information in repr
        masked_account = self.mask_account_number()
        return f"<BankAccount(id={self.id}, bank='{self.bank_name}', account='***{masked_account}', gl_account_id={self.gl_account_id})>"

    def mask_account_number(self) -> str:
        """Return masked account number for display purposes"""
        if not self.account_number:
            return ""
        if len(self.account_number) <= 4:
            return "*" * len(self.account_number)
        return self.account_number[-4:]

    def mask_iban(self) -> str:
        """Return masked IBAN for display purposes"""
        if not self.iban:
            return ""
        if len(self.iban) <= 8:
            return "*" * len(self.iban)
        return self.iban[:4] + "*" * (len(self.iban) - 8) + self.iban[-4:]

    @property
    def is_bank_enabled(self) -> bool:
        """Check if this bank account has any banking features enabled"""
        return any([
            self.online_banking_enabled,
            self.mobile_banking_enabled,
            self.wire_transfer_enabled,
            self.ach_enabled,
            self.bank_api_enabled
        ])

    def get_transfer_limits_dict(self) -> dict:
        """Get transfer limits as dictionary"""
        return {
            "daily_limit": float(self.daily_transfer_limit) if self.daily_transfer_limit else None,
            "monthly_limit": float(self.monthly_transfer_limit) if self.monthly_transfer_limit else None,
            "requires_dual_approval": self.requires_dual_approval
        }


class BankAccountHistory(Base):
    """Bank Account History model for audit trail"""

    __tablename__ = "bank_account_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("bank_accounts.id"), 
        nullable=False
    )
    action_type = Column(String(50), nullable=False)          # created, updated, activated, deactivated
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    changed_by = Column(String(100), nullable=False)
    changed_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(UTC)
    )
    reason = Column(Text, nullable=True)

    # Relationships
    bank_account = relationship("BankAccount", back_populates="history")

    def __repr__(self):
        return f"<BankAccountHistory(id={self.id}, action='{self.action_type}', bank_account_id={self.bank_account_id}, changed_at={self.changed_at})>"