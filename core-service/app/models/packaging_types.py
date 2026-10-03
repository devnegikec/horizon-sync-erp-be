"""PackagingType model — reusable master for physical packaging types (Case, Pallet, Drum…)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class PackagingType(Base):
    """A reusable packaging type shared across items.

    The reusable half of packaging lives here (name, standard dimensions, weight).
    The item-specific half (how many base units fit in this pack) lives on
    ``item_packaging_units.conversion_factor``.
    """

    __tablename__ = "packaging_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    uom_id = Column(UUID(as_uuid=True), ForeignKey("uoms.id"), nullable=True)

    length_mm = Column(Numeric(10, 2), nullable=True)
    width_mm = Column(Numeric(10, 2), nullable=True)
    height_mm = Column(Numeric(10, 2), nullable=True)
    weight_grams = Column(Numeric(10, 2), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    uom = relationship("UOM")

    def __repr__(self):
        return f"<PackagingType(id={self.id}, code='{self.code}', name='{self.name}')>"
