"""PaymentEntry model definition for Payment Flow system"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import (
    PaymentEntryStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentSource,
)
from app.models.types import UUID


class PaymentEntry(Base):
    """PaymentEntry model representing actual money received or paid"""

    __tablename__ = "payment_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Payment Information
    payment_type = Column(
        Enum(
            PaymentEntryType,
            name="payment_type",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    party_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency_code = Column(String(3), nullable=False, default="USD")
    payment_date = Column(DateTime(timezone=True), nullable=False)
    payment_mode = Column(
        Enum(
            PaymentMode,
            name="payment_mode",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    reference_no = Column(String(100), nullable=True, index=True)
    bank_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Status and Source
    status = Column(
        Enum(
            PaymentEntryStatus,
            name="payment_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PaymentEntryStatus.DRAFT,
        index=True,
    )
    source = Column(
        Enum(
            PaymentSource,
            name="payment_source",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PaymentSource.MANUAL,
    )
    gateway_transaction_id = Column(String(200), nullable=True)
    receipt_number = Column(String(50), nullable=True, unique=True, index=True)

    # Cancellation Information
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(UUID(as_uuid=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    bank_account = relationship(
        "BankAccount",
        foreign_keys=[bank_account_id],
    )
    payment_references = relationship(
        "PaymentReference",
        back_populates="payment_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs = relationship(
        "PaymentAuditLog",
        back_populates="payment_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @hybrid_property
    def unallocated_amount(self) -> Decimal:
        """
        Calculate unallocated amount as payment amount minus sum of allocated amounts.

        Returns:
            Decimal: The unallocated amount
        """
        if not self.payment_references:
            return Decimal(str(self.amount))

        total_allocated = sum(
            Decimal(str(ref.allocated_amount)) for ref in self.payment_references
        )
        return Decimal(str(self.amount)) - total_allocated

    def __repr__(self):
        return (
            f"<PaymentEntry(id={self.id}, "
            f"type='{self.payment_type.value}', "
            f"amount={self.amount}, "
            f"currency='{self.currency_code}', "
            f"mode='{self.payment_mode.value}', "
            f"status='{self.status.value}', "
            f"date='{self.payment_date}', "
            f"bank_account_id={self.bank_account_id})>"
        )
