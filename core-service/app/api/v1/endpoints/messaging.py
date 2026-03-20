"""Messaging module endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.messaging import (
    BulkMessageJobCreate,
    BulkMessageJobResponse,
    MessageCreditResponse,
    MessageCreditSummary,
    MessageTemplateCreate,
    MessageTemplateListResponse,
    MessageTemplateResponse,
    MessageTemplateUpdate,
    RCSSendRequest,
    RCSSendResponse,
    ScheduledMessageCreate,
    ScheduledMessageResponse,
    SMSWebhookPayload,
    WhatsAppSendRequest,
    WhatsAppSendResponse,
    WhatsAppWebhookPayload,
)
from app.services.messaging_service import MessagingService
from app.api.deps import get_current_user

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> MessagingService:
    return MessagingService(db)


# ── Message Templates ─────────────────────────────────────────────────────────

@router.post(
    "/templates",
    response_model=MessageTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create message template",
)
def create_template(
    data: MessageTemplateCreate,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.create_template(data, org_id, user_id)


@router.get(
    "/templates",
    response_model=MessageTemplateListResponse,
    summary="List message templates",
)
def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel: str | None = Query(None, description="Filter by channel: sms|whatsapp|rcs|email"),
    search: str | None = Query(None),
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_templates(org_id, page, page_size, channel, search)


@router.get(
    "/templates/{template_id}",
    response_model=MessageTemplateResponse,
    summary="Get message template",
)
def get_template(
    template_id: UUID,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    tmpl = service.get_template(template_id, org_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.patch(
    "/templates/{template_id}",
    response_model=MessageTemplateResponse,
    summary="Update message template",
)
def update_template(
    template_id: UUID,
    data: MessageTemplateUpdate,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    tmpl = service.update_template(template_id, data, org_id, user_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete message template",
)
def delete_template(
    template_id: UUID,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    if not service.delete_template(template_id, org_id, user_id):
        raise HTTPException(status_code=404, detail="Template not found")


# ── Bulk Message Jobs ─────────────────────────────────────────────────────────

@router.post(
    "/jobs",
    response_model=BulkMessageJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create bulk message job",
)
def create_bulk_job(
    data: BulkMessageJobCreate,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.create_bulk_job(data, org_id, user_id)


@router.get(
    "/jobs",
    summary="List bulk message jobs",
)
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    message_type: str | None = Query(None),
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_jobs(org_id, page, page_size, message_type)


@router.get(
    "/jobs/{job_id}",
    response_model=BulkMessageJobResponse,
    summary="Get bulk message job",
)
def get_job(
    job_id: UUID,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    job = service.get_job(job_id, org_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Scheduled Messages ────────────────────────────────────────────────────────

@router.post(
    "/scheduled",
    response_model=ScheduledMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a message",
)
def create_scheduled_message(
    data: ScheduledMessageCreate,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.create_scheduled_message(data, org_id, user_id)


@router.get(
    "/scheduled",
    summary="List scheduled messages",
)
def list_scheduled(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_scheduled(org_id, page, page_size)


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@router.post(
    "/whatsapp/send",
    response_model=WhatsAppSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send WhatsApp message",
)
def send_whatsapp(
    data: WhatsAppSendRequest,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.send_whatsapp(data, org_id, user_id)


@router.post(
    "/whatsapp/webhook",
    summary="WhatsApp delivery webhook (no auth)",
    include_in_schema=True,
)
def whatsapp_webhook(payload: WhatsAppWebhookPayload, service: MessagingService = Depends(get_service)):
    """Receives delivery status updates from WhatsApp provider."""
    result = service.handle_whatsapp_webhook(payload)
    return result


# ── SMS ───────────────────────────────────────────────────────────────────────

@router.post(
    "/sms/webhook",
    summary="SMS delivery webhook (no auth)",
    include_in_schema=True,
)
def sms_webhook(payload: SMSWebhookPayload, service: MessagingService = Depends(get_service)):
    """Receives delivery status updates from SMS provider."""
    result = service.handle_sms_webhook(payload)
    return result


# ── RCS ───────────────────────────────────────────────────────────────────────

@router.post(
    "/rcs/send",
    response_model=RCSSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send RCS message",
)
def send_rcs(
    data: RCSSendRequest,
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.send_rcs(data, org_id, user_id)


# ── Credits ───────────────────────────────────────────────────────────────────

@router.get(
    "/credits",
    response_model=list[MessageCreditSummary],
    summary="Get credit summary (all types)",
)
def get_credit_summary(
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_credit_summary(org_id)


@router.get(
    "/credits/balance",
    summary="Get credit balance for a specific type",
)
def get_credit_balance(
    credit_type: str = Query(..., description="sms|whatsapp|rcs"),
    service: MessagingService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    balance = service.get_credit_balance(org_id, credit_type)
    return {"credit_type": credit_type, "balance_credit": balance}
