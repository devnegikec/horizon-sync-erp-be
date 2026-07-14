"""Tax Template and Tax Rule model definitions"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB


class TaxTemplate(Base):
    """Tax Template model for managing tax configurations"""

    __tablename__ = "tax_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    template_code = Column(String(100), nullable=False, index=True)
    template_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    tax_category = Column(String(50), nullable=False)  # "Input" or "Output"

    # Configuration
    is_default = Column(Boolean, default=False, index=True)
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

    # Relationships
    tax_rules = relationship(
        "TaxRule",
        back_populates="tax_template",
        cascade="all, delete-orphan",
        order_by="TaxRule.sequence",
    )

    def __repr__(self):
        return f"<TaxTemplate(id={self.id}, code='{self.template_code}', name='{self.template_name}')>"


class TaxRule(Base):
    """Tax Rule model for individual tax components within a template"""

    __tablename__ = "tax_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tax_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tax_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic Information
    rule_name = Column(String(255), nullable=False)
    tax_type = Column(String(100), nullable=False)  # "GST", "VAT", "CGST", "SGST", etc.
    description = Column(Text, nullable=True)

    # Tax Configuration
    tax_rate = Column(Numeric(5, 2), nullable=False)  # Percentage (e.g., 9.00 for 9%)
    account_head_id = Column(
        UUID(as_uuid=True), nullable=False
    )  # Reference to chart_of_accounts

    # Calculation Settings
    is_compound = Column(Boolean, default=False)  # Tax on tax
    sequence = Column(Integer, nullable=False)  # Order of calculation

    # Applicability Conditions (JSONB for flexible conditions)
    applicability_conditions = Column(JSONB, nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    tax_template = relationship("TaxTemplate", back_populates="tax_rules")

    def __repr__(self):
        return f"<TaxRule(id={self.id}, name='{self.rule_name}', type='{self.tax_type}', rate={self.tax_rate})>"
