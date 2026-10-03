"""API contracts for Organization QR-credit balances and ledger entries."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QRCreditBalanceResponse(BaseModel):
    organization_id: UUID
    total_credits: int
    used_credits: int
    reserved_credits: int = 0
    balance_credits: int
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class QRCreditAddRequest(BaseModel):
    amount: int = Field(..., ge=1, le=10_000_000)
    reason: str = Field(..., min_length=3, max_length=500)
    reference_id: UUID


class QRCreditLedgerItem(BaseModel):
    id: UUID
    organization_id: UUID
    block_id: UUID | None
    transaction_type: str
    amount: int
    balance_after: int
    reason: str | None
    created_by: UUID | None
    reference_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QRCreditLedgerResponse(BaseModel):
    transactions: list[QRCreditLedgerItem]
    pagination: dict
