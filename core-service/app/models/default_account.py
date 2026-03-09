"""Default Account model for transaction type mappings"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class DefaultAccount(Base):
    """Default Account model for mapping transaction types to accounts"""

    __tablename__ = "default_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Transaction type and scenario for multiple defaults per type
    transaction_type = Column(String(100), nullable=False)
    scenario = Column(String(100), nullable=True)

    # Foreign key to accounts table
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Multi-tenancy support
    organization_id = Column(UUID(as_uuid=True), nullable=False)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationship to Account
    account = relationship("Account", foreign_keys=[account_id])

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "transaction_type",
            "scenario",
            name="uq_default_accounts_org_type_scenario",
        ),
        Index("idx_default_accounts_transaction_type", "transaction_type"),
        Index("idx_default_accounts_scenario", "scenario"),
        Index("idx_default_accounts_organization_id", "organization_id"),
    )

    def __repr__(self):
        scenario_str = f", scenario={self.scenario}" if self.scenario else ""
        return f"<DefaultAccount(type={self.transaction_type}{scenario_str}, account_id={self.account_id})>"
