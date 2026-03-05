"""Journal entry schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class JournalEntryLineBase(BaseModel):
    account_id: UUID
    debit: Decimal | float = 0
    credit: Decimal | float = 0
    against_account_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    remarks: str | None = None
    sort_order: int = 0


class JournalEntryLineCreate(JournalEntryLineBase):
    pass


class JournalEntryBase(BaseModel):
    entry_no: str = Field(..., min_length=1, max_length=100)
    posting_date: datetime
    status: str = Field(default="draft", pattern="^(draft|posted|cancelled)$")
    voucher_type: str | None = Field(None, max_length=50)
    reference_type: str | None = None
    reference_id: UUID | None = None
    total_debit: Decimal | float = 0
    total_credit: Decimal | float = 0
    remarks: str | None = None


class JournalEntryCreate(JournalEntryBase):
    lines: list[JournalEntryLineCreate] = Field(default_factory=list)


class JournalEntryUpdate(BaseModel):
    posting_date: datetime | None = None
    status: str | None = Field(None, pattern="^(draft|posted|cancelled)$")
    remarks: str | None = None


class JournalEntryResponse(JournalEntryBase):
    id: UUID
    organization_id: UUID
    posted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JournalEntryLineResponse(BaseModel):
    id: UUID
    account_id: UUID
    account_code: str | None = None
    account_name: str | None = None
    debit: Decimal
    credit: Decimal
    remarks: str | None = None
    model_config = ConfigDict(from_attributes=True)


class JournalEntryListItem(BaseModel):
    id: UUID
    organization_id: UUID
    entry_no: str
    status: str
    posting_date: datetime
    voucher_type: str | None = None
    total_debit: Decimal
    total_credit: Decimal
    remarks: str | None = None
    lines: list[JournalEntryLineResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JournalEntryListResponse(BaseModel):
    journal_entries: list[JournalEntryListItem]
    pagination: PaginationMeta
