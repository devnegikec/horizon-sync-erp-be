"""Pydantic schemas for Landing Page Config module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# ── Enums / Literals ──────────────────────────────────────────────────────

SocialPlatform = str  # validated via Field pattern
CTAButtonStyle = str  # validated via Field pattern
FeedbackType = str  # validated via Field pattern

# ── Nested config objects ─────────────────────────────────────────────────


class CustomField(BaseModel):
    """A custom key-value field displayed in the product details section."""

    label: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class ProductDetailsConfig(BaseModel):
    """Controls which product attributes are visible on the landing page."""

    show_gtin: bool = True
    show_batch: bool = True
    show_mfg_date: bool = True
    show_expiry_date: bool = True
    show_serial_number: bool = False
    custom_fields: list[CustomField] = []


class SocialLink(BaseModel):
    """A social media or website link displayed as an icon/link."""

    platform: str = Field(
        ...,
        pattern=r"^(facebook|twitter|instagram|linkedin|youtube|whatsapp|telegram|website|other)$",
    )
    url: str = Field(..., min_length=1, max_length=2048)
    label: str | None = Field(None, max_length=100)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=0)


class FeedbackConfig(BaseModel):
    """Feedback / survey section configuration."""

    enabled: bool = False
    type: str = Field(default="none", pattern=r"^(feedback|survey|none)$")
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=500)
    survey_url: str | None = Field(None, max_length=2048)
    thank_you_message: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def survey_url_required(self):
        if self.enabled and self.type == "survey" and not self.survey_url:
            raise ValueError("survey_url is required when type is 'survey'")
        return self


class WarrantyConfig(BaseModel):
    """Warranty registration CTA section."""

    enabled: bool = False
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=1000)
    cta_text: str = Field(default="", max_length=50)
    cta_url: str = Field(default="", max_length=2048)


class CustomCTAConfig(BaseModel):
    """A custom call-to-action button."""

    enabled: bool = False
    button_text: str = Field(default="", max_length=50)
    button_url: str = Field(default="", max_length=2048)
    button_style: str = Field(
        default="primary", pattern=r"^(primary|secondary|outline)$"
    )


class FooterLink(BaseModel):
    """A link displayed in the footer."""

    label: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=2048)
    sort_order: int = Field(default=0, ge=0)


class FooterConfig(BaseModel):
    """Footer section configuration."""

    text: str = Field(default="", max_length=500)
    show_powered_by: bool = True
    custom_links: list[FooterLink] = []


# ── Top-level Config ─────────────────────────────────────────────────────


class LandingPageConfigBase(BaseModel):
    """Shared fields for create/update/response."""

    logo_url: str | None = None
    banner_image_url: str | None = None
    primary_color: str = Field(default="#1a56db", pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str = Field(default="#f59e0b", pattern=r"^#[0-9a-fA-F]{6}$")
    product_details: ProductDetailsConfig = Field(default_factory=ProductDetailsConfig)
    social_links: list[SocialLink] = []
    feedback: FeedbackConfig = Field(default_factory=FeedbackConfig)
    warranty: WarrantyConfig = Field(default_factory=WarrantyConfig)
    custom_cta: CustomCTAConfig = Field(default_factory=CustomCTAConfig)
    footer: FooterConfig = Field(default_factory=FooterConfig)


class LandingPageConfigCreate(LandingPageConfigBase):
    """Request body for POST /products/{productId}/landing-page."""

    pass


class LandingPageConfigUpdate(BaseModel):
    """Request body for PATCH — all fields optional, nested objects merged."""

    logo_url: str | None = None
    banner_image_url: str | None = None
    primary_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    product_details: ProductDetailsConfig | None = None
    social_links: list[SocialLink] | None = None
    feedback: FeedbackConfig | None = None
    warranty: WarrantyConfig | None = None
    custom_cta: CustomCTAConfig | None = None
    footer: FooterConfig | None = None


class LandingPageConfigResponse(BaseModel):
    """Response for all landing page config CRUD operations."""

    config: "LandingPageConfigOut"

    model_config = {"from_attributes": True}


class LandingPageConfigOut(BaseModel):
    """The full config object returned inside the response envelope."""

    id: UUID
    product_id: UUID
    organization_id: UUID
    logo_url: str | None
    banner_image_url: str | None
    primary_color: str
    accent_color: str
    product_details: ProductDetailsConfig
    social_links: list[SocialLink]
    feedback: FeedbackConfig
    warranty: WarrantyConfig
    custom_cta: CustomCTAConfig
    footer: FooterConfig
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Image Upload ─────────────────────────────────────────────────────────


class ImageUploadResponse(BaseModel):
    """Response after uploading a logo or banner image."""

    url: str


# Rebuild forward reference
LandingPageConfigResponse.model_rebuild()
