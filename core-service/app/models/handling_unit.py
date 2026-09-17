"""Handling unit model (PR-11 / T-11, WF-018).

A handling unit is the physical carrier used during picking — trolley, carton
or pallet. Pick list items are optionally linked to one (``handling_unit_id``)
when ``pick.enable_handling_unit`` is enabled.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint

from app.database import Base
from app.models.types import UUID


class HandlingUnitType(str, enum.Enum):
    """Physical handling unit types."""

    TROLLEY = "trolley"
    CARTON = "carton"
    PALLET = "pallet"


class HandlingUnit(Base):
    """A physical trolley / carton / pallet used during picking."""

    __tablename__ = "handling_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=True)
    hu_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_handling_units_org_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<HandlingUnit(id={self.id}, code='{self.code}', type='{self.hu_type}')>"
