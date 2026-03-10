"""Bank Transaction model for storing imported bank transactions"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID

if TYPE_CHECKING:
    from app.models.bank_account import BankAccount


class BankTransaction(Base):
    """Bank Transaction model for Shadow Ledger pattern"""

    __tablename__ = "bank_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    bank_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction details
    statement_date = Column(Date, nullable=False, index=True)
    transaction_amount = Column(Numeric(15, 2), nullable=False)
    transaction_description = Column(String(500), nullable=True)
    bank_reference = Column(String(100), nullable=True, index=True)
    transaction_status = Column(
        String(20), 
        nullable=False, 
        default='pending',
        index=True
    )  # pending, cleared, reconciled, void
    transaction_type = Column(String(10), nullable=False)  # debit, credit

    # Import metadata
    imported_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )
    import_source = Column(String(50), nullable=True)  # csv, pdf, mt940, api
    import_batch_id = Column(UUID(as_uuid=True), nullable=True)

    # Reconciliation tracking
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    is_duplicate = Column(Boolean, default=False)

    # Additional data
    extra_data = Column(JSONB, nullable=True)

    # Relationships
    bank_account = relationship("BankAccount", back_populates="transactions")
    reconciliations = relationship(
        "BankReconciliation",
        back_populates="bank_transaction",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "transaction_status IN ('pending', 'cleared', 'reconciled', 'void')",
            name='chk_transaction_status'
        ),
        CheckConstraint(
            "transaction_type IN ('debit', 'credit')",
            name='chk_transaction_type'
        ),
    )

    def __repr__(self):
        return (
            f"<BankTransaction(id={self.id}, "
            f"date={self.statement_date}, "
            f"amount={self.transaction_amount}, "
            f"type='{self.transaction_type}', "
            f"status='{self.transaction_status}')>"
        )

    @property
    def is_reconciled(self) -> bool:
        """Check if this transaction is reconciled"""
        return self.transaction_status == 'reconciled'

    @property
    def can_be_reconciled(self) -> bool:
        """Check if this transaction can be reconciled"""
        return self.transaction_status == 'cleared' and not self.is_reconciled
