"""Communications API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import PaginationMeta
from app.schemas.communication import (
    CommunicationCreate,
    CommunicationListItem,
    CommunicationListResponse,
    CommunicationResponse,
    CommunicationStatusUpdate,
    SendEmailRequest,
    SendEmailResponse,
)
from app.services.communication_service import CommunicationService

router = APIRouter()


@router.post(
    "", response_model=CommunicationResponse, status_code=status.HTTP_201_CREATED
)
async def create_communication(
    body: CommunicationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a communication log entry.

    Records outgoing communications (email, SMS, WhatsApp, webhook) for documents
    like quotations, invoices, purchase orders, etc.
    """
    svc = CommunicationService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return CommunicationResponse.model_validate(data)


@router.get("", response_model=CommunicationListResponse)
async def list_communications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    doc_type: str | None = Query(
        None,
        pattern="^(quotation|sales_order|purchase_order|invoice|delivery_note|purchase_receipt|payment|rfq|material_request)$",
    ),
    doc_id: UUID | None = None,
    channel: str | None = Query(None, pattern="^(email|whatsapp|sms|webhook)$"),
    status: str | None = Query(
        None, pattern="^(pending|sent|delivered|failed|bounced)$"
    ),
    recipient_type: str | None = Query(
        None, pattern="^(customer|supplier|employee|other)$"
    ),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List communication logs with optional filters.

    Filter by document type, document ID, channel, status, or recipient type.
    """
    svc = CommunicationService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        doc_type=doc_type,
        doc_id=doc_id,
        channel=channel,
        status=status,
        recipient_type=recipient_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return CommunicationListResponse(
        communications=[CommunicationListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{communication_id}", response_model=CommunicationResponse)
async def get_communication(
    communication_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get communication log by ID."""
    svc = CommunicationService(db)
    data = svc.get_by_id(communication_id, current_user.organization_id)
    return CommunicationResponse.model_validate(data)


@router.patch("/{communication_id}/status", response_model=CommunicationResponse)
async def update_communication_status(
    communication_id: UUID,
    body: CommunicationStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update communication status.

    Used to track delivery status of sent communications.
    Typically called by webhook handlers or background jobs.
    """
    svc = CommunicationService(db)
    data = svc.update_status(
        communication_id,
        body.status,
        current_user.organization_id,
        body.error_message,
    )
    return CommunicationResponse.model_validate(data)


@router.delete("/{communication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_communication(
    communication_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete communication log."""
    svc = CommunicationService(db)
    svc.delete(communication_id, current_user.organization_id)
    return None



@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    body: SendEmailRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send an email with optional CC and attachments, and log the communication.

    This endpoint:
    1. Sends the email via SMTP
    2. Automatically logs the communication
    3. Returns the communication log ID for tracking

    Attachments should be provided as base64-encoded content.
    """
    svc = CommunicationService(db)
    result = await svc.send_email(
        to=body.to,
        subject=body.subject,
        message=body.message,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        cc=body.cc,
        html_message=body.html_message,
        attachments=body.attachments,
        doc_type=body.doc_type,
        doc_id=body.doc_id,
        doc_no=body.doc_no,
    )
    return SendEmailResponse(**result)
