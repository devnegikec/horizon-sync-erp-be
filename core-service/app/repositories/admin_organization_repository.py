"""Repository for admin organization management.

Uses raw SQL via sqlalchemy.text() for organizations and users tables
(owned by identity-service but sharing the same database).
Uses SQLAlchemy ORM for invoices and payments (core-service models).
"""

import math
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment


class AdminOrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── List with search, status filter, pagination ──────────────────

    def list_organizations(
        self,
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Return paginated list of organizations with optional filters.

        Returns (rows_as_dicts, total_count).
        """
        where_clauses: list[str] = ["deleted_at IS NULL"]
        params: dict = {}

        if search:
            where_clauses.append(
                "(LOWER(name) LIKE :search OR LOWER(slug) LIKE :search)"
            )
            params["search"] = f"%{search.lower()}%"

        if status:
            where_clauses.append("status = :status")
            params["status"] = status

        where_sql = " AND ".join(where_clauses)

        # Count
        count_row = self.db.execute(
            text(f"SELECT COUNT(*)::int AS total FROM organizations WHERE {where_sql}"),
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
                SELECT id, name, slug, display_name, status,
                       organization_type, is_active, created_at
                FROM organizations
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        orgs = [
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "display_name": row.display_name,
                "status": row.status,
                "organization_type": row.organization_type,
                "is_active": row.is_active,
                "created_at": row.created_at,
            }
            for row in rows
        ]
        return orgs, total

    # ── Get by ID with summary counts ────────────────────────────────

    def get_by_id(self, org_id: uuid.UUID) -> dict | None:
        """Return full organization record or None if not found."""
        row = self.db.execute(
            text(
                """
                SELECT id, name, slug, display_name, description,
                       email, phone, website,
                       address_line1, address_line2, city, state, postal_code, country,
                       organization_type, industry, base_currency,
                       logo_url, status, is_active, owner_id,
                       settings, extra_data, created_at, updated_at
                FROM organizations
                WHERE id = :org_id AND deleted_at IS NULL
                """
            ),
            {"org_id": org_id},
        ).first()
        if not row:
            return None
        return dict(row._mapping)

    def get_summary_counts(self, org_id: uuid.UUID) -> dict:
        """Return user_count, invoice_count, payment_total for an org."""
        # User count (raw SQL — users table owned by identity-service)
        user_row = self.db.execute(
            text(
                """
                SELECT COUNT(*)::int AS user_count
                FROM user_organization_roles
                WHERE organization_id = :org_id
                """
            ),
            {"org_id": org_id},
        ).one()

        # Invoice count (ORM)
        invoice_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.organization_id == org_id)
            .scalar()
        ) or 0

        # Payment total (ORM)
        payment_total = (
            self.db.query(func.coalesce(func.sum(Payment.amount), Decimal("0")))
            .filter(Payment.organization_id == org_id)
            .scalar()
        ) or Decimal("0")

        return {
            "user_count": user_row.user_count,
            "invoice_count": invoice_count,
            "payment_total": payment_total,
        }

    # ── Create ───────────────────────────────────────────────────────

    def create(self, data: dict) -> dict:
        """Insert a new organization and return the created record."""
        org_id = uuid.uuid4()
        columns = ["id"] + list(data.keys())
        placeholders = [":id"] + [f":{k}" for k in data.keys()]
        params = {"id": org_id, **data}

        self.db.execute(
            text(
                f"""
                INSERT INTO organizations ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                """
            ),
            params,
        )
        self.db.flush()
        return self.get_by_id(org_id)  # type: ignore

    # ── Check slug uniqueness ────────────────────────────────────────

    def slug_exists(self, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
        """Return True if an organization with this slug already exists."""
        sql = "SELECT COUNT(*)::int AS cnt FROM organizations WHERE slug = :slug AND deleted_at IS NULL"
        params: dict = {"slug": slug}
        if exclude_id:
            sql += " AND id != :exclude_id"
            params["exclude_id"] = exclude_id
        row = self.db.execute(text(sql), params).one()
        return row.cnt > 0

    # ── Update ───────────────────────────────────────────────────────

    def update(self, org_id: uuid.UUID, data: dict) -> dict | None:
        """Partially update an organization. Returns updated record."""
        if not data:
            return self.get_by_id(org_id)
        set_clauses = [f"{k} = :{k}" for k in data.keys()]
        set_clauses.append("updated_at = NOW()")
        params = {"org_id": org_id, **data}

        self.db.execute(
            text(
                f"""
                UPDATE organizations
                SET {', '.join(set_clauses)}
                WHERE id = :org_id AND deleted_at IS NULL
                """
            ),
            params,
        )
        self.db.flush()
        return self.get_by_id(org_id)

    # ── Deactivate all users (suspension cascade) ────────────────────

    def deactivate_all_users(self, org_id: uuid.UUID) -> int:
        """Set is_active=false for every user linked to this org.

        Returns the number of affected rows.
        """
        result = self.db.execute(
            text(
                """
                UPDATE users
                SET is_active = false, updated_at = NOW()
                WHERE id IN (
                    SELECT user_id FROM user_organization_roles
                    WHERE organization_id = :org_id
                )
                """
            ),
            {"org_id": org_id},
        )
        self.db.flush()
        return result.rowcount

    # ── Billing helpers ──────────────────────────────────────────────

    def get_billing_info(self, org_id: uuid.UUID) -> dict | None:
        """Return billing/subscription fields for an organization."""
        row = self.db.execute(
            text(
                """
                SELECT id, name, on_trial, trial_expiry, paid_until
                FROM organizations
                WHERE id = :org_id AND deleted_at IS NULL
                """
            ),
            {"org_id": org_id},
        ).first()
        if not row:
            return None

        # Financial aggregates via ORM
        total_invoiced = (
            self.db.query(func.coalesce(func.sum(Invoice.grand_total), Decimal("0")))
            .filter(Invoice.organization_id == org_id)
            .scalar()
        ) or Decimal("0")

        total_paid = (
            self.db.query(func.coalesce(func.sum(Payment.amount), Decimal("0")))
            .filter(
                Payment.organization_id == org_id,
                Payment.status == "completed",
            )
            .scalar()
        ) or Decimal("0")

        outstanding = total_invoiced - total_paid

        return {
            "organization_id": row.id,
            "organization_name": row.name,
            "on_trial": row.on_trial if row.on_trial is not None else False,
            "trial_expiry": row.trial_expiry,
            "paid_until": row.paid_until,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding": outstanding,
        }
