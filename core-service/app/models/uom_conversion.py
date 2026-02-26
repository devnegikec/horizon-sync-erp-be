"""UOM Conversion model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)

from app.database import Base
from app.models.types import UUID


class UOMConversion(Base):
    """UOM Conversion model - stores conversion factors between UOMs for a specific item"""

    __tablename__ = "uom_conversions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=False, index=True
    )

    # Conversion fields
    from_uom = Column(String(50), nullable=False)
    to_uom = Column(String(50), nullable=False)
    conversion_factor = Column(Numeric(19, 6), nullable=False)

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
            "uq_uom_conv_org_item_pair",
            "organization_id",
            "item_id",
            "from_uom",
            "to_uom",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "conversion_factor > 0", name="ck_uom_conv_positive_factor"
        ),
        Index("ix_uom_conversions_item", "item_id"),
    )

    def __repr__(self):
        return (
            f"<UOMConversion(id={self.id}, item_id={self.item_id}, "
            f"from_uom='{self.from_uom}', to_uom='{self.to_uom}', "
            f"factor={self.conversion_factor})>"
        )
