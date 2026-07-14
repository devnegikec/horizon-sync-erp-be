"""Repository for user activity log operations.

Uses SQLAlchemy ORM for the UserActivityLog model (core-service owned table).
Joins to users and organizations tables via raw SQL for display fields.
"""

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.admin import UserActivityLog


class UserActivityLogRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Create ───────────────────────────────────────────────────────

    def create(self, data: dict) -> dict:
        """Insert a new activity log entry and return it as a dict."""
        entry = UserActivityLog(
            id=uuid.uuid4(),
            user_id=data["user_id"],
            organization_id=data["organization_id"],
            action=data["action"],
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            metadata_=data.get("metadata"),
        )
        self.db.add(entry)
        self.db.flush()
        return self._to_dict(entry)

    # ── List with filters ────────────────────────────────────────────

    def list_activity_logs(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Return paginated activity logs with optional filters.

        Joins to users and organizations for display fields.
        Returns (rows_as_dicts, total_count).
        """
        where_clauses: list[str] = ["1=1"]
        params: dict = {}

        if user_id:
            where_clauses.append("al.user_id = :user_id")
            params["user_id"] = user_id

        if organization_id:
            where_clauses.append("al.organization_id = :organization_id")
            params["organization_id"] = organization_id

        if action:
            where_clauses.append("al.action = :action")
            params["action"] = action

        if date_from:
            where_clauses.append("al.created_at >= :date_from")
            params["date_from"] = date_from

        if date_to:
            where_clauses.append("al.created_at <= :date_to")
            params["date_to"] = date_to

        where_sql = " AND ".join(where_clauses)

        # Count
        count_row = self.db.execute(
            text(
                f"SELECT COUNT(*)::int AS total FROM user_activity_logs al WHERE {where_sql}"
            ),
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
                       al.resource_type, al.resource_id, al.ip_address,
                       al.user_agent, al.metadata, al.created_at,
                       u.email AS user_email,
                       o.name AS organization_name
                FROM user_activity_logs al
                LEFT JOIN users u ON u.id = al.user_id
                LEFT JOIN organizations o ON o.id = al.organization_id
                WHERE {where_sql}
                ORDER BY al.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        return [self._row_to_dict(row) for row in rows], total

    # ── Login history ────────────────────────────────────────────────

    def get_login_history(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Return login and login_failed entries for a specific user."""
        params: dict = {"user_id": user_id}

        count_row = self.db.execute(
            text(
                "SELECT COUNT(*)::int AS total FROM user_activity_logs "
                "WHERE user_id = :user_id AND action IN ('login', 'login_failed')"
            ),
            params,
        ).one()
        total = count_row.total

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                """
                SELECT al.id, al.user_id, al.organization_id, al.action,
                       al.resource_type, al.resource_id, al.ip_address,
                       al.user_agent, al.metadata, al.created_at,
                       u.email AS user_email,
                       o.name AS organization_name
                FROM user_activity_logs al
                LEFT JOIN users u ON u.id = al.user_id
                LEFT JOIN organizations o ON o.id = al.organization_id
                WHERE al.user_id = :user_id
                  AND al.action IN ('login', 'login_failed')
                ORDER BY al.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        return [self._row_to_dict(row) for row in rows], total

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(entry: UserActivityLog) -> dict:
        return {
            "id": entry.id,
            "user_id": entry.user_id,
            "organization_id": entry.organization_id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "ip_address": entry.ip_address,
            "user_agent": entry.user_agent,
            "metadata": entry.metadata_,
            "created_at": entry.created_at,
        }

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "organization_id": row.organization_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "metadata": row.metadata,
            "created_at": row.created_at,
            "user_email": row.user_email,
            "organization_name": row.organization_name,
        }
