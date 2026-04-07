"""Pydantic schemas for audit log API responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import PaginationMeta


class AuditLogListItem(BaseModel):
    """Single audit log entry in a paginated list."""

    id: UUID
    user_id: UUID | None
    organization_id: UUID | None
    action: str
    table_name: str
    record_id: UUID
    old_values: dict | None
    new_values: dict | None
    changed_fields: list[str] | None
    ip_address: str | None
    created_at: datetime
    user_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChangeDiffEntry(BaseModel):
    """A single field-level diff entry."""

    field: str
    old_value: Any
    new_value: Any


class AuditLogDetail(AuditLogListItem):
    """Audit log entry with computed change diff."""

    change_diff: list[ChangeDiffEntry] | None = None

    @model_validator(mode="after")
    def compute_diff(self):
        if self.old_values and self.new_values and self.changed_fields:
            self.change_diff = [
                ChangeDiffEntry(
                    field=f,
                    old_value=self.old_values.get(f),
                    new_value=self.new_values.get(f),
                )
                for f in self.changed_fields
            ]
        return self


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    audit_logs: list[AuditLogListItem]
    pagination: PaginationMeta


class AuditLogHistoryResponse(BaseModel):
    """Record change history response."""

    record_id: UUID
    table_name: str
    history: list[AuditLogDetail]
    pagination: PaginationMeta
