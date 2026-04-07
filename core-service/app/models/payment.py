"""Payment model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, Numeric, String, Text

from app.database import Base
from app.models.base import PaymentMethod, PaymentStatus, PaymentType
from app.models.types import JSONB, UUID


class Payment(Base):
    __tablename__ = "payments"
    __audited__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payment_no = Column(String(100), nullable=False)
    payment_type = Column(
        Enum(
            PaymentType,
            name="paymenttype",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=False,
    )
    party_id = Column(UUID(as_uuid=True), nullable=False)
    party_type = Column(String(20), nullable=False)
    posting_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(
        Enum(
            PaymentStatus,
            name="paymentstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    payment_method = Column(
        Enum(
            PaymentMethod,
            name="paymentmethod",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        nullable=True,
    )
    reference_no = Column(String(100), nullable=True)
    remarks = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
