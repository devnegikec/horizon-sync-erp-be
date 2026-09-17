"""Customer model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Numeric, String, Text

from app.database import Base
from app.models.base import CustomerStatus
from app.models.types import JSONB, UUID


class Customer(Base):
    """Customer model for master data"""

    __tablename__ = "customers"
    __audited__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    customer_name = Column(String(255), nullable=False)
    customer_code = Column(String(50), nullable=False, index=True)

    # Contact
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Address
    address = Column(Text, nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Tax
    tax_number = Column(String(50), nullable=True)
    is_tax_exempt = Column(Boolean, default=False)

    # Status
    status = Column(
        Enum(
            CustomerStatus,
            name="customerstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=CustomerStatus.ACTIVE,
    )

    # Credit
    credit_limit = Column(Numeric(15, 2), default=0)
    outstanding_balance = Column(Numeric(15, 2), default=0)

    # Extra
    tags = Column(JSONB, nullable=True)
    custom_fields = Column(JSONB, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Customer(id={self.id}, code='{self.customer_code}', name='{self.customer_name}')>"
