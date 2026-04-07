"""Thin admin service layer for cross-org payment tracking.

Provides cross-org payment list with organization_name via identity service.
Does NOT duplicate business logic from PaymentEntryService — only adds
the cross-org query that removes the org-scoping filter.
"""

import logging
import math
from datetime import datetime
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.admin_invoice import (
    AdminPaymentListItem,
    AdminPaymentListResponse,
)

logger = logging.getLogger(__name__)


class AdminPaymentService:
    def __init__(self, db: Session, token: str | None = None):
        self.db = db
        self.token = token

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

    # ── Cross-org list ───────────────────────────────────────────────

    async def list_payments(
        self,
        organization_id: UUID | None = None,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
        current_user_org: UUID | None = None,
    ) -> AdminPaymentListResponse:
        """List payments across all organizations with optional filters.
        
        For system admin users from master organizations, only shows payments
        from the master organization itself (not customer organizations).
        """
        where_clauses: list[str] = ["1=1"]
        params: dict = {}

        # Filter by master organization payments only for system admins
        if current_user_org:
            where_clauses.append("p.organization_id = :master_org_id")
            params["master_org_id"] = str(current_user_org)
            logger.info(f"Filtering payments by master organization only: {current_user_org}")
        else:
            logger.info("No current_user_org provided, showing all payments")

        if organization_id:
            where_clauses.append("p.organization_id = :organization_id")
            params["organization_id"] = organization_id

        if status_filter:
            where_clauses.append("p.status = :status")
            params["status"] = status_filter

        where_sql = " AND ".join(where_clauses)

        # Count
        count_row = self.db.execute(
            text(f"SELECT COUNT(*)::int AS total FROM payment_entries p WHERE {where_sql}"),
            params,
        ).one()
        total = count_row.total

        # Data with organization_name join
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                f"""
                SELECT p.id, p.organization_id, NULL AS organization_name,
                       p.payment_type, p.party_id, p.amount, p.currency_code,
                       p.payment_date, p.payment_mode, p.reference_no,
                       p.status, p.source, p.receipt_number,
                       p.amount - COALESCE(
                           (SELECT SUM(pr.allocated_amount)
                            FROM payment_references pr
                            WHERE pr.payment_id = p.id), 0
                       ) AS unallocated_amount,
                       p.created_at
                FROM payment_entries p
                WHERE {where_sql}
                ORDER BY p.payment_date DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        # Build party map for party_name/party_code/party_email/party_phone
        party_map = self._build_cross_org_party_map(rows)
        
        # Fetch organization names from identity service
        org_ids = list(set(row.organization_id for row in rows))
        org_names = await self._get_organization_names(org_ids)

        payments = [
            AdminPaymentListItem(
                id=row.id,
                organization_id=row.organization_id,
                organization_name=org_names.get(row.organization_id),
                payment_type=row.payment_type,
                party_id=row.party_id,
                amount=row.amount,
                currency_code=row.currency_code,
                payment_date=row.payment_date,
                payment_mode=row.payment_mode,
                reference_no=row.reference_no,
                status=row.status,
                source=row.source,
                receipt_number=row.receipt_number,
                unallocated_amount=row.unallocated_amount,
                created_at=row.created_at,
                party_name=party_map.get(row.party_id, {}).get("name"),
                party_code=party_map.get(row.party_id, {}).get("code"),
                party_email=party_map.get(row.party_id, {}).get("email"),
                party_phone=party_map.get(row.party_id, {}).get("phone"),
            )
            for row in rows
        ]

        total_pages = max(1, math.ceil(total / page_size))
        return AdminPaymentListResponse(
            payments=payments,
            page=page,
            total_pages=total_pages,
            total_count=total,
            page_size=page_size,
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def _build_cross_org_party_map(self, rows) -> dict:
        """Batch-load party name/code/email/phone for a list of payment rows."""
        from app.models.base import PaymentEntryType
        from app.models.customer import Customer
        from app.models.supplier import Supplier

        customer_ids = set()
        supplier_ids = set()
        for row in rows:
            pt = str(row.payment_type)
            if pt == PaymentEntryType.CUSTOMER_PAYMENT.value:
                customer_ids.add(row.party_id)
            elif pt == PaymentEntryType.SUPPLIER_PAYMENT.value:
                supplier_ids.add(row.party_id)

        party_map: dict = {}
        if customer_ids:
            customers = (
                self.db.query(
                    Customer.id,
                    Customer.customer_name,
                    Customer.customer_code,
                    Customer.email,
                    Customer.phone,
                )
                .filter(Customer.id.in_(customer_ids))
                .all()
            )
            for c in customers:
                party_map[c.id] = {
                    "name": c.customer_name,
                    "code": c.customer_code,
                    "email": getattr(c, "email", None),
                    "phone": getattr(c, "phone", None),
                }
        if supplier_ids:
            suppliers = (
                self.db.query(
                    Supplier.id,
                    Supplier.supplier_name,
                    Supplier.supplier_code,
                    Supplier.email,
                    Supplier.phone,
                )
                .filter(Supplier.id.in_(supplier_ids))
                .all()
            )
            for s in suppliers:
                party_map[s.id] = {
                    "name": s.supplier_name,
                    "code": s.supplier_code,
                    "email": getattr(s, "email", None),
                    "phone": getattr(s, "phone", None),
                }
        return party_map
