"""Landed cost voucher schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class LandedCostVoucherBase(BaseModel):
    voucher_no: str = Field(..., min_length=1, max_length=100)
    posting_date: datetime
    status: str = Field(default="draft", pattern="^(draft|submitted|cancelled)$")
    remarks: str | None = None


class LandedCostVoucherCreate(LandedCostVoucherBase):
    pass


class LandedCostVoucherUpdate(BaseModel):
    posting_date: datetime | None = None
    status: str | None = Field(None, pattern="^(draft|submitted|cancelled)$")
    remarks: str | None = None


class LandedCostVoucherResponse(LandedCostVoucherBase):
    id: UUID
    organization_id: UUID
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LandedCostVoucherListItem(BaseModel):
    id: UUID
    organization_id: UUID
    voucher_no: str
    status: str
    posting_date: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LandedCostVoucherListResponse(BaseModel):
    vouchers: list[LandedCostVoucherListItem]
    pagination: PaginationMeta
