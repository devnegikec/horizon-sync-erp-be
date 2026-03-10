"""Exchange Rate model definition for multi-currency support"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)

from app.database import Base
from app.models.types import UUID


class ExchangeRate(Base):
    """Exchange Rate model for currency conversions"""

    __tablename__ = "exchange_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization scoping (nullable for backward compatibility with existing data)
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Currency pair
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)

    # Exchange rate with high precision
    rate = Column(Numeric(19, 6), nullable=False)

    # Effective date for historical tracking
    effective_date = Column(Date, nullable=False)

    # Capture timestamp for audit trail
    captured_at = Column(
        DateTime(timezone=True), nullable=True, default=lambda: datetime.now(UTC)
    )

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "from_currency",
            "to_currency",
            "effective_date",
            name="uq_exchange_rate_currency_date",
        ),
        CheckConstraint("rate > 0", name="ck_exchange_rate_positive"),
        Index("ix_exchange_rates_currencies", "from_currency", "to_currency"),
        Index("ix_exchange_rates_effective_date", "effective_date"),
        Index("ix_exchange_rates_org_id", "organization_id"),
    )

    def __repr__(self):
        return f"<ExchangeRate(from={self.from_currency}, to={self.to_currency}, rate={self.rate}, date={self.effective_date})>"
