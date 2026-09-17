"""Landing Page Config model — per-product customisation for QR verification pages."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class LandingPageConfig(Base):
    """Custom landing page configuration for a QR product.

    Each QR product can have ONE config. The config controls branding,
    product details visibility, social links, feedback, warranty, and
    custom CTA sections that render on the consumer-facing verification page.
    """

    __tablename__ = "landing_page_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Visuals ──────────────────────────────────────────────────────────
    logo_url = Column(Text, nullable=True)
    banner_image_url = Column(Text, nullable=True)

    # ── Branding ─────────────────────────────────────────────────────────
    primary_color = Column(String(7), nullable=False, default="#1a56db")
    accent_color = Column(String(7), nullable=False, default="#f59e0b")

    # ── Sections (stored as JSONB) ───────────────────────────────────────
    product_details = Column(JSONB, nullable=False, default=dict)
    social_links = Column(JSONB, nullable=False, default=list)
    feedback = Column(JSONB, nullable=False, default=dict)
    warranty = Column(JSONB, nullable=False, default=dict)
    custom_cta = Column(JSONB, nullable=False, default=dict)
    footer = Column(JSONB, nullable=False, default=dict)

    # ── Audit ────────────────────────────────────────────────────────────
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────
    product = relationship("QRProduct", back_populates="landing_page_config")

    def __repr__(self):
        return f"<LandingPageConfig(id={self.id}, product_id={self.product_id})>"
