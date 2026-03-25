"""Thin admin service layer for cross-org invoice management.

Reuses existing InvoiceService for create, get_by_id, and send logic.
Adds cross-org list/detail methods that query without org-scoping and
resolve organization_name from the identity DB (separate database).
"""

import logging
import math
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.invoice import Invoice
from app.schemas.admin_invoice import (
    AdminInvoiceListItem,
    AdminInvoiceListResponse,
    AdminInvoiceStatsResponse,
)
from app.schemas.common import PaginationMeta
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)

# ── Identity DB engine (organizations live there, not in core DB) ────
_identity_engine = None


def _get_identity_engine():
    global _identity_engine
    if _identity_engine is None and settings.identity_database_url:
        _identity_engine = create_engine(
            settings.identity_database_url, pool_size=2, max_overflow=0
        )
    return _identity_engine


class AdminInvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(
        self, organization_id: UUID | None = None
    ) -> AdminInvoiceStatsResponse:
        """Return aggregated invoice statistics, optionally scoped to one org."""
        where_clauses: list[str] = ["1=1"]
        params: dict = {}

        if organization_id:
            where_clauses.append("i.organization_id = :organization_id")
            params["organization_id"] = organization_id

        where_sql = " AND ".join(where_clauses)

        row = self.db.execute(
            text(
                f"""
                SELECT
                    COUNT(*)::int AS total_invoices,
                    COUNT(*) FILTER (
                        WHERE i.due_date < NOW()
                          AND i.status IN ('pending', 'partial')
                    )::int AS overdue_invoices,
                    COALESCE(SUM(i.outstanding_amount), 0) AS total_outstanding,
                    COALESCE(
                        SUM(i.outstanding_amount) FILTER (
                            WHERE i.due_date < NOW()
                              AND i.status IN ('pending', 'partial')
                        ), 0
                    ) AS total_overdue_amount
                FROM invoices i
                WHERE {where_sql}
                """
            ),
            params,
        ).one()

        return AdminInvoiceStatsResponse(
            total_invoices=row.total_invoices,
            overdue_invoices=row.overdue_invoices,
            total_outstanding=row.total_outstanding,
            total_overdue_amount=row.total_overdue_amount,
        )

    # ── Cross-org list ───────────────────────────────────────────────

    def list_invoices(
        self,
        organization_id: UUID | None = None,
        status_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminInvoiceListResponse:
        """List invoices across all organizations with optional filters."""
        where_clauses: list[str] = ["1=1"]
        params: dict = {}

        if organization_id:
            where_clauses.append("i.organization_id = :organization_id")
            params["organization_id"] = organization_id

        if status_filter:
            where_clauses.append("i.status = :status")
            params["status"] = status_filter

        if date_from:
            where_clauses.append("i.posting_date >= :date_from")
            params["date_from"] = date_from

        if date_to:
            where_clauses.append("i.posting_date <= :date_to")
            params["date_to"] = date_to

        where_sql = " AND ".join(where_clauses)

        # Count
        count_row = self.db.execute(
            text(f"SELECT COUNT(*)::int AS total FROM invoices i WHERE {where_sql}"),
            params,
        ).one()
        total = count_row.total

        # Data — no JOIN to organizations (different DB)
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                f"""
                SELECT i.id, i.organization_id,
                       i.invoice_no, i.invoice_type, i.party_id, i.party_type,
                       i.status, i.posting_date, i.due_date,
                       i.grand_total, i.outstanding_amount, i.created_at
                FROM invoices i
                WHERE {where_sql}
                ORDER BY i.posting_date DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        # Resolve org names from identity DB
        org_ids = list({str(row.organization_id) for row in rows if row.organization_id})
        org_name_map = self._resolve_org_names(org_ids)

        # Build party map for party_name/party_code
        party_map = self._build_cross_org_party_map(rows)

        invoices = [
            AdminInvoiceListItem(
                id=row.id,
                organization_id=row.organization_id,
                organization_name=org_name_map.get(str(row.organization_id)),
                invoice_no=row.invoice_no,
                invoice_type=row.invoice_type,
                party_id=row.party_id,
                party_name=party_map.get(row.party_id, {}).get("name"),
                party_code=party_map.get(row.party_id, {}).get("code"),
                status=row.status,
                posting_date=row.posting_date,
                due_date=row.due_date,
                grand_total=row.grand_total,
                outstanding_amount=row.outstanding_amount,
                created_at=row.created_at,
            )
            for row in rows
        ]

        total_pages = max(1, math.ceil(total / page_size))
        return AdminInvoiceListResponse(
            invoices=invoices,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    # ── Cross-org detail ─────────────────────────────────────────────

    def get_invoice(self, invoice_id: UUID) -> dict:
        """Get invoice detail without org restriction.

        Queries the invoice directly (no org filter), then delegates to
        InvoiceService._to_response for the full response with line items
        and party details.
        """
        inv = (
            self.db.query(Invoice)
            .options(joinedload(Invoice.items))
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )
        response = self.invoice_service._to_response(inv)

        # Add organization_name from identity DB
        org_name_map = self._resolve_org_names([str(inv.organization_id)])
        response["organization_name"] = org_name_map.get(str(inv.organization_id))

        return response

    # ── Create (delegate) ────────────────────────────────────────────

    def create_invoice(
        self, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        """Create an invoice in the specified organization.

        Delegates entirely to existing InvoiceService.create.
        """
        return self.invoice_service.create(data, organization_id, user_id)

    # ── Send (delegate) ──────────────────────────────────────────────

    async def send_invoice(
        self, invoice_id: UUID, user_id: UUID
    ) -> dict:
        """Send an invoice via email and update status to pending.

        Fetches the invoice without org restriction, resolves the party
        email, delegates to CommunicationService.send_email, and updates
        the invoice status.
        """
        from app.models.customer import Customer
        from app.models.supplier import Supplier
        from app.services.communication_service import CommunicationService

        inv = (
            self.db.query(Invoice)
            .options(joinedload(Invoice.items))
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        # Resolve party email
        party_email: str | None = None
        party_name: str | None = None
        party_type = (inv.party_type or "").lower()

        if party_type == "customer" and inv.party_id:
            customer = self.db.query(Customer).filter(Customer.id == inv.party_id).first()
            if customer:
                party_email = customer.email
                party_name = customer.customer_name
        elif party_type == "supplier" and inv.party_id:
            supplier = self.db.query(Supplier).filter(Supplier.id == inv.party_id).first()
            if supplier:
                party_email = supplier.email
                party_name = supplier.supplier_name

        if not party_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Party email not found — cannot send invoice",
            )

        # Send via communication service
        comm_service = CommunicationService(self.db)
        result = await comm_service.send_email(
            to=party_email,
            subject=f"Invoice {inv.invoice_no}",
            message=f"Please find attached invoice {inv.invoice_no} for {party_name or 'your account'}.",
            organization_id=inv.organization_id,
            user_id=user_id,
            doc_type="invoice",
            doc_id=str(inv.id),
            doc_no=inv.invoice_no,
        )

        # Update invoice status to pending
        from app.models.base import InvoiceStatus

        inv.status = InvoiceStatus.PENDING
        self.db.commit()
        self.db.refresh(inv)

        return {
            "invoice_id": str(inv.id),
            "status": "pending",
            "communication": result,
        }

    # ── Send Reminder ────────────────────────────────────────────────

    async def send_reminder(
        self, invoice_id: UUID, email_data, user_id: UUID
    ) -> dict:
        """Send an overdue payment reminder email for an invoice.

        Validates the invoice is overdue (due_date < today AND status in
        ('pending', 'partial')), then delegates to CommunicationService.
        """
        from datetime import date

        from app.services.communication_service import CommunicationService

        inv = (
            self.db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        # Validate overdue: due_date < today AND status in ('pending', 'partial')
        if (
            inv.due_date is None
            or inv.due_date >= date.today()
            or inv.status not in ("pending", "partial")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice is not overdue",
            )

        # Send via CommunicationService
        comm_service = CommunicationService(self.db)
        result = await comm_service.send_email(
            to=email_data.to,
            subject=email_data.subject,
            message=email_data.body,
            organization_id=inv.organization_id,
            user_id=user_id,
            doc_type="invoice",
            doc_id=str(inv.id),
            doc_no=inv.invoice_no,
        )

        return {
            "invoice_id": str(inv.id),
            "status": "reminder_sent",
            "communication": result,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    def _resolve_org_names(self, org_ids: list[str]) -> dict[str, str]:
        """Batch-resolve organization names from the identity DB."""
        if not org_ids:
            return {}
        engine = _get_identity_engine()
        if not engine:
            return {}
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id::text, name FROM organizations WHERE id::text = ANY(:ids)"),
                    {"ids": org_ids},
                )
                return {row[0]: row[1] for row in result}
        except Exception as e:
            logger.warning(f"Failed to resolve org names from identity DB: {e}")
            return {}

    def _build_cross_org_party_map(self, rows) -> dict:
        """Batch-load party name/code for a list of invoice rows."""
        from app.models.customer import Customer
        from app.models.supplier import Supplier

        customer_ids = set()
        supplier_ids = set()
        for row in rows:
            pt = (row.party_type or "").lower()
            if pt == "customer" and row.party_id:
                customer_ids.add(row.party_id)
            elif pt == "supplier" and row.party_id:
                supplier_ids.add(row.party_id)

        party_map: dict = {}
        if customer_ids:
            customers = (
                self.db.query(
                    Customer.id, Customer.customer_name, Customer.customer_code
                )
                .filter(Customer.id.in_(customer_ids))
                .all()
            )
            for c in customers:
                party_map[c.id] = {"name": c.customer_name, "code": c.customer_code}
        if supplier_ids:
            suppliers = (
                self.db.query(
                    Supplier.id, Supplier.supplier_name, Supplier.supplier_code
                )
                .filter(Supplier.id.in_(supplier_ids))
                .all()
            )
            for s in suppliers:
                party_map[s.id] = {"name": s.supplier_name, "code": s.supplier_code}
        return party_map
