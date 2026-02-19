"""Communication schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class CommunicationBase(BaseModel):
    doc_type: str = Field(
        ...,
        pattern="^(quotation|sales_order|purchase_order|invoice|delivery_note|purchase_receipt|payment|rfq|material_request)$",
    )
    doc_id: UUID
    doc_no: str | None = Field(None, max_length=100)
    version: int = Field(default=1, ge=1)
    channel: str = Field(..., pattern="^(email|whatsapp|sms|webhook)$")
    recipient_type: str | None = Field(
        None, pattern="^(customer|supplier|employee|other)$"
    )
    recipient: str = Field(..., min_length=1, max_length=255)
    recipient_name: str | None = Field(None, max_length=255)
    sender_name: str | None = Field(None, max_length=255)
    sender_email: str | None = Field(None, max_length=255)
    subject: str | None = Field(None, max_length=500)
    message: str | None = None
    metadata: dict | None = None


class CommunicationCreate(CommunicationBase):
    pass


class CommunicationResponse(CommunicationBase):
    id: UUID
    organization_id: UUID
    sender_id: UUID
    status: str
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CommunicationListItem(BaseModel):
    id: UUID
    organization_id: UUID
    doc_type: str
    doc_id: UUID
    doc_no: str | None
    version: int
    channel: str
    recipient_type: str | None
    recipient: str
    recipient_name: str | None
    status: str
    sent_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CommunicationListResponse(BaseModel):
    communications: list[CommunicationListItem]
    pagination: PaginationMeta


class CommunicationStatusUpdate(BaseModel):
    status: str = Field(
        ..., pattern="^(pending|sent|delivered|failed|bounced)$"
    )
    error_message: str | None = None
