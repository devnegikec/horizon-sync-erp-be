"""Pick settings model — tenant-scoped WMS pick configuration (PR-02 / T-17).

Stores per-organization overrides for the ``pick.*`` config keys defined in
``app/core/pick_config.py``. Values are stored as JSON so bool / int / float /
enum / list keys all share one table. Defaults live in code (see the catalog)
and are only materialized here when an organization overrides a key.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint

from app.database import Base
from app.models.types import JSONB, UUID


class PickSetting(Base):
    """One tenant-scoped ``pick.*`` config override."""

    __tablename__ = "pick_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(JSONB, nullable=False)

    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "key", name="uq_pick_settings_org_key"
        ),
        Index("ix_pick_settings_organization_id", "organization_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PickSetting(organization_id={self.organization_id}, "
            f"key='{self.key}', value={self.value!r})>"
        )
