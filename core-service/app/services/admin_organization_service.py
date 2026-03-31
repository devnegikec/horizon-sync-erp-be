"""Service layer for admin organization management.

Proxies requests to identity-service which owns the organizations table.
Enriches responses with core-service data (invoices, payments) where needed.
"""

import logging
import math
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.schemas.admin_organization import (
    AdminOrgBillingResponse,
    AdminOrgCreate,
    AdminOrgDetailResponse,
    AdminOrgListItem,
    AdminOrgListResponse,
    AdminOrgUpdate,
    PaginationMeta,
)

logger = logging.getLogger(__name__)

IDENTITY_API = f"{settings.identity_service_url}/api/v1/identity"


class AdminOrganizationService:
    def __init__(self, db: Session, token: str | None = None):
        self.db = db
        self.token = token

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # ── List ─────────────────────────────────────────────────────────

    async def list_organizations(
        self,
        search: str | None = None,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminOrgListResponse:
        params: dict = {"page": page, "page_size": page_size, "sort_by": "created_at", "sort_order": "desc"}
        if search:
            params["search"] = search
        if status_filter:
            params["status"] = status_filter

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{IDENTITY_API}/organizations",
                params=params,
                headers=self._headers(),
            )

        # Handle authentication/authorization errors by passing them through
        if resp.status_code in [401, 403]:
            logger.warning(f"Identity-service authentication error: {resp.status_code} - {resp.text}")
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.json().get("detail", "Authentication required")
            )
        
        if resp.status_code != 200:
            logger.error(f"Identity-service /organizations returned {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch organizations")

        data = resp.json()
        orgs_raw = data.get("organizations", [])
        pagination_raw = data.get("pagination", {})

        orgs = []
        for o in orgs_raw:
            orgs.append(AdminOrgListItem(
                id=o["id"],
                name=o["name"],
                slug=o["slug"],
                display_name=o.get("display_name"),
                status=o["status"],
                organization_type=o["organization_type"],
                is_active=o.get("is_active", True),
                created_at=o["created_at"],
            ))

        return AdminOrgListResponse(
            organizations=orgs,
            pagination=PaginationMeta(
                page=pagination_raw.get("page", page),
                page_size=pagination_raw.get("page_size", page_size),
                total_items=pagination_raw.get("total_items", 0),
                total_pages=pagination_raw.get("total_pages", 0),
                has_next=pagination_raw.get("has_next", False),
                has_prev=pagination_raw.get("has_prev", False),
            ),
        )

    # ── Detail ───────────────────────────────────────────────────────

    async def get_organization(self, org_id: UUID) -> AdminOrgDetailResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{IDENTITY_API}/organizations/{org_id}",
                headers=self._headers(),
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")        # Handle authentication/authorization errors by passing them through
        if resp.status_code in [401, 403]:
            logger.warning(f"Identity-service authentication error: {resp.status_code} - {resp.text}")
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.json().get("detail", "Authentication required")
            )        # Handle authentication/authorization errors by passing them through
        if resp.status_code in [401, 403]:
            logger.warning(f"Identity-service authentication error: {resp.status_code} - {resp.text}")
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.json().get("detail", "Authentication required")
            )
        if resp.status_code != 200:
            logger.error(f"Identity-service /organizations/{org_id} returned {resp.status_code}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch organization")

        o = resp.json()
        counts = self._get_core_counts(org_id)

        return AdminOrgDetailResponse(
            id=o["id"], name=o["name"], slug=o["slug"],
            display_name=o.get("display_name"), description=o.get("description"),
            email=o.get("email"), phone=o.get("phone"), website=o.get("website"),
            address_line1=o.get("address_line1"), address_line2=o.get("address_line2"),
            city=o.get("city"), state=o.get("state"),
            postal_code=o.get("postal_code"), country=o.get("country"),
            organization_type=o["organization_type"],
            industry=o.get("industry"), base_currency=o.get("base_currency"),
            logo_url=o.get("logo_url"), status=o["status"],
            is_active=o.get("is_active", True),
            owner_id=o.get("owner_id"),
            settings=o.get("settings"), extra_data=o.get("extra_data"),
            created_at=o["created_at"], updated_at=o.get("updated_at"),
            user_count=counts["user_count"],
            invoice_count=counts["invoice_count"],
            payment_total=counts["payment_total"],
        )

    # ── Create ───────────────────────────────────────────────────────

    async def create_organization(self, data: AdminOrgCreate) -> AdminOrgDetailResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{IDENTITY_API}/organizations",
                json=data.model_dump(),
                headers=self._headers(),
            )

        if resp.status_code == 409:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization with this slug already exists")
        if resp.status_code not in (200, 201):
            logger.error(f"Identity-service POST /organizations returned {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to create organization")

        o = resp.json()
        org_id = o["id"]
        counts = self._get_core_counts(org_id)

        return AdminOrgDetailResponse(
            id=o["id"], name=o["name"], slug=o["slug"],
            display_name=o.get("display_name"), description=o.get("description"),
            email=o.get("email"), phone=o.get("phone"), website=o.get("website"),
            address_line1=o.get("address_line1"), address_line2=o.get("address_line2"),
            city=o.get("city"), state=o.get("state"),
            postal_code=o.get("postal_code"), country=o.get("country"),
            organization_type=o["organization_type"],
            industry=o.get("industry"), base_currency=o.get("base_currency"),
            logo_url=o.get("logo_url"), status=o["status"],
            is_active=o.get("is_active", True),
            owner_id=o.get("owner_id"),
            settings=o.get("settings"), extra_data=o.get("extra_data"),
            created_at=o["created_at"], updated_at=o.get("updated_at"),
            user_count=counts["user_count"],
            invoice_count=counts["invoice_count"],
            payment_total=counts["payment_total"],
        )

    # ── Update ───────────────────────────────────────────────────────

    async def update_organization(self, org_id: UUID, data: AdminOrgUpdate) -> AdminOrgDetailResponse:
        payload = data.model_dump(exclude_unset=True)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{IDENTITY_API}/organizations/{org_id}",
                json=payload,
                headers=self._headers(),
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        if resp.status_code != 200:
            logger.error(f"Identity-service PATCH /organizations/{org_id} returned {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to update organization")

        # Re-fetch full detail
        return await self.get_organization(org_id)

    # ── Billing ──────────────────────────────────────────────────────

    async def get_billing(self, org_id: UUID) -> AdminOrgBillingResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{IDENTITY_API}/organizations/{org_id}",
                headers=self._headers(),
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch organization")

        o = resp.json()

        # Financial aggregates from core_db
        total_invoiced = (
            self.db.query(func.coalesce(func.sum(Invoice.grand_total), Decimal("0")))
            .filter(Invoice.organization_id == org_id)
            .scalar()
        ) or Decimal("0")

        total_paid = (
            self.db.query(func.coalesce(func.sum(Payment.amount), Decimal("0")))
            .filter(Payment.organization_id == org_id, Payment.status == "completed")
            .scalar()
        ) or Decimal("0")

        return AdminOrgBillingResponse(
            organization_id=o["id"],
            organization_name=o["name"],
            on_trial=o.get("on_trial", False) if "on_trial" in o else (o.get("status") == "trial"),
            trial_expiry=o.get("trial_expiry"),
            paid_until=o.get("paid_until"),
            total_invoiced=total_invoiced,
            total_paid=total_paid,
            outstanding=total_invoiced - total_paid,
        )

    # ── Core-db helpers ──────────────────────────────────────────────

    def _get_core_counts(self, org_id: UUID) -> dict:
        """Get invoice_count and payment_total from core_db. user_count comes from identity-service."""
        invoice_count = (
            self.db.query(func.count(Invoice.id))
            .filter(Invoice.organization_id == org_id)
            .scalar()
        ) or 0

        payment_total = (
            self.db.query(func.coalesce(func.sum(Payment.amount), Decimal("0")))
            .filter(Payment.organization_id == org_id)
            .scalar()
        ) or Decimal("0")

        return {"user_count": 0, "invoice_count": invoice_count, "payment_total": payment_total}

    # ── System Administration Methods ──────────────────────────────────

    async def get_master_organization(self) -> Optional[AdminOrgDetailResponse]:
        """Get the master organization details for system administration"""
        try:
            # Call identity service to get master organization
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{IDENTITY_API}/organizations/master",
                    headers=self._headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 404:
                    return None
                    
                response.raise_for_status() 
                org_data = response.json()
                
                # Map to AdminOrgDetailResponse format
                return AdminOrgDetailResponse(
                    id=UUID(org_data["id"]),
                    name=org_data["name"],
                    slug=org_data.get("slug"),
                    display_name=org_data.get("display_name"),
                    description=org_data.get("description"),
                    email=org_data.get("email"),
                    phone=org_data.get("phone"),
                    website=org_data.get("website"),
                    address_line1=org_data.get("address_line1"),
                    address_line2=org_data.get("address_line2"),
                    city=org_data.get("city"),
                    state=org_data.get("state"),
                    postal_code=org_data.get("postal_code"),
                    country=org_data.get("country"),
                    organization_type=org_data.get("organization_type", "master"),
                    industry=org_data.get("industry"),
                    base_currency=org_data.get("base_currency"),
                    logo_url=org_data.get("logo_url"),
                    status=org_data.get("status", "active"),
                    is_active=org_data.get("is_active", True),
                    owner_id=UUID(org_data["owner_id"]) if org_data.get("owner_id") else None,
                    settings=org_data.get("settings"),
                    extra_data=org_data.get("extra_data"),
                    created_at=org_data["created_at"],
                    updated_at=org_data.get("updated_at"),
                    **self._get_core_counts(UUID(org_data["id"]))
                )
                
        except httpx.RequestError as e:
            logger.error(f"Network error getting master organization: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting master organization: {e}")
            return None

    async def update_master_organization(self, updates: dict) -> Optional[AdminOrgDetailResponse]:
        """Update master organization details"""
        try:
            # First get master organization to get its ID
            master_org = await self.get_master_organization()
            if not master_org:
                raise HTTPException(status_code=404, detail="Master organization not found")
            
            # Update via identity service
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{IDENTITY_API}/organizations/{master_org.id}",
                    headers=self._headers(),
                    json=updates,
                    timeout=30.0,
                )
                
                response.raise_for_status()
                
                # Return updated organization
                return await self.get_master_organization()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating master organization: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to update master organization")
        except Exception as e:
            logger.error(f"Error updating master organization: {e}")
            raise HTTPException(status_code=500, detail="Failed to update master organization")
