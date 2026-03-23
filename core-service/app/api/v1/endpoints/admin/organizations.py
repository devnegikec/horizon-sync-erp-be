"""Admin organization management endpoints.

POST   /admin/organizations        — create org (201, 409 for duplicate slug)
GET    /admin/organizations        — paginated list with search, status filter
GET    /admin/organizations/{id}   — detail with summary counts (404 if not found)
PATCH  /admin/organizations/{id}   — partial update with suspension cascade
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_organization import (
    AdminOrgCreate,
    AdminOrgDetailResponse,
    AdminOrgListResponse,
    AdminOrgUpdate,
)
from app.services.admin_organization_service import AdminOrganizationService

router = APIRouter()


@router.post("", response_model=AdminOrgDetailResponse, status_code=201)
async def create_organization(
    body: AdminOrgCreate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgDetailResponse:
    """Create a new organization. Returns 409 if slug already exists."""
    service = AdminOrganizationService(db)
    return service.create_organization(body)


@router.get("", response_model=AdminOrgListResponse)
async def list_organizations(
    search: str | None = Query(None, description="Search by name or slug"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgListResponse:
    """Return a paginated list of organizations with optional filters."""
    service = AdminOrganizationService(db)
    return service.list_organizations(
        search=search, status_filter=status, page=page, page_size=page_size
    )


@router.get("/{org_id}", response_model=AdminOrgDetailResponse)
async def get_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgDetailResponse:
    """Return full organization detail with user_count, invoice_count, payment_total."""
    service = AdminOrganizationService(db)
    return service.get_organization(org_id)


@router.patch("/{org_id}", response_model=AdminOrgDetailResponse)
async def update_organization(
    org_id: UUID,
    body: AdminOrgUpdate,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgDetailResponse:
    """Partially update an organization. Setting status to 'suspended' cascades deactivation to all org users."""
    service = AdminOrganizationService(db)
    return service.update_organization(org_id, body)
