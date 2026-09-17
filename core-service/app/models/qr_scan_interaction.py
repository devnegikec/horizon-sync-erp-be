"""QR Scan Interaction model — tracks post-scan user actions."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class QRScanInteraction(Base):
    """Individual user interaction that occurs after a QR code scan.

    Examples: clicking a CTA button, calling support, filling a form,
    watching a video, sharing the product page.
    """

    __tablename__ = "qr_scan_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    scan_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_scan_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interaction_type = Column(String(50), nullable=False)
    interaction_target = Column(Text, nullable=True)
    interaction_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self):
        return (
            f"<QRScanInteraction(id={self.id}, "
            f"type='{self.interaction_type}', scan={self.scan_event_id})>"
        )
