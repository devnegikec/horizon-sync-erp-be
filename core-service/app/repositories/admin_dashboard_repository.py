"""Repository for admin dashboard aggregation queries.

Queries core_db tables (invoices, payments, user_activity_logs)
cross-org (no org filter) to produce dashboard metrics.

Organization and user metrics are fetched from identity-service
via the service layer, not from this repository.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models.admin import UserActivityLog
from app.models.invoice import Invoice
from app.models.payment import Payment


def _safe_scalar(query, fallback=Decimal("0")):
    """Execute a scalar query, returning fallback if the underlying table
    does not exist (schema drift / migration pending).
    Rolls back the session so the failed transaction doesn't poison
    subsequent queries."""
    try:
        return query.scalar() or fallback
    except ProgrammingError as exc:
        if "does not exist" in str(exc).lower():
            # Rollback to clear the aborted transaction state
            if query.session and hasattr(query.session, "rollback"):
                query.session.rollback()
            return fallback
        raise


class AdminDashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Revenue metrics ──────────────────────────────────────────────

    def get_revenue_metrics(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Return total_invoiced, total_outstanding, total_received."""
        # Total invoiced (paid invoices)
        inv_q = self.db.query(
            func.coalesce(func.sum(Invoice.grand_total), Decimal("0")).label(
                "total_invoiced"
            )
        ).filter(Invoice.status == "paid")
        if date_from:
            inv_q = inv_q.filter(Invoice.posting_date >= date_from)
        if date_to:
            inv_q = inv_q.filter(Invoice.posting_date <= date_to)
        total_invoiced = _safe_scalar(inv_q)

        # Total outstanding (pending / partial / overdue)
        out_q = self.db.query(
            func.coalesce(func.sum(Invoice.outstanding_amount), Decimal("0")).label(
                "total_outstanding"
            )
        ).filter(Invoice.status.in_(["pending", "partial", "overdue"]))
        if date_from:
            out_q = out_q.filter(Invoice.posting_date >= date_from)
        if date_to:
            out_q = out_q.filter(Invoice.posting_date <= date_to)
        total_outstanding = _safe_scalar(out_q)

        # Total received (completed payments)
        pay_q = self.db.query(
            func.coalesce(func.sum(Payment.amount), Decimal("0")).label(
                "total_received"
            )
        ).filter(Payment.status == "completed")
        if date_from:
            pay_q = pay_q.filter(Payment.posting_date >= date_from)
        if date_to:
            pay_q = pay_q.filter(Payment.posting_date <= date_to)
        total_received = _safe_scalar(pay_q)

        return {
            "total_invoiced": total_invoiced,
            "total_outstanding": total_outstanding,
            "total_received": total_received,
        }

    # ── Recent activity ──────────────────────────────────────────────

    def get_recent_activity(
        self,
        limit: int = 10,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[UserActivityLog]:
        """Return the most recent activity log entries, sorted by created_at desc.
        Returns empty list if the table does not exist (schema drift)."""
        q = self.db.query(UserActivityLog)
        if date_from:
            q = q.filter(UserActivityLog.created_at >= date_from)
        if date_to:
            q = q.filter(UserActivityLog.created_at <= date_to)
        try:
            return q.order_by(UserActivityLog.created_at.desc()).limit(limit).all()
        except ProgrammingError as exc:
            if "does not exist" in str(exc).lower():
                if self.db and hasattr(self.db, "rollback"):
                    self.db.rollback()
                return []
            raise
