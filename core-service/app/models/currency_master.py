"""Currency Master model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    String,
    text,
)

from app.database import Base
from app.models.types import UUID


class CurrencyMaster(Base):
    """Currency master model for multi-currency support"""

    __tablename__ = "currency_masters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Currency fields
    code = Column(String(3), nullable=False)
    name = Column(String(100), nullable=False)
    symbol = Column(String(5), nullable=True)
    is_base_currency = Column(Boolean, default=False, nullable=False)

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

    __table_args__ = (
        Index(
            "uq_currency_org_code",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_currency_masters_org_id", "organization_id"),
    )

    def __repr__(self):
        return f"<CurrencyMaster(id={self.id}, code='{self.code}', name='{self.name}')>"
