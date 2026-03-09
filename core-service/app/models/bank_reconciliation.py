"""Bank Reconciliation model for linking bank transactions with journal entries"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID

if TYPE_CHECKING:
    from app.models.bank_transaction import BankTransaction
    from app.models.journal_entry import JournalEntry


class BankReconciliation(Base):
    """Bank Reconciliation model for matching bank transactions with journal entries"""

    __tablename__ = "bank_reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    bank_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    journal_entry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reconciliation metadata
    reconciliation_type = Column(
        String(20),
        nullable=False
    )  # manual, auto_exact, auto_fuzzy, many_to_one
    reconciliation_status = Column(
        String(20),
        nullable=False,
        default='suggested',
        index=True
    )  # suggested, confirmed, rejected
    match_confidence = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00

    # Multi-currency support
    exchange_rate = Column(Numeric(15, 6), nullable=True)
    converted_amount = Column(Numeric(15, 2), nullable=True)

    # Audit
    reconciled_by = Column(String(100), nullable=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Undo tracking
    is_active = Column(Boolean, default=True, index=True)
    undone_by = Column(String(100), nullable=True)
    undone_at = Column(DateTime(timezone=True), nullable=True)
    undo_reason = Column(Text, nullable=True)

    # Relationships
    bank_transaction = relationship("BankTransaction", back_populates="reconciliations")
    journal_entry = relationship("JournalEntry")

    __table_args__ = (
        CheckConstraint(
            "reconciliation_type IN ('manual', 'auto_exact', 'auto_fuzzy', 'many_to_one')",
            name='chk_reconciliation_type'
        ),
        CheckConstraint(
            "reconciliation_status IN ('suggested', 'confirmed', 'rejected')",
            name='chk_reconciliation_status'
        ),
        CheckConstraint(
            "match_confidence >= 0 AND match_confidence <= 1",
            name='chk_match_confidence'
        ),
    )

    def __repr__(self):
        return (
            f"<BankReconciliation(id={self.id}, "
            f"type='{self.reconciliation_type}', "
            f"status='{self.reconciliation_status}', "
            f"confidence={self.match_confidence})>"
        )

    @property
    def is_confirmed(self) -> bool:
        """Check if this reconciliation is confirmed"""
        return self.reconciliation_status == 'confirmed' and self.is_active

    @property
    def is_suggested(self) -> bool:
        """Check if this reconciliation is a suggestion"""
        return self.reconciliation_status == 'suggested' and self.is_active

    @property
    def can_be_undone(self) -> bool:
        """Check if this reconciliation can be undone"""
        return self.is_confirmed and self.is_active
