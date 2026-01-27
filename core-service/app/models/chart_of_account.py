"""Chart of Account model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import AccountType


class ChartOfAccount(Base):
    """Chart of Account model with hierarchy support"""

    __tablename__ = "chart_of_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Basic Information
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    account_type = Column(
        Enum(
            AccountType,
            name="accounttype",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    # Hierarchy
    parent_account_id = Column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id"), nullable=True
    )
    level = Column(Integer, default=1)
    is_group = Column(Boolean, default=False)

    # Balances
    opening_balance = Column(Numeric(15, 2), default=0)
    current_balance = Column(Numeric(15, 2), default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Extra
    tags = Column(JSONB, nullable=True)
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

    # Relationships
    parent = relationship("ChartOfAccount", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<ChartOfAccount(id={self.id}, code='{self.account_code}', name='{self.account_name}')>"
