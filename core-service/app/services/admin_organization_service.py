"""Service layer for admin organization management.

Orchestrates repository calls, enforces business rules (duplicate slug,
suspension cascade), and will integrate audit logging once AdminAuditService
is created in task 11.3.
"""

import math
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.admin_organization_repository import AdminOrganizationRepository
from app.schemas.admin_organization import (
    AdminOrgBillingResponse,
    AdminOrgCreate,
    AdminOrgDetailResponse,
    AdminOrgListItem,
    AdminOrgListResponse,
    AdminOrgUpdate,
    PaginationMeta,
)


class AdminOrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminOrganizationRepository(db)
        # TODO (task 11.3): integrate AdminAuditService
        # self.audit_service = AdminAuditService(db)

    # ── Create ───────────────────────────────────────────────────────

    def create_organization(self, data: AdminOrgCreate) -> AdminOrgDetailResponse:
        """Create a new organization. Raises 409 if slug is taken."""
        if self.repo.slug_exists(data.slug):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization with this slug already exists",
            )

        org_dict = data.model_dump()
        created = self.repo.create(org_dict)
        self.db.commit()

        # TODO (task 11.3): audit log
        # self.audit_service.log(admin_user_id, "create", "organization", created["id"], None, org_dict)

        counts = self.repo.get_summary_counts(created["id"])
        return AdminOrgDetailResponse(**created, **counts)

    # ── List ─────────────────────────────────────────────────────────

    def list_organizations(
        self,
        search: str | None = None,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminOrgListResponse:
        orgs, total = self.repo.list_organizations(
            search=search, status=status_filter, page=page, page_size=page_size
        )
        total_pages = max(1, math.ceil(total / page_size))
        return AdminOrgListResponse(
            organizations=[AdminOrgListItem(**o) for o in orgs],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    # ── Detail ───────────────────────────────────────────────────────

    def get_organization(self, org_id: UUID) -> AdminOrgDetailResponse:
        org = self.repo.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        counts = self.repo.get_summary_counts(org_id)
        return AdminOrgDetailResponse(**org, **counts)

    # ── Update ───────────────────────────────────────────────────────

    def update_organization(
        self,
        org_id: UUID,
        data: AdminOrgUpdate,
    ) -> AdminOrgDetailResponse:
        # Ensure org exists
        existing = self.repo.get_by_id(org_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        update_dict = data.model_dump(exclude_unset=True)

        # Suspension cascade: if status is being set to "suspended"
        if update_dict.get("status") == "suspended":
            self.repo.deactivate_all_users(org_id)

        updated = self.repo.update(org_id, update_dict)
        self.db.commit()

        # TODO (task 11.3): audit log
        # self.audit_service.log(admin_user_id, "update", "organization", org_id, old_values, update_dict)

        counts = self.repo.get_summary_counts(org_id)
        return AdminOrgDetailResponse(**updated, **counts)  # type: ignore

    # ── Billing ──────────────────────────────────────────────────────

    def get_billing(self, org_id: UUID) -> AdminOrgBillingResponse:
        billing = self.repo.get_billing_info(org_id)
        if not billing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        return AdminOrgBillingResponse(**billing)
