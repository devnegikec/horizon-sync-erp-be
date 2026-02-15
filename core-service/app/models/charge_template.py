"""Charge Template model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.types import JSONB


class ChargeTemplate(Base):
    """Extra Charge Template model for managing additional charges"""

    __tablename__ = "charge_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    template_code = Column(String(100), nullable=False, index=True)
    template_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Charge Configuration
    charge_type = Column(String(50), nullable=False, index=True)  # "Shipping", "Handling", "Packaging", "Insurance", "Custom"
    calculation_method = Column(String(20), nullable=False)  # "FIXED" or "PERCENTAGE"

    # Calculation Parameters
    fixed_amount = Column(Numeric(15, 2), nullable=True)  # Required when calculation_method is FIXED
    percentage_rate = Column(Numeric(5, 2), nullable=True)  # Required when calculation_method is PERCENTAGE
    base_on = Column(String(20), nullable=True)  # "Net_Total" or "Grand_Total" (for percentage)

    # Account Reference
    account_head_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to chart_of_accounts

    # Configuration
    is_active = Column(Boolean, default=True)

    # Applicability Rules (JSONB for flexible rule definitions)
    applicability_rules = Column(JSONB, nullable=True)

    # Extensibility
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
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    def __repr__(self):
        return f"<ChargeTemplate(id={self.id}, code='{self.template_code}', name='{self.template_name}', type='{self.charge_type}')>"
