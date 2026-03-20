"""Destination Market model"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Numeric, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class DestinationMarket(Base):
    __tablename__ = "destination_markets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)          # e.g. "IN", "US-WEST"
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    currency_code = Column(String(3), nullable=True)   # links to currency_masters.code
    language = Column(String(10), nullable=True)       # BCP-47, e.g. "en-US"
    tax_rate = Column(Numeric(5, 4), nullable=True)    # e.g. 0.1800
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<DestinationMarket(code='{self.code}', name='{self.name}')>"
