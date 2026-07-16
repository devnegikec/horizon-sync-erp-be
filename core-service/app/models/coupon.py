"""Coupon, Lead, and Tag models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSONB, UUID

# M2M junction table
lead_tags = Table(
    "lead_tags",
    Base.metadata,
    Column(
        "lead_id",
        UUID(as_uuid=True),
        ForeignKey("campaign_leads.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("campaign_tags.id", ondelete="CASCADE"),
        nullable=False,
    ),
)


class CampaignTag(Base):
    __tablename__ = "campaign_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    segment = Column(String(20), nullable=True)
    tag_type = Column(String(10), nullable=True)
    tag_source = Column(String(256), nullable=True)
    total_lead = Column(Integer, default=0)
    tag_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    leads = relationship("CampaignLead", secondary=lead_tags, back_populates="tags")


class CampaignLead(Base):
    __tablename__ = "campaign_leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    name = Column(String(255), nullable=True)
    mobilenumber = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    pincode = Column(String(30), nullable=True)
    dob = Column(Date, nullable=True)
    gender = Column(String(30), nullable=True)
    occupation = Column(String(256), nullable=True)
    gst_number = Column(String(256), nullable=True)
    state_name = Column(String(30), nullable=True)
    country = Column(String(30), nullable=True)
    coupon = Column(String(255), nullable=True)
    value = Column(String(255), nullable=True)
    used = Column(String(255), nullable=True)
    expiry = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    used_timestamp = Column(DateTime(timezone=True), nullable=True)
    rating = Column(String(255), nullable=True)
    comment = Column(String(255), nullable=True)
    status = Column(String(20), nullable=True)
    redeem_mode = Column(String(10), default="none")
    external_lead = Column(Boolean, default=False)
    marital_status = Column(String(30), nullable=True)
    lead_owner_id = Column(UUID(as_uuid=True), nullable=True)
    is_archived = Column(Boolean, default=False)
    is_blocklisted = Column(Boolean, default=False)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    campaign = relationship("Campaign", back_populates="leads")
    tags = relationship("CampaignTag", secondary=lead_tags, back_populates="leads")
    coupons = relationship("Coupon", back_populates="lead")
    notes = relationship(
        "LeadNote", back_populates="lead", cascade="all, delete-orphan"
    )


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    web_campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("web_campaigns.id"), nullable=True
    )
    lead_id = Column(UUID(as_uuid=True), ForeignKey("campaign_leads.id"), nullable=True)
    coupon_code = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    mobilenumber = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    state_name = Column(String(30), nullable=True)
    dob = Column(Date, nullable=True)
    gender = Column(String(30), nullable=True)
    occupation = Column(String(30), nullable=True)
    units = Column(String(255), default="RS")
    value = Column(String(255), nullable=True)
    used = Column(String(255), nullable=True)
    min_bill_value = Column(String(255), nullable=True)
    expiry = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    used_timestamp = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(255), nullable=True)
    rating = Column(String(255), nullable=True)
    product_rating = Column(String(255), nullable=True)
    color_rating = Column(String(255), nullable=True)
    price_rating = Column(String(255), nullable=True)
    comment = Column(String(255), nullable=True)
    custom_question = Column(JSONB, nullable=True)
    custom_answer = Column(JSONB, nullable=True)
    acception_id = Column(String(256), nullable=True)
    is_unlocked = Column(Boolean, default=False)
    unlock_count = Column(Integer, default=0)
    final_billed_amount = Column(Float, nullable=True)
    redeem_mode = Column(String(10), default="none")
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    campaign = relationship("Campaign", back_populates="coupons")
    web_campaign = relationship("WebCampaign", back_populates="coupons")
    lead = relationship("CampaignLead", back_populates="coupons")
    unlock_logs = relationship(
        "CouponUnlockLog", back_populates="coupon", cascade="all, delete-orphan"
    )


class CouponUnlockLog(Base):
    __tablename__ = "coupon_unlock_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("coupons.id"), nullable=False)
    action = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    user_reference = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    coupon = relationship("Coupon", back_populates="unlock_logs")


class ExternalCoupon(Base):
    __tablename__ = "external_coupons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    web_campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("web_campaigns.id"), nullable=True
    )
    coupon_code = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    mobilenumber = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    state_name = Column(String(30), nullable=True)
    city = Column(String(30), nullable=True)
    zipcode = Column(String(30), nullable=True)
    ip_address = Column(String(255), nullable=True)
    dob = Column(Date, nullable=True)
    age = Column(String(30), nullable=True)
    occupation = Column(String(30), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    web_campaign = relationship("WebCampaign", back_populates="external_coupons")


class CouponDuration(Base):
    __tablename__ = "coupon_durations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    delivery_type = Column(String(3), nullable=False)
    cooling_periods = Column(Integer, nullable=False)
    min_order_amount = Column(String(256), default="1500")


class ShopifyConfig(Base):
    __tablename__ = "shopify_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    api_endpoint = Column(Text, nullable=True)
    auth_token = Column(String(256), nullable=True)
    price_rule_id = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class LeadNote(Base):
    """Notes/comments on leads (admins can add multiple notes per lead)."""

    __tablename__ = "lead_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaign_leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    lead = relationship("CampaignLead", back_populates="notes")


class Store(Base):
    """POS/store locations for business analytics dashboard."""

    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    pincode = Column(String(30), nullable=True)
    contact_person = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class QReachAPIKey(Base):
    """API keys for QReach/QSeal developer portal."""

    __tablename__ = "qreach_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    prefix = Column(String(12), nullable=False)  # e.g. "qr_live_ab"
    hashed_key = Column(String(255), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class LandingCustomization(Base):
    """Custom form configurations for campaign landing pages."""

    __tablename__ = "landing_customizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    form_config = Column(JSONB, nullable=True)  # Custom questions/fields configuration
    theme_config = Column(JSONB, nullable=True)  # Colors, fonts, logos
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
