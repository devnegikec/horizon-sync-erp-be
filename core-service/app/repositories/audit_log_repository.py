"""Repository for audit log queries.

Uses raw SQL with text() and LEFT JOIN to users table for user_email,
following the same pattern as user_activity_log_repository.py.
"""

import json
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_audit_logs(
        self,
        organization_id: uuid.UUID | None = None,
        table_name: str | None = None,
        record_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        changed_field: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Return paginated audit logs with optional filters.

        Joins to users table for user_email.
        Returns (rows_as_dicts, total_count).
        """
        where_clauses: list[str] = ["1=1"]
        params: dict = {}

        if organization_id:
            where_clauses.append("al.organization_id = :organization_id")
            params["organization_id"] = organization_id

        if table_name:
            where_clauses.append("al.table_name = :table_name")
            params["table_name"] = table_name

        if record_id:
            where_clauses.append("al.record_id = :record_id")
            params["record_id"] = record_id

        if user_id:
            where_clauses.append("al.user_id = :user_id")
            params["user_id"] = user_id

        if action:
            where_clauses.append("al.action = :action")
            params["action"] = action

        if date_from:
            where_clauses.append("al.created_at >= :date_from")
            params["date_from"] = date_from

        if date_to:
            where_clauses.append("al.created_at <= :date_to")
            params["date_to"] = date_to

        if changed_field:
            where_clauses.append("al.changed_fields @> :changed_field_json::jsonb")
            params["changed_field_json"] = json.dumps([changed_field])

        where_sql = " AND ".join(where_clauses)

        # Count
        count_row = self.db.execute(
            text(f"SELECT COUNT(*)::int AS total FROM audit_logs al WHERE {where_sql}"),
            params,
        ).one()
        total = count_row.total

        # Data
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                f"""
                SELECT al.id, al.user_id, al.organization_id, al.action,
                       al.table_name, al.record_id, al.old_values, al.new_values,
                       al.changed_fields, al.ip_address, al.created_at
                FROM audit_logs al
                WHERE {where_sql}
                ORDER BY al.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        return [self._row_to_dict(row) for row in rows], total

    def get_record_history(
        self,
        table_name: str,
        record_id: uuid.UUID,
        organization_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Return paginated change history for a specific record."""
        where_clauses: list[str] = [
            "al.table_name = :table_name",
            "al.record_id = :record_id",
        ]
        params: dict = {"table_name": table_name, "record_id": record_id}

        if organization_id:
            where_clauses.append("al.organization_id = :organization_id")
            params["organization_id"] = organization_id

        where_sql = " AND ".join(where_clauses)

        count_row = self.db.execute(
            text(f"SELECT COUNT(*)::int AS total FROM audit_logs al WHERE {where_sql}"),
            params,
        ).one()
        total = count_row.total

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                f"""
                SELECT al.id, al.user_id, al.organization_id, al.action,
                       al.table_name, al.record_id, al.old_values, al.new_values,
                       al.changed_fields, al.ip_address, al.created_at
                FROM audit_logs al
                WHERE {where_sql}
                ORDER BY al.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        return [self._row_to_dict(row) for row in rows], total

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "organization_id": row.organization_id,
            "action": row.action,
            "table_name": row.table_name,
            "record_id": row.record_id,
            "old_values": row.old_values,
            "new_values": row.new_values,
            "changed_fields": row.changed_fields,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
            "user_email": None,  # users table lives in identity_db; resolve via API if needed
        }
