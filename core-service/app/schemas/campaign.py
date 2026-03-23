"""Pydantic schemas for Campaigns & Coupons module"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Campaign ──────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(..., max_length=256)
    campaign_type: str = Field(..., max_length=3)
    from_date: date
    to_date: date
    campaign_status: str = Field("A", max_length=1)
    location: str | None = None
    coupon_deliver: str = "Nothing"
    denominations: str | None = None
    denominations_value: str | None = None
    denominations_list: list[Any] | None = None
    sms_senderid: str | None = None
    sms_template: str | None = None
    sms_variable: dict[str, Any] | None = None
    whatsapp_template_name: str | None = None
    whatsapp_template_type: str | None = None
    whatsapp_media_type: str | None = None
    whatsapp_interactive_type: str | None = None
    whatsapp_variable: dict[str, Any] | None = None
    media_link: str | None = None
    campaign_message: str | None = None
    used_message: str | None = None
    terms_conditions: str | None = None
    bypass_url: str | None = None
    client_url: str | None = None
    redirect_url_type: str | None = None
    budget_cap: int | None = None
    coupon_reissue_time: str | None = None
    brand_image_url: str | None = None
    promotional_image_url: str | None = None
    congrats_image_url: str | None = None
    multilink_type: str | None = None
    multilink_items: list[Any] | None = None
    game_config: dict[str, Any] | None = None
    extra_data: dict[str, Any] | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, max_length=256)
    campaign_status: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    campaign_message: str | None = None
    used_message: str | None = None
    terms_conditions: str | None = None
    budget_cap: int | None = None
    media_link: str | None = None
    brand_image_url: str | None = None
    promotional_image_url: str | None = None
    congrats_image_url: str | None = None
    multilink_items: list[Any] | None = None
    game_config: dict[str, Any] | None = None
    extra_data: dict[str, Any] | None = None


class CampaignResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    campaign_type: str
    campaign_status: str
    from_date: date
    to_date: date
    coupon_deliver: str | None
    budget_cap: int | None
    scans: int
    media_link: str | None
    brand_image_url: str | None
    promotional_image_url: str | None
    terms_conditions: str | None
    multilink_items: list[Any] | None
    game_config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignResponse]
    pagination: dict[str, Any]


# ── Play2Win Prize ─────────────────────────────────────────────────────────────

class PrizeCreate(BaseModel):
    name: str = Field(..., max_length=128)
    prize_type: str = "none"
    value: float = 0
    weight: int = 1
    max_quantity: int | None = None
    slot_color: str = "#3157EF"
    is_active: bool = True


class PrizeResponse(PrizeCreate):
    id: UUID
    campaign_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Lead ──────────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    campaign_id: UUID | None = None
    name: str | None = None
    mobilenumber: str | None = None
    email: str | None = None
    address: str | None = None
    location: str | None = None
    pincode: str | None = None
    dob: date | None = None
    gender: str | None = None
    occupation: str | None = None
    gst_number: str | None = None
    state_name: str | None = None
    country: str | None = None
    rating: str | None = None
    comment: str | None = None
    extra_data: dict[str, Any] | None = None


class LeadResponse(LeadCreate):
    id: UUID
    organization_id: UUID
    status: str | None
    redeem_mode: str
    external_lead: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    leads: list[LeadResponse]
    pagination: dict[str, Any]


# ── Coupon ────────────────────────────────────────────────────────────────────

class CouponVerifyRequest(BaseModel):
    coupon_code: str
    mobilenumber: str | None = None


class CouponVerifyResponse(BaseModel):
    is_valid: bool
    is_used: bool
    is_expired: bool
    coupon_id: UUID | None
    value: str | None
    units: str | None
    expiry: datetime | None
    message: str


class CouponRedeemRequest(BaseModel):
    coupon_code: str
    mobilenumber: str | None = None
    final_billed_amount: float | None = None
    location: str | None = None
    rating: str | None = None
    comment: str | None = None
    custom_answer: dict[str, Any] | None = None


class CouponRedeemResponse(BaseModel):
    success: bool
    coupon_id: UUID
    message: str


class CouponUnlockRequest(BaseModel):
    coupon_code: str
    mobilenumber: str | None = None
    location: str | None = None
    user_reference: str | None = None
    notes: str | None = None


class CouponUnlockResponse(BaseModel):
    success: bool
    coupon_id: UUID
    unlock_count: int
    message: str


class CouponResponse(BaseModel):
    id: UUID
    organization_id: UUID
    campaign_id: UUID | None
    coupon_code: str | None
    name: str | None
    mobilenumber: str | None
    value: str | None
    units: str | None
    used: str | None
    expiry: datetime | None
    is_unlocked: bool
    unlock_count: int
    redeem_mode: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CouponListResponse(BaseModel):
    coupons: list[CouponResponse]
    pagination: dict[str, Any]


# ── Feedback / Survey ─────────────────────────────────────────────────────────

class FeedbackSubmit(BaseModel):
    campaign_id: UUID
    mobilenumber: str | None = None
    coupon_code: str | None = None
    rating: str | None = None
    product_rating: str | None = None
    color_rating: str | None = None
    price_rating: str | None = None
    comment: str | None = None
    custom_question: dict[str, Any] | None = None
    custom_answer: dict[str, Any] | None = None


class FeedbackResponse(BaseModel):
    success: bool
    coupon_id: UUID | None
    message: str
