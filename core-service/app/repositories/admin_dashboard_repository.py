"""Repository for admin dashboard aggregation queries.

Queries core_db tables (invoices, payments, user_activity_logs)
cross-org (no org filter) to produce dashboard metrics.

Organization and user metrics are fetched from identity-service
via the service layer, not from this repository.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.admin import UserActivityLog
from app.models.invoice import Invoice
from app.models.payment import Payment


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
        total_invoiced = inv_q.scalar() or Decimal("0")

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
        total_outstanding = out_q.scalar() or Decimal("0")

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
        total_received = pay_q.scalar() or Decimal("0")

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
        """Return the most recent activity log entries, sorted by created_at desc."""
        q = self.db.query(UserActivityLog)
        if date_from:
            q = q.filter(UserActivityLog.created_at >= date_from)
        if date_to:
            q = q.filter(UserActivityLog.created_at <= date_to)
        return q.order_by(UserActivityLog.created_at.desc()).limit(limit).all()
