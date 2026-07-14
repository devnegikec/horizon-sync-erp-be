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

        Resolves user_email from identity DB.
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

        dicts = [self._row_to_dict(row) for row in rows]

        # Batch-resolve user names and org names from identity DB
        user_ids = list({str(d["user_id"]) for d in dicts if d["user_id"]})
        org_ids = list({str(d["organization_id"]) for d in dicts if d["organization_id"]})
        user_map = self._resolve_user_names(user_ids)
        org_map = self._resolve_org_names(org_ids)
        for d in dicts:
            uid = str(d["user_id"]) if d["user_id"] else None
            oid = str(d["organization_id"]) if d["organization_id"] else None
            user_info = user_map.get(uid, {}) if uid else {}
            d["user_email"] = user_info.get("name") or user_info.get("email") if user_info else None
            d["user_name"] = user_info.get("name") if user_info else None
            d["user_email_address"] = user_info.get("email") if user_info else None
            d["organization_name"] = org_map.get(oid) if oid else None

        return dicts, total

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
            "user_email": None,
            "organization_name": None,
        }

    @staticmethod
    def _resolve_user_names(user_ids: list[str]) -> dict[str, dict]:
        """Batch-resolve user_id → {name, email} from identity DB."""
        import logging
        logger = logging.getLogger(__name__)

        if not user_ids:
            return {}
        try:
            from app.config import settings
            if not settings.identity_database_url:
                logger.warning("IDENTITY_DATABASE_URL not configured")
                return {}
            from sqlalchemy import create_engine
            engine = create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)
            placeholders = ", ".join(f"'{uid}'" for uid in user_ids)
            with engine.connect() as conn:
                rows = conn.execute(
                    text(f"SELECT id::text, first_name, last_name, email FROM users WHERE id::text IN ({placeholders})")
                ).fetchall()
                result = {}
                for r in rows:
                    name = f"{r[1] or ''} {r[2] or ''}".strip()
                    result[r[0]] = {"name": name, "email": r[3]}
                logger.info(f"Resolved {len(result)} user names from {len(user_ids)} user_ids")
                return result
        except Exception as e:
            logger.error(f"Failed to resolve user names: {e}")
            return {}

    @staticmethod
    def _resolve_org_names(org_ids: list[str]) -> dict[str, str]:
        """Batch-resolve organization_id → name from identity DB."""
        if not org_ids:
            return {}
        try:
            from app.config import settings
            if not settings.identity_database_url:
                return {}
            from sqlalchemy import create_engine
            engine = create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)
            placeholders = ", ".join(f"'{oid}'" for oid in org_ids)
            with engine.connect() as conn:
                rows = conn.execute(
                    text(f"SELECT id::text, name FROM organizations WHERE id::text IN ({placeholders})")
                ).fetchall()
                return {r[0]: r[1] for r in rows}
        except Exception:
            return {}
