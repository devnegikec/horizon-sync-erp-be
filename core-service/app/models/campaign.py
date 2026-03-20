"""Campaign models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    campaign_type = Column(String(3), nullable=False)   # QR, WB, etc.
    campaign_status = Column(String(1), default="A")    # A=active, I=inactive
    location = Column(String(256), nullable=True)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    coupon_deliver = Column(String(50), default="Nothing")
    denominations = Column(Text, nullable=True)
    denominations_value = Column(Text, nullable=True)
    denominations_list = Column(JSONB, nullable=True)
    sms_senderid = Column(String(10), nullable=True)
    sms_template = Column(String(256), nullable=True)
    sms_variable = Column(JSONB, nullable=True)
    whatsapp_template_name = Column(String(256), nullable=True)
    whatsapp_template_type = Column(String(256), nullable=True)
    whatsapp_media_type = Column(String(256), nullable=True)
    whatsapp_interactive_type = Column(String(256), nullable=True)
    whatsapp_variable = Column(JSONB, nullable=True)
    media_link = Column(Text, nullable=True)
    campaign_message = Column(String(256), nullable=True)
    used_message = Column(String(256), nullable=True)
    terms_conditions = Column(Text, nullable=True)
    bypass_url = Column(Text, nullable=True)
    client_url = Column(Text, nullable=True)
    redirect_url_type = Column(String(2), nullable=True)
    budget_cap = Column(Integer, nullable=True)
    scans = Column(Integer, default=0)
    coupon_reissue_time = Column(String(50), nullable=True)
    brand_image_url = Column(Text, nullable=True)
    promotional_image_url = Column(Text, nullable=True)
    congrats_image_url = Column(Text, nullable=True)
    multilink_type = Column(String(3), nullable=True)
    multilink_items = Column(JSONB, nullable=True)
    game_config = Column(JSONB, nullable=True)
    shuffle = Column(Text, nullable=True)
    shuffle_gb = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    prizes = relationship("Play2WinPrize", back_populates="campaign",
                          cascade="all, delete-orphan")
    leads = relationship("CampaignLead", back_populates="campaign")
    coupons = relationship("Coupon", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}')>"


class Play2WinPrize(Base):
    __tablename__ = "play2win_prizes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    name = Column(String(128), nullable=False)
    prize_type = Column(String(20), default="none")
    value = Column(Numeric(10, 2), default=0)
    weight = Column(Integer, default=1)
    max_quantity = Column(Integer, nullable=True)
    slot_color = Column(String(7), default="#3157EF")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    campaign = relationship("Campaign", back_populates="prizes")


class WebCampaign(Base):
    __tablename__ = "web_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(256), nullable=True)
    campaign_type = Column(String(3), nullable=True)
    campaign_status = Column(String(1), default="A")
    from_date = Column(Date, nullable=True)
    to_date = Column(Date, nullable=True)
    coupon_deliver = Column(String(50), nullable=True)
    denominations = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    config = Column(JSONB, nullable=True)
    extra_data = Column(JSONB, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    coupons = relationship("Coupon", back_populates="web_campaign")
    external_coupons = relationship("ExternalCoupon", back_populates="web_campaign")
