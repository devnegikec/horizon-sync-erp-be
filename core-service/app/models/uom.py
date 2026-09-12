"""UOM (Unit of Measure) model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    text,
)

from app.database import Base
from app.models.types import UUID


class UOM(Base):
    """Unit of Measure master model"""

    __tablename__ = "uoms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # UOM fields
    name = Column(String(50), nullable=False)
    abbreviation = Column(String(10), nullable=False)
    uom_type = Column(String(20), nullable=True)  # count | weight | volume | length | time
    precision = Column(Integer, nullable=False, default=0, server_default="0")
    description = Column(Text, nullable=True)

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
            "uq_uom_org_name",
            "organization_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_uom_org_abbr",
            "organization_id",
            "abbreviation",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_uoms_org_id", "organization_id"),
    )

    def __repr__(self):
        return f"<UOM(id={self.id}, name='{self.name}', abbreviation='{self.abbreviation}')>"
