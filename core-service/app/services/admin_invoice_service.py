"""Thin admin service layer for cross-org invoice management.

Reuses existing InvoiceService for create, get_by_id, and send logic.
Adds cross-org list/detail methods that query without org-scoping and
join to organizations for organization_name.
Integrates SubscriptionInvoiceService for B2B billing (Task 1B-2).
"""

import math
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import logging

import httpx
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

from app.config import settings
from app.models.base import BillingCycle
from app.models.invoice import Invoice
from app.schemas.admin_invoice import (
    AdminInvoiceListItem,
    AdminInvoiceListResponse,
)
from app.schemas.common import PaginationMeta
from app.services.invoice_service import InvoiceService
from app.services.subscription_invoice_service import SubscriptionInvoiceService


class AdminInvoiceService:
    def __init__(self, db: Session, token: str | None = None):
        self.db = db
        self.token = token
        self.invoice_service = InvoiceService(db)
        self.subscription_service = SubscriptionInvoiceService(db)  # Task 1B-2

    async def _get_customer_organization_ids(self, master_org_id: UUID) -> list[UUID]:
        """Fetch customer organization IDs from identity service for the given master org."""
        logger.info(f"Fetching customer organizations for master org: {master_org_id}")
        
        if not self.token:
            logger.warning("No authentication token provided, falling back to master org only")
            return [master_org_id]  # Fallback to just master org
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{settings.identity_service_url}/api/v1/identity/organizations"
                params = {"parent_organization_id": str(master_org_id), "page_size": 1000}
                headers = {"Authorization": f"Bearer {self.token}"}
                
                logger.info(f"Making request to: {url} with params: {params}")
                
                response = await client.get(url, params=params, headers=headers)
                
                logger.info(f"Identity service response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Identity service response data: {data}")
                    
                    orgs_data = data.get("organizations", [])
                    customer_org_ids = [UUID(org["id"]) for org in orgs_data]
                    # Do NOT include master org itself - we only want customer invoices
                    
                    logger.info(f"Found {len(customer_org_ids)} customer organizations (excluding master): {customer_org_ids}")
                    return customer_org_ids
                else:
                    logger.error(f"Identity service returned status {response.status_code}: {response.text}")
                    return []  # Return empty list to show no invoices if API fails
        except Exception as e:
            logger.error(f"Error fetching customer organizations: {e}")
            return []  # Return empty list on error
            
    async def _get_organization_names(self, org_ids: list[UUID]) -> dict[UUID, str]:
        """Fetch organization names from identity service for given org IDs."""
        if not self.token or not org_ids:
            return {}
            
        try:
            org_names = {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fetch organizations in batches to get names
                url = f"{settings.identity_service_url}/api/v1/identity/organizations"
                headers = {"Authorization": f"Bearer {self.token}"}
                
                # Get all organizations (we'll filter by IDs)
                response = await client.get(url, params={"page_size": 1000}, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    orgs_data = data.get("organizations", [])
                    
                    for org in orgs_data:
                        org_id = UUID(org["id"])
                        if org_id in org_ids:
                            org_names[org_id] = org["name"]
                    
                    logger.info(f"Fetched names for {len(org_names)} organizations")
                    return org_names
                else:
                    logger.error(f"Failed to fetch organization names: {response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching organization names: {e}")
            return {}
            return [master_org_id]  # Fallback on error

    # ── Cross-org list ───────────────────────────────────────────────

    async def list_invoices(
        self,
        organization_id: UUID | None = None,
        status_filter: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
        current_user_org: UUID | None = None,
    ) -> AdminInvoiceListResponse:
        """List invoices across all organizations with optional filters.
        
        For system admin users from master organizations, only shows invoices
        from the master organization itself (not customer organizations).
        """
        where_clauses: list[str] = ["1=1"]
        params: dict = {}

        # Filter by master organization invoices only for system admins
        if current_user_org:
            where_clauses.append("i.organization_id = :master_org_id")
            params["master_org_id"] = str(current_user_org)
            logger.info(f"Filtering invoices by master organization only: {current_user_org}")
        else:
            logger.info("No current_user_org provided, showing all invoices")

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
        
        logger.info(f"Found {total} invoices matching filter criteria. Where clause: {where_sql}, Params: {params}")

        # Data with organization_name join
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                f"""
                SELECT i.id, i.organization_id, NULL AS organization_name,
                       i.invoice_no, i.invoice_type, i.party_id, i.party_type,
                       i.status, i.posting_date, i.due_date,
                       i.grand_total, i.outstanding_amount, i.created_at,
                       i.billing_cycle, i.subscription_period_start, i.subscription_period_end,
                       i.seat_count, i.credit_usage
                FROM invoices i
                WHERE {where_sql}
                ORDER BY i.posting_date DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        # Build party map for party_name/party_code
        party_map = self._build_cross_org_party_map(rows)
        
        # Fetch organization names from identity service
        org_ids = list(set(row.organization_id for row in rows))
        org_names = await self._get_organization_names(org_ids)

        invoices = [
            AdminInvoiceListItem(
                id=row.id,
                organization_id=row.organization_id,
                organization_name=org_names.get(row.organization_id, f"Organization {row.organization_id}"),
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
                # Subscription billing fields (Task 1B-1)
                billing_cycle=row.billing_cycle,
                subscription_period_start=row.subscription_period_start,
                subscription_period_end=row.subscription_period_end,
                seat_count=row.seat_count,
                credit_usage=row.credit_usage,
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

        # Add organization_name - TODO: Get from identity service
        response["organization_name"] = None  # Will need to fetch from identity service

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

    # ── Helpers ──────────────────────────────────────────────────────

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

    # ── Subscription Invoice Methods (Task 1B-2) ─────────────────────

    def create_subscription_invoice(
        self,
        organization_id: UUID,
        billing_cycle: str,
        seat_count: int,
        credit_usage: Decimal = Decimal("0"),
        base_price_per_seat: Decimal = Decimal("10.00"),
        credit_rate: Decimal = Decimal("0.01"),
        created_by: UUID | None = None
    ) -> dict:
        """Create subscription invoice for organization billing.
        
        Admin interface for creating subscription invoices with validation.
        """
        try:
            # Convert string to enum
            cycle_enum = BillingCycle(billing_cycle)
            
            # Delegate to SubscriptionInvoiceService
            return self.subscription_service.create_subscription_invoice(
                organization_id=organization_id,
                billing_cycle=cycle_enum,
                seat_count=seat_count,
                credit_usage=credit_usage,
                base_price_per_seat=base_price_per_seat,
                credit_rate=credit_rate,
                created_by=created_by
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def get_subscription_invoices_for_organization(
        self,
        organization_id: UUID,
        limit: int = 50
    ) -> list[dict]:
        """Get subscription invoices for organization (admin view)."""
        return self.subscription_service.get_subscription_invoices_for_organization(
            organization_id, limit
        )

    def get_overdue_subscription_invoices(self) -> list[dict]:
        """Get all overdue subscription invoices across organizations."""
        return self.subscription_service.get_overdue_subscription_invoices()

    def generate_bulk_subscription_invoices(
        self,
        billing_cycle: str,
        exclude_master_org: bool = True,
        created_by: UUID | None = None
    ) -> dict:
        """Generate subscription invoices for all eligible organizations.
        
        This method would typically be called on a schedule (monthly/quarterly/yearly)
        to generate subscription invoices for all customer organizations.
        """
        try:
            cycle_enum = BillingCycle(billing_cycle)
            
            # Get all customer organizations (would need to query identity service)
            # For now, return a placeholder response
            
            # TODO: Implement bulk generation by:
            # 1. Querying identity service for all customer organizations
            # 2. Getting their current seat counts and credit usage
            # 3. Creating subscription invoices for each eligible org
            # 4. Handling errors and reporting results
            
            return {
                "message": "Bulk subscription invoice generation not yet implemented",
                "billing_cycle": billing_cycle,
                "status": "pending_implementation"
            }
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid billing cycle: {e}"
            )

    def get_organization_billing_summary(
        self,
        organization_id: UUID,
        requested_by: UUID
    ) -> dict:
        """Get comprehensive billing summary for customer organization"""
        from app.models.organization import Organization
        
        # Get organization details
        org = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Get invoice statistics
        invoice_stats = self.db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_invoices,
                    COALESCE(SUM(grand_total), 0) as total_amount,
                    COALESCE(SUM(CASE WHEN status = 'paid' THEN grand_total ELSE 0 END), 0) as total_paid,
                    COALESCE(SUM(outstanding_amount), 0) as total_outstanding
                FROM invoices 
                WHERE organization_id = :org_id
            """),
            {"org_id": organization_id}
        ).fetchone()
        
        # Get current subscription info
        current_subscription = None
        if org.billing_status and org.subscription_end_date:
            current_subscription = {
                "status": org.billing_status.value,
                "start_date": org.subscription_start_date,
                "end_date": org.subscription_end_date,
                "billing_cycle": org.billing_cycle,
                "seat_limit": org.max_users,
                "credit_limit": org.max_credits,
                "next_billing_date": org.next_billing_date
            }
        
        # Get recent invoices (last 10)
        recent_invoices_query = (
            self.db.query(Invoice)
            .filter(Invoice.organization_id == organization_id)
            .order_by(Invoice.posting_date.desc())
            .limit(10)
            .all()
        )
        
        recent_invoices = [
            {
                "invoice_id": inv.id,
                "invoice_no": inv.invoice_no,
                "invoice_type": inv.invoice_type,
                "posting_date": inv.posting_date,
                "due_date": inv.due_date,
                "grand_total": float(inv.grand_total),
                "outstanding_amount": float(inv.outstanding_amount),
                "status": inv.status
            }
            for inv in recent_invoices_query
        ]
        
        # Get payment history (simplified - would need payment tracking)
        payment_history = [
            # This would be populated from payment records
            # For now, returning empty list as payment tracking is not fully implemented
        ]
        
        return {
            "organization_id": organization_id,
            "organization_name": org.name,
            "billing_status": org.billing_status.value if org.billing_status else "unknown",
            "total_invoices": invoice_stats.total_invoices,
            "total_amount": float(invoice_stats.total_amount),
            "total_paid": float(invoice_stats.total_paid),
            "total_outstanding": float(invoice_stats.total_outstanding),
            "current_subscription": current_subscription,
            "recent_invoices": recent_invoices,
            "payment_history": payment_history
        }
