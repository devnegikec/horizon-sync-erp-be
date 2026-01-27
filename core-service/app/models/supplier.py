"""Supplier model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base
from app.models.base import SupplierStatus


class Supplier(Base):
    """Supplier model for master data"""

    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    supplier_name = Column(String(255), nullable=False)
    supplier_code = Column(String(50), nullable=False, index=True)

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

    # Status
    status = Column(
        Enum(
            SupplierStatus,
            name="supplierstatus",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SupplierStatus.ACTIVE,
    )

    # Payment Terms (days)
    payment_terms = Column(Integer, default=30)

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
        return f"<Supplier(id={self.id}, code='{self.supplier_code}', name='{self.supplier_name}')>"
