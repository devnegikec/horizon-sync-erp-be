"""Schemas for the pick exception framework (PR-03 / T-02 + T-05)."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class PickExceptionCreate(BaseModel):
    """Body for capturing a new pick exception against a pick list item."""

    pick_list_item_id: UUID = Field(..., description="Pick list item to raise against")
    reason_code: str = Field(
        ..., description="Reason code from the tenant's pick.reason_codes master"
    )
    severity: str = Field(
        default="warning",
        pattern="^(info|warning|error|critical)$",
        description="Exception severity (info/warning/error/critical)",
    )
    quantity: Decimal | None = Field(
        default=None, description="Affected quantity, if applicable"
    )
    note: str | None = Field(default=None, max_length=4000)
    details: dict[str, Any] | None = Field(
        default=None, description="Free-form capture context (device, batch, …)"
    )


class PickExceptionAuditItem(BaseModel):
    """One append-only audit entry for a pick exception."""

    id: UUID
    exception_id: UUID
    event_type: str
    actor_id: UUID | None = None
    from_state: str | None = None
    to_state: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime


class PickExceptionResponse(BaseModel):
    """A pick exception with its audit event count."""

    id: UUID
    organization_id: UUID
    pick_list_id: UUID
    pick_list_item_id: UUID
    reason_code: str
    severity: str
    reported_by: UUID | None = None
    status: str
    resolution: str | None = None
    approver: UUID | None = None
    approved_at: datetime | None = None
    quantity: Decimal | None = None
    note: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class PickExceptionListResponse(BaseModel):
    """Paginated list of pick exceptions."""

    exceptions: list[PickExceptionResponse]
    pagination: PaginationMeta


class PickExceptionAuditResponse(BaseModel):
    """Immutable audit trail for one pick exception."""

    exception_id: UUID
    events: list[PickExceptionAuditItem]


class PickReasonCodesResponse(BaseModel):
    """Effective reason-code master for the current organization."""

    reason_codes: list[str]


class PickExceptionResolve(BaseModel):
    """Body for resolving a pick exception (supervisor)."""

    resolution: str = Field(..., min_length=1, max_length=4000)


class PickExceptionApprove(BaseModel):
    """Body for approving/rejecting a pick exception (supervisor)."""

    decision: str = Field(..., pattern="^(approved|rejected)$")
