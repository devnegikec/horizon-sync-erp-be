"""PaymentReference model definition for Payment Flow system"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class PaymentReference(Base):
    """PaymentReference model linking payments to invoices"""

    __tablename__ = "payment_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Reference Information
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payment_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Allocation Information
    allocated_amount = Column(Numeric(15, 2), nullable=False)
    exchange_rate = Column(Numeric(15, 6), nullable=True, default=1.0)
    allocated_amount_invoice_currency = Column(Numeric(15, 2), nullable=True)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Relationships
    payment_entry = relationship(
        "PaymentEntry",
        back_populates="payment_references",
    )
    invoice = relationship(
        "Invoice",
        foreign_keys=[invoice_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "payment_id", "invoice_id", name="unique_payment_references_payment_invoice"
        ),
    )

    def __repr__(self):
        return (
            f"<PaymentReference(id={self.id}, "
            f"payment_id={self.payment_id}, "
            f"invoice_id={self.invoice_id}, "
            f"allocated_amount={self.allocated_amount})>"
        )
