"""Audit logger service for tracking account changes"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.account_audit_log import AccountAuditLog, AuditAction


class AuditLogger:
    """Service for logging account changes for compliance"""

    def __init__(self, db: Session):
        self.db = db

    def log_account_change(
        self,
        account_id: UUID,
        action: AuditAction,
        user_id: str,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AccountAuditLog:
        """
        Log an account change with before/after values.

        Args:
            account_id: UUID of the account being changed
            action: Type of action (CREATE, UPDATE, DELETE, STATUS_CHANGE)
            user_id: ID of the user making the change
            old_values: Dictionary of field values before the change
            new_values: Dictionary of field values after the change
            metadata: Additional metadata about the change

        Returns:
            Created AccountAuditLog entry
        """
        # Build changes dictionary with old and new values
        changes = {}

        if action == AuditAction.CREATE:
            # For CREATE, only new values matter
            changes = {"new": new_values or {}}
        elif action == AuditAction.DELETE:
            # For DELETE, only old values matter
            changes = {"old": old_values or {}}
        else:
            # For UPDATE and STATUS_CHANGE, capture both old and new
            changes = self._build_changes_dict(old_values or {}, new_values or {})

        # Create audit log entry
        audit_entry = AccountAuditLog(
            account_id=account_id,
            action=action.value,
            user_id=user_id,
            timestamp=datetime.now(UTC),
            changes=changes,
            audit_metadata=metadata,
        )

        self.db.add(audit_entry)
        self.db.flush()

        return audit_entry

    def _build_changes_dict(
        self, old_values: dict[str, Any], new_values: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """
        Build a changes dictionary showing only fields that changed.

        Args:
            old_values: Dictionary of old field values
            new_values: Dictionary of new field values

        Returns:
            Dictionary mapping field names to {oldValue, newValue} dicts
        """
        changes = {}

        # Get all unique field names from both dictionaries
        all_fields = set(old_values.keys()) | set(new_values.keys())

        for field in all_fields:
            old_val = old_values.get(field)
            new_val = new_values.get(field)

            # Only include fields that actually changed
            if old_val != new_val:
                changes[field] = {
                    "oldValue": self._serialize_value(old_val),
                    "newValue": self._serialize_value(new_val),
                }

        return changes

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize a value for JSON storage.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "value"):  # Enum
            return value.value
        return value

    def get_audit_trail(
        self,
        account_id: UUID,
        action_filter: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AccountAuditLog]:
        """
        Get audit trail for an account with optional filtering.

        Args:
            account_id: UUID of the account
            action_filter: Optional filter by action type
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of entries to return
            offset: Number of entries to skip (for pagination)

        Returns:
            List of audit log entries ordered by timestamp (newest first)
        """
        query = self.db.query(AccountAuditLog).filter(
            AccountAuditLog.account_id == account_id
        )

        # Apply filters
        if action_filter:
            query = query.filter(AccountAuditLog.action == action_filter)

        if start_date:
            query = query.filter(AccountAuditLog.timestamp >= start_date)

        if end_date:
            query = query.filter(AccountAuditLog.timestamp <= end_date)

        # Order by timestamp descending (newest first)
        query = query.order_by(desc(AccountAuditLog.timestamp))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        return query.all()

    def get_audit_count(
        self,
        account_id: UUID,
        action_filter: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Get count of audit entries for pagination.

        Args:
            account_id: UUID of the account
            action_filter: Optional filter by action type
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Total count of matching audit entries
        """
        query = self.db.query(AccountAuditLog).filter(
            AccountAuditLog.account_id == account_id
        )

        if action_filter:
            query = query.filter(AccountAuditLog.action == action_filter)

        if start_date:
            query = query.filter(AccountAuditLog.timestamp >= start_date)

        if end_date:
            query = query.filter(AccountAuditLog.timestamp <= end_date)

        return query.count()
