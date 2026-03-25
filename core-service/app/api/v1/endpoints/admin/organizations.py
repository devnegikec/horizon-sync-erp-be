"""Admin organization management endpoints.

Proxies to identity-service for org CRUD, enriches with core-service data.

POST   /admin/organizations        — create org
GET    /admin/organizations        — paginated list with search, status filter
GET    /admin/organizations/{id}   — detail with summary counts
PATCH  /admin/organizations/{id}   — partial update
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
security = HTTPBearer()


@router.post("", response_model=AdminOrgDetailResponse, status_code=201)
async def create_organization(
    body: AdminOrgCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgDetailResponse:
    service = AdminOrganizationService(db, token=credentials.credentials)
    return await service.create_organization(body)


@router.get("", response_model=AdminOrgListResponse)
async def list_organizations(
    search: str | None = Query(None, description="Search by name or slug"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgListResponse:
    service = AdminOrganizationService(db, token=credentials.credentials)
    return await service.list_organizations(
        search=search, status_filter=status, page=page, page_size=page_size
    )


@router.get("/{org_id}", response_model=AdminOrgDetailResponse)
async def get_organization(
    org_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgDetailResponse:
    service = AdminOrganizationService(db, token=credentials.credentials)
    return await service.get_organization(org_id)


@router.patch("/{org_id}", response_model=AdminOrgDetailResponse)
async def update_organization(
    org_id: UUID,
    body: AdminOrgUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminOrgDetailResponse:
    service = AdminOrganizationService(db, token=credentials.credentials)
    return await service.update_organization(org_id, body)
