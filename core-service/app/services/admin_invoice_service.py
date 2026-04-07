"""Thin admin service layer for cross-org invoice management.

Reuses existing InvoiceService for create, get_by_id, and send logic.
Adds cross-org list/detail methods that query without org-scoping and
join to organizations for organization_name.
Integrates SubscriptionInvoiceService for B2B billing (Task 1B-2).
"""

import math
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from uuid import UUID
import logging

import httpx
from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
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

# Reusable read-only engine for identity DB (org name lookups)
_identity_engine = None
def _get_identity_engine():
    global _identity_engine
    if _identity_engine is None and settings.identity_database_url:
        _identity_engine = create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)
    return _identity_engine


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
        """Fetch organization names from identity database directly."""
        if not org_ids:
            return {}

        # Try direct DB access first (most reliable)
        engine = _get_identity_engine()
        if engine:
            try:
                with engine.connect() as conn:
                    placeholders = ", ".join(f"'{str(oid)}'" for oid in org_ids)
                    rows = conn.execute(
                        text(f"SELECT id, name FROM organizations WHERE id::text IN ({placeholders})")
                    ).fetchall()
                    org_names = {UUID(str(row[0])): row[1] for row in rows}
                    if org_names:
                        logger.info(f"Fetched {len(org_names)} org names from identity DB")
                        return org_names
            except Exception as e:
                logger.warning(f"Direct identity DB lookup failed: {e}")

        # Fallback to HTTP call to identity service
        if not self.token:
            return {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{settings.identity_service_url}/api/v1/identity/organizations"
                headers = {"Authorization": f"Bearer {self.token}"}
                response = await client.get(url, params={"page_size": 1000}, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    org_names = {}
                    for org in data.get("organizations", []):
                        org_id = UUID(org["id"])
                        if org_id in org_ids:
                            org_names[org_id] = org["name"]
                    logger.info(f"Fetched {len(org_names)} org names via HTTP")
                    return org_names
        except Exception as e:
            logger.error(f"HTTP org name lookup failed: {e}")

        return {}

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

    def _get_org_name_sync(self, org_id: UUID) -> str | None:
        """Synchronously fetch a single organization name from identity DB."""
        engine = _get_identity_engine()
        if engine:
            try:
                with engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT name FROM organizations WHERE id = :oid"),
                        {"oid": str(org_id)}
                    ).fetchone()
                    if row:
                        return row[0]
            except Exception as e:
                logger.warning(f"Direct identity DB lookup failed for org {org_id}: {e}")
        return None

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

        # Resolve organization_name from identity DB
        response["organization_name"] = self._get_org_name_sync(inv.organization_id)

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
        elif party_type == "organization" and inv.party_id:
            # For subscription invoices (self-billing), get organization info from identity service
            try:
                if self.token:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(
                            f"{settings.identity_service_url}/api/v1/identity/organizations/{inv.party_id}",
                            headers={"Authorization": f"Bearer {self.token}"}
                        )
                        if response.status_code == 200:
                            org_data = response.json()
                            party_email = org_data.get("billing_contact_email") or org_data.get("email")
                            party_name = org_data.get("name", f"Organization {inv.party_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch organization email for {inv.party_id}: {e}")

        if not party_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Party email not found for {party_type} — cannot send invoice",
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

    async def mark_invoice_paid(
        self, invoice_id: UUID, payment_data: dict, user_id: UUID
    ) -> dict:
        """Mark an invoice as paid and create a corresponding payment entry."""
        from app.models.base import InvoiceStatus, PaymentEntryType, PaymentMode, PaymentEntryStatus, PaymentSource
        from app.models.payment_entry import PaymentEntry
        from app.models.payment_reference import PaymentReference
        from app.services.document_numbering_service import DocumentNumberingService
        
        # Get the invoice
        inv = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )
        
        # Determine payment type based on invoice party type
        if inv.party_type == "customer":
            payment_type = PaymentEntryType.CUSTOMER_PAYMENT
        elif inv.party_type == "supplier":
            payment_type = PaymentEntryType.SUPPLIER_PAYMENT
        else:
            # For organization invoices (B2B), treat as customer payment
            payment_type = PaymentEntryType.CUSTOMER_PAYMENT
        
        # Parse payment date
        payment_date = datetime.now(UTC)
        if payment_data.get("payment_date"):
            try:
                payment_date_str = payment_data["payment_date"]
                # Handle both ISO format with and without 'Z'
                if payment_date_str.endswith('Z'):
                    payment_date_str = payment_date_str.replace('Z', '+00:00')
                payment_date = datetime.fromisoformat(payment_date_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse payment_date '{payment_data.get('payment_date')}': {e}")
        
        # Map payment method to PaymentMode enum
        payment_method = payment_data.get("payment_method", "bank_transfer")
        try:
            if payment_method.lower() in ["credit_card", "debit_card", "card"]:
                payment_mode = PaymentMode.BANK_TRANSFER  # Cards go through bank
            elif payment_method.lower() in ["cash"]:
                payment_mode = PaymentMode.CASH
            elif payment_method.lower() in ["check", "cheque"]:
                payment_mode = PaymentMode.CHECK
            else:
                payment_mode = PaymentMode.BANK_TRANSFER  # Default
        except:
            payment_mode = PaymentMode.BANK_TRANSFER
        
        # Generate receipt number
        doc_num_svc = DocumentNumberingService(self.db)
        receipt_number = doc_num_svc.get_next_number(
            inv.organization_id, "payment", reference_date=payment_date
        )
        
        # Create PaymentEntry record
        payment_entry = PaymentEntry(
            organization_id=inv.organization_id,
            payment_type=payment_type,
            party_id=inv.party_id,
            amount=inv.outstanding_amount,  # Pay the full outstanding amount
            currency_code="USD",  # TODO: Get from invoice or organization settings
            payment_date=payment_date,
            payment_mode=payment_mode,
            reference_no=payment_data.get("transaction_id"),
            receipt_number=receipt_number,
            status=PaymentEntryStatus.CONFIRMED,  # Mark as confirmed since invoice is being marked as paid
            source=PaymentSource.MANUAL,
            created_by=user_id,
            updated_by=user_id,
        )
        
        self.db.add(payment_entry)
        self.db.flush()  # Get the payment_entry.id
        
        # Create PaymentReference to link payment to invoice
        payment_reference = PaymentReference(
            organization_id=inv.organization_id,
            payment_id=payment_entry.id,
            invoice_id=inv.id,
            allocated_amount=inv.outstanding_amount,  # Allocate full outstanding amount
            created_by=user_id,
        )
        
        self.db.add(payment_reference)
        
        # Update invoice status to paid and clear outstanding amount
        inv.status = InvoiceStatus.PAID
        inv.outstanding_amount = 0
        inv.paid_at = payment_date
        inv.updated_by = user_id
        inv.updated_at = datetime.now(UTC)
        
        self.db.commit()
        self.db.refresh(payment_entry)
        self.db.refresh(inv)
        
        return {
            "invoice_id": str(inv.id),
            "payment_id": str(payment_entry.id),
            "receipt_number": payment_entry.receipt_number,
            "status": "paid",
            "message": "Invoice marked as paid and payment entry created successfully",
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "payment_data": payment_data,
        }

    async def create_payment_from_invoice(
        self, invoice_id: UUID, payment_data: dict, user_id: UUID
    ) -> dict:
        """Create a payment entry from an invoice."""
        from app.models.base import InvoiceStatus
        
        logger.info(f"Creating payment for invoice {invoice_id} with data: {payment_data}")
        
        # Get the invoice
        inv = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            logger.error(f"Invoice not found: {invoice_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )
        
        # Validate payment amount
        payment_amount = payment_data.get("payment_amount", 0)
        logger.info(f"Payment amount received: {payment_amount} (type: {type(payment_amount)})")
        logger.info(f"Invoice outstanding amount: {inv.outstanding_amount} (type: {type(inv.outstanding_amount)})")
        
        # Convert payment_amount to Decimal for consistent calculations
        from decimal import Decimal
        try:
            payment_amount = Decimal(str(payment_amount))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid payment amount format: {payment_amount}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount must be a valid number",
            )
        
        if payment_amount <= 0:
            logger.error(f"Invalid payment amount: {payment_amount}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount must be greater than 0",
            )
            
        # Validate payment amount is not greater than outstanding amount
        if payment_amount > inv.outstanding_amount:
            logger.error(f"Payment amount {payment_amount} exceeds outstanding amount {inv.outstanding_amount}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ({payment_amount}) cannot exceed outstanding amount ({inv.outstanding_amount})",
            )
        
        # Update invoice outstanding amount (both are now Decimal)
        new_outstanding = max(Decimal('0'), inv.outstanding_amount - payment_amount)
        
        # Parse payment date
        payment_date = datetime.now(UTC)
        if payment_data.get("payment_date"):
            try:
                payment_date_str = payment_data["payment_date"]
                if payment_date_str.endswith('Z'):
                    payment_date_str = payment_date_str.replace('Z', '+00:00')
                payment_date = datetime.fromisoformat(payment_date_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse payment_date: {e}")
        
        # Create PaymentEntry record
        from app.models.base import PaymentEntryType, PaymentMode, PaymentEntryStatus, PaymentSource
        from app.models.payment_entry import PaymentEntry
        from app.models.payment_reference import PaymentReference
        from app.services.document_numbering_service import DocumentNumberingService
        
        # Determine payment type
        if inv.party_type == "customer":
            payment_type = PaymentEntryType.CUSTOMER_PAYMENT
        elif inv.party_type == "supplier":
            payment_type = PaymentEntryType.SUPPLIER_PAYMENT
        else:
            payment_type = PaymentEntryType.CUSTOMER_PAYMENT
        
        # Map payment method to PaymentMode enum
        payment_method = payment_data.get("payment_method", "bank_transfer")
        try:
            if payment_method.lower() in ["credit_card", "debit_card", "card"]:
                payment_mode = PaymentMode.BANK_TRANSFER
            elif payment_method.lower() in ["cash"]:
                payment_mode = PaymentMode.CASH
            elif payment_method.lower() in ["check", "cheque"]:
                payment_mode = PaymentMode.CHECK
            else:
                payment_mode = PaymentMode.BANK_TRANSFER
        except:
            payment_mode = PaymentMode.BANK_TRANSFER
        
        # Generate receipt number
        doc_num_svc = DocumentNumberingService(self.db)
        receipt_number = doc_num_svc.get_next_number(
            inv.organization_id, "payment", reference_date=payment_date
        )
        
        # Create PaymentEntry
        payment_entry = PaymentEntry(
            organization_id=inv.organization_id,
            payment_type=payment_type,
            party_id=inv.party_id,
            amount=payment_amount,
            currency_code="USD",
            payment_date=payment_date,
            payment_mode=payment_mode,
            reference_no=payment_data.get("notes"),
            receipt_number=receipt_number,
            status=PaymentEntryStatus.CONFIRMED,
            source=PaymentSource.MANUAL,
            created_by=user_id,
            updated_by=user_id,
        )
        
        self.db.add(payment_entry)
        self.db.flush()  # Get payment_entry.id
        
        # Create PaymentReference to link payment to invoice
        payment_reference = PaymentReference(
            organization_id=inv.organization_id,
            payment_id=payment_entry.id,
            invoice_id=inv.id,
            allocated_amount=payment_amount,
            created_by=user_id,
        )
        
        self.db.add(payment_reference)
        
        # Update invoice details
        inv.outstanding_amount = new_outstanding
        
        # Mark as paid if fully paid
        if new_outstanding == 0:
            inv.status = InvoiceStatus.PAID
            inv.paid_at = payment_date
        
        inv.updated_by = user_id
        inv.updated_at = datetime.now(UTC)
        
        self.db.commit()
        self.db.refresh(inv)
        self.db.refresh(payment_entry)
        
        logger.info(f"Payment created successfully for invoice {invoice_id}: PaymentEntry ID {payment_entry.id}")
        
        return {
            "payment_id": str(payment_entry.id),
            "invoice_id": str(inv.id),
            "success": True,
            "message": "Payment created successfully",
            "payment_amount": payment_amount,
            "remaining_balance": new_outstanding,
            "invoice_status": inv.status.value if hasattr(inv.status, 'value') else str(inv.status),
            "payment_data": payment_data,
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
            
            # For customer IDs not found, try looking up by customer_name from the customers table
            # using a broader search (some party_ids may reference organizations)
            missing_ids = customer_ids - set(party_map.keys())
            if missing_ids:
                # Try to find customer name by matching organization_id
                for mid in missing_ids:
                    cust = (
                        self.db.query(Customer.customer_name, Customer.customer_code)
                        .filter(Customer.organization_id == mid)
                        .first()
                    )
                    if cust:
                        party_map[mid] = {"name": cust.customer_name, "code": cust.customer_code}

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
