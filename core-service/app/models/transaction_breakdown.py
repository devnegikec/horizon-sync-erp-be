"""Transaction Tax and Charge Breakdown model definitions"""

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
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TransactionTaxBreakdown(Base):
    """Transaction Tax Breakdown model for storing detailed tax calculations"""

    __tablename__ = "transaction_tax_breakdown"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Transaction Reference
    transaction_type = Column(String(50), nullable=False, index=True)  # "Quotation", "Sales_Order", "Purchase_Order", "Invoice", etc.
    transaction_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Tax Template and Rule References
    tax_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tax_templates.id"),
        nullable=False,
    )
    tax_rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tax_rules.id"),
        nullable=False,
    )

    # Tax Details
    tax_type = Column(String(100), nullable=False, index=True)  # "GST", "VAT", "CGST", "SGST", etc.
    tax_rate = Column(Numeric(5, 2), nullable=False)  # Percentage (e.g., 9.00 for 9%)
    taxable_amount = Column(Numeric(15, 2), nullable=False)  # Amount on which tax is calculated
    tax_amount = Column(Numeric(15, 2), nullable=False)  # Calculated tax amount

    # Calculation Settings
    is_compound = Column(Boolean, default=False)  # Whether this is a compound tax
    sequence = Column(Integer, nullable=False)  # Order of calculation

    # Account Reference
    account_head_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to chart_of_accounts

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self):
        return (
            f"<TransactionTaxBreakdown(id={self.id}, "
            f"transaction_type='{self.transaction_type}', "
            f"transaction_id={self.transaction_id}, "
            f"tax_type='{self.tax_type}', "
            f"tax_amount={self.tax_amount})>"
        )


class TransactionChargeBreakdown(Base):
    """Transaction Charge Breakdown model for storing detailed charge calculations"""

    __tablename__ = "transaction_charge_breakdown"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Transaction Reference
    transaction_type = Column(String(50), nullable=False, index=True)  # "Quotation", "Sales_Order", "Purchase_Order", "Invoice", etc.
    transaction_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Charge Template Reference (nullable for manual charges)
    charge_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("charge_templates.id"),
        nullable=True,
    )

    # Charge Details
    charge_type = Column(String(50), nullable=False, index=True)  # "Shipping", "Handling", "Packaging", "Insurance", "Custom"
    description = Column(String(255), nullable=True)
    calculation_method = Column(String(20), nullable=False)  # "FIXED" or "PERCENTAGE"
    charge_amount = Column(Numeric(15, 2), nullable=False)  # Calculated charge amount

    # Account Reference
    account_head_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to chart_of_accounts

    # Configuration
    is_auto_calculated = Column(Boolean, default=True)  # True for template-based, False for manual

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self):
        return (
            f"<TransactionChargeBreakdown(id={self.id}, "
            f"transaction_type='{self.transaction_type}', "
            f"transaction_id={self.transaction_id}, "
            f"charge_type='{self.charge_type}', "
            f"charge_amount={self.charge_amount})>"
        )
