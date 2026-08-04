"""Analytics module models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from app.database import Base
from app.models.types import JSONB, UUID


class MetaCampaign(Base):
    """Meta/Facebook ad campaign analytics snapshot"""

    __tablename__ = "meta_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    campaign_id = Column(String(256), nullable=True, index=True)
    campaign_name = Column(String(256), nullable=True)
    impressions = Column(Integer, nullable=True)
    clicks = Column(Integer, nullable=True)
    spend = Column(Numeric(10, 2), nullable=True)
    reach = Column(Integer, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    fetched_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    def __repr__(self):
        return f"<MetaCampaign(id={self.id}, campaign='{self.campaign_name}')>"


class ScanInteraction(Base):
    """Post-scan user interaction (CTA click, call, form submit, etc.)"""

    __tablename__ = "qr_scan_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    scan_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_scan_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    interaction_type = Column(String(50), nullable=False)
    interaction_target = Column(String, nullable=True)
    interaction_data = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
