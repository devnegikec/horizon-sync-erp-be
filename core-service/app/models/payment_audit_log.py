"""PaymentAuditLog model definition for Payment Flow system"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PaymentAuditAction
from app.models.types import UUID, JSONB


class PaymentAuditLog(Base):
    """PaymentAuditLog model for tracking payment entry changes"""

    __tablename__ = "payment_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Audit Information
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payment_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(
        Enum(
            PaymentAuditAction,
            name="payment_audit_action",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Change Tracking
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)

    # Timestamp
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Relationships
    payment_entry = relationship(
        "PaymentEntry",
        back_populates="audit_logs",
    )

    def __repr__(self):
        return (
            f"<PaymentAuditLog(id={self.id}, "
            f"payment_id={self.payment_id}, "
            f"action='{self.action.value}', "
            f"timestamp='{self.timestamp}')>"
        )
