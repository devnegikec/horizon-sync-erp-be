"""Feature flag model for runtime feature toggling"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base
from app.models.types import UUID


class FeatureFlag(Base):
    """GLOBAL-scoped feature flags for runtime feature toggling."""

    __tablename__ = "feature_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=False)
    visible = Column(Boolean, nullable=False, default=True)
    scope = Column(String(20), nullable=False, default="GLOBAL")
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    rollout_percentage = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "name", "scope", "tenant_id", "user_id", name="uq_feature_flag_scope"
        ),
        Index("ix_feature_flags_name", "name"),
        Index("ix_feature_flags_scope", "scope"),
    )

    def __repr__(self):
        return f"<FeatureFlag(id={self.id}, name='{self.name}', enabled={self.enabled}, visible={self.visible})>"
