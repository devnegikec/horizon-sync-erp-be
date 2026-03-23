"""Pydantic schemas for Messaging module"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Message Template ──────────────────────────────────────────────────────────

class MessageTemplateCreate(BaseModel):
    template_name: str = Field(..., max_length=4000)
    channel: str = Field(..., pattern="^(sms|whatsapp|rcs|email)$")
    template_text: str
    template_type: str | None = None
    message: str | None = None
    media_type: str | None = None
    interactive_type: str | None = None
    sender_id: str | None = None
    cta_button1: str | None = None
    cta_button2: str | None = None
    qr_button1: str | None = None
    qr_button2: str | None = None
    qr_button3: str | None = None
    entity_name: str | None = None
    dlt_principal_entity_id: str | None = None
    dlt_template_id: str | None = None
    mobtexting_template_id: str | None = None
    service_type: str = Field("T", pattern="^(T|P)$")
    extra_data: dict[str, Any] | None = None


class MessageTemplateUpdate(BaseModel):
    template_name: str | None = None
    template_text: str | None = None
    status: str | None = None
    sender_id: str | None = None
    dlt_template_id: str | None = None
    extra_data: dict[str, Any] | None = None


class MessageTemplateResponse(BaseModel):
    id: UUID
    organization_id: UUID
    template_name: str
    channel: str
    template_text: str
    status: str
    service_type: str
    sender_id: str | None
    dlt_template_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageTemplateListResponse(BaseModel):
    templates: list[MessageTemplateResponse]
    pagination: dict[str, Any]


# ── Bulk Message Job ──────────────────────────────────────────────────────────

class BulkMessageJobCreate(BaseModel):
    message_type: str = Field(..., pattern="^(sms|whatsapp|rcs)$")
    template_name: str | None = None
    message_template: str | None = None
    sender_id: str | None = None
    tag_id: UUID | None = None
    variable: dict[str, Any] | None = None
    media_link: str | None = None
    coupon_type: str | None = None
    coupon_value: str | None = None
    extra_data: dict[str, Any] | None = None


class BulkMessageJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    message_type: str
    template_name: str | None
    status: str | None
    total_lead: str | None
    used_credit: str | None
    created_at: date

    model_config = {"from_attributes": True}


# ── Scheduled Message ─────────────────────────────────────────────────────────

class ScheduledMessageCreate(BaseModel):
    message_type: str = Field(..., pattern="^(sms|whatsapp|rcs)$")
    schedule: datetime
    template_name: str | None = None
    template_text: str | None = None
    variable: dict[str, Any] | None = None
    sender_id: str | None = None
    media_link: str | None = None
    tag_id: UUID | None = None
    extra_data: dict[str, Any] | None = None


class ScheduledMessageResponse(BaseModel):
    id: UUID
    organization_id: UUID
    message_type: str
    template_name: str | None
    schedule: datetime
    status: str
    created_at: date

    model_config = {"from_attributes": True}


# ── WhatsApp Send ─────────────────────────────────────────────────────────────

class WhatsAppSendRequest(BaseModel):
    recipient_number: str = Field(..., description="E.164 format, e.g. +919876543210")
    template_name: str
    template_type: str | None = None
    media_type: str | None = None
    interactive_type: str | None = None
    variable: dict[str, Any] | None = None
    media_link: str | None = None
    sender_number: str | None = None


class WhatsAppSendResponse(BaseModel):
    success: bool
    message_id: str | None
    status: str
    message: str


# ── WhatsApp Webhook ──────────────────────────────────────────────────────────

class WhatsAppWebhookPayload(BaseModel):
    guid: str | None = None
    whatsapp_msg_id: str | None = None
    recipient_number: str | None = None
    status: str | None = None
    reason_code: str | None = None
    deliver_date: datetime | None = None
    extra_data: dict[str, Any] | None = None


# ── SMS Webhook ───────────────────────────────────────────────────────────────

class SMSWebhookPayload(BaseModel):
    msg_id: str | None = None
    recipient_number: str | None = None
    status: str | None = None
    deliver_date: datetime | None = None
    extra_data: dict[str, Any] | None = None


# ── RCS Send ──────────────────────────────────────────────────────────────────

class RCSSendRequest(BaseModel):
    recipient_number: str
    template_id: UUID
    variable: dict[str, Any] | None = None


class RCSSendResponse(BaseModel):
    success: bool
    guid: str | None
    status: str
    message: str


# ── Message Credits ───────────────────────────────────────────────────────────

class MessageCreditResponse(BaseModel):
    id: UUID
    organization_id: UUID
    credit_type: str
    add_credit: int
    reduce_credit: int
    balance_credit: int
    transaction_date: datetime

    model_config = {"from_attributes": True}


class MessageCreditSummary(BaseModel):
    credit_type: str
    balance_credit: int
