"""Payment schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class PaymentBase(BaseModel):
    payment_no: str = Field(..., min_length=1, max_length=100)
    payment_type: str = Field(..., pattern="^(receive|pay)$")
    party_id: UUID
    party_type: str = Field(..., min_length=1, max_length=20)
    posting_date: datetime
    amount: Decimal | float = Field(..., gt=0)
    status: str = Field(
        default="pending", pattern="^(pending|completed|failed|cancelled)$"
    )
    payment_method: str | None = Field(
        None, pattern="^(cash|bank_transfer|credit_card|debit_card|cheque|upi|other)$"
    )
    reference_no: str | None = Field(None, max_length=100)
    remarks: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    posting_date: datetime | None = None
    status: str | None = Field(None, pattern="^(pending|completed|failed|cancelled)$")
    remarks: str | None = None


class PaymentResponse(PaymentBase):
    id: UUID
    organization_id: UUID
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentListItem(BaseModel):
    id: UUID
    organization_id: UUID
    payment_no: str
    payment_type: str
    party_id: UUID
    status: str
    amount: Decimal
    posting_date: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentListResponse(BaseModel):
    payments: list[PaymentListItem]
    pagination: PaginationMeta
