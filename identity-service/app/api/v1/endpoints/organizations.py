"""Organization management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.authorization import (
    is_system_admin,
    require_permission,
    validate_user_in_organization,
)
from app.core.exceptions import (
    DuplicateOrganizationSlugException,
    OrganizationNotFoundException,
)
from app.database import get_db
from app.dependencies import CurrentUser, get_core_service_client, get_current_active_user
from app.models.role import UserOrganizationRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationListItem,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdate,
    PaginationMeta,
)
from app.services.core_service_client import CoreServiceClient
from app.services.organization_service import OrganizationService

router = APIRouter()
logger = logging.getLogger(__name__)


def _user_organization_ids(db: Session, user_id: UUID) -> list[UUID]:
    """Return list of organization IDs the user is a member of."""
    rows = (
        db.query(UserOrganizationRole.organization_id)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.is_active,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@router.get(
    "/organizations",
    response_model=OrganizationListResponse,
    summary="List organizations",
    description="Get paginated list of organizations; requires org.read.",
)
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: str | None = Query(
        None, description="Filter by status (active, inactive, suspended, trial)"
    ),
    organization_type: str | None = Query(
        None,
        description="Filter by type (enterprise, business, startup, individual)",
    ),
    search: str | None = Query(None, description="Search in name, slug, display_name"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List organizations with pagination and filters.

    Requires authentication and 'org.read' permission.
    Non–system-admins only see organizations they belong to.
    """
    require_permission(current_user.permissions, "org.read")
    org_ids: list[UUID] | None = None
    if not is_system_admin(current_user.permissions):
        org_ids = _user_organization_ids(db, current_user.id)
        if not org_ids:
            return OrganizationListResponse(
                organizations=[],
                pagination=PaginationMeta(
                    page=page,
                    page_size=min(page_size, 100),
                    total_items=0,
                    total_pages=0,
                    has_next=False,
                    has_prev=False,
                ),
            )
    svc = OrganizationService(db)
    items, pagination = svc.list_organizations(
        page=page,
        page_size=page_size,
        status=status,
        organization_type=organization_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        organization_ids=org_ids,
    )
    return OrganizationListResponse(
        organizations=[OrganizationListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
    summary="Get organization",
    description="Get organization by ID; requires org.read and membership.",
)
async def get_organization(
    organization_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get organization by ID. Requires org.read and membership (unless system admin)."""
    require_permission(current_user.permissions, "org.read")
    if not is_system_admin(current_user.permissions):
        validate_user_in_organization(current_user.id, organization_id, db)
    svc = OrganizationService(db)
    try:
        data = svc.get_by_id(organization_id)
        return OrganizationResponse.model_validate(data)
    except OrganizationNotFoundException:
        raise


def _user_has_no_organization(db: Session, user_id: UUID) -> bool:
    """Return True if the user is not a member of any organization (first-time user)."""
    any_org = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == user_id,
            UserOrganizationRole.is_active,
        )
        .first()
    )
    return any_org is None


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=201,
    summary="Create organization",
    description="Create a new organization. Allowed if user has org.create (or org.* / *.*) or has no org (first-time user).",
)
async def create_organization(
    body: OrganizationCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    core_client: CoreServiceClient | None = Depends(get_core_service_client),
):
    """
    Create organization. Sets owner to current user and assigns them the Owner role with *.*.

    Allowed when:
    - User has org.create, org.*, or *.* permission, OR
    - User belongs to no organization (first-time user creating their first org).
    """
    from app.core.authorization import has_permission

    can_create = has_permission(
        current_user.permissions, "org.create"
    ) or _user_has_no_organization(db, current_user.id)
    if not can_create:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Required: org.create (or create your first organization)",
        )
    svc = OrganizationService(
        db, 
        core_client=core_client,
        retry_attempts=settings.chart_creation_retry_attempts
    )
    try:
        data = svc.create(body.model_dump(), owner_id=current_user.id, user_type=current_user.user_type)
        return OrganizationResponse.model_validate(data)
    except DuplicateOrganizationSlugException:
        raise


@router.patch(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    description="Update organization; requires org.update and membership.",
)
async def update_organization(
    organization_id: UUID,
    body: OrganizationUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update organization. Requires org.update and membership (unless system admin)."""
    require_permission(current_user.permissions, "org.update")
    if not is_system_admin(current_user.permissions):
        validate_user_in_organization(current_user.id, organization_id, db)
    svc = OrganizationService(db)
    payload = body.model_dump(exclude_unset=True)
    try:
        data = svc.update(organization_id, payload, user_type=current_user.user_type)
        return OrganizationResponse.model_validate(data)
    except OrganizationNotFoundException:
        raise
    except DuplicateOrganizationSlugException:
        raise


@router.delete(
    "/organizations/{organization_id}",
    status_code=204,
    summary="Delete organization",
    description="Soft-delete organization; requires org.delete and membership.",
)
async def delete_organization(
    organization_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Soft delete organization. Requires org.delete and membership (unless system admin)."""
    require_permission(current_user.permissions, "org.delete")
    if not is_system_admin(current_user.permissions):
        validate_user_in_organization(current_user.id, organization_id, db)
    svc = OrganizationService(db)
    try:
        svc.delete(organization_id, user_type=current_user.user_type)
    except OrganizationNotFoundException:
        raise
