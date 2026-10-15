"""Dashboard layout endpoints — Settings → Dashboard Layout tab.

The layout is org-wide and stored in ``organizations.extra_data["dashboard_layout"]``
(see ``app/services/dashboard_layout_service.py``).

Full paths (identity router is mounted under ``/identity``)::

    GET    /api/v1/identity/organizations/{organization_id}/dashboard-layout
    PUT    /api/v1/identity/organizations/{organization_id}/dashboard-layout
    DELETE /api/v1/identity/organizations/{organization_id}/dashboard-layout

GET returns the server-owned widget catalogue merged with the saved state, so the
frontend renders the tab purely from the response. PUT saves the toggles, DELETE
clears them (every widget back to its catalogue default).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    has_permission,
    is_system_admin,
    validate_user_in_organization,
)
from app.core.exceptions import OrganizationNotFoundException
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.role import Permission, Role, RolePermission, UserOrganizationRole
from app.schemas.dashboard_layout import DashboardLayoutResponse, DashboardLayoutUpdate
from app.services.dashboard_layout_service import DashboardLayoutService

router = APIRouter()
logger = logging.getLogger(__name__)

ORG_UPDATE_PERMISSION = "org.update"


def _org_permission_codes(
    db: Session, user_id: UUID, organization_id: UUID
) -> list[str]:
    """Permission codes the user holds *inside this organization*.

    ``CurrentUser.permissions`` is the union of every active organization role,
    so it must not authorise an action against one specific organization: an
    ``org.update`` grant held in org A would otherwise let the holder edit org
    B, where they may only have ``org.read``. Mirrors
    ``AuthService.get_permission_codes`` but scoped by ``organization_id``.
    """
    try:
        rows = (
            db.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(
                UserOrganizationRole,
                RolePermission.role_id == UserOrganizationRole.role_id,
            )
            .join(Role, Role.id == UserOrganizationRole.role_id)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == organization_id,
                UserOrganizationRole.is_active == True,  # noqa: E712
                Role.is_active == True,  # noqa: E712
                Permission.is_active == True,  # noqa: E712
            )
            .distinct()
            .all()
        )
        return [code for (code,) in rows if code]
    except Exception:  # noqa: BLE001 - never block on a permission read
        logger.error(
            "Error fetching permissions for user %s in organization %s",
            user_id,
            organization_id,
            exc_info=True,
        )
        return []


def _require_org_update(
    current_user: CurrentUser, organization_id: UUID, db: Session
) -> None:
    """Raise 403 unless the caller may edit *this* organization's settings.

    The permission is resolved inside the target organization on purpose — see
    ``_org_permission_codes``.
    """
    if is_system_admin(current_user.permissions):
        return
    if has_permission(
        _org_permission_codes(db, current_user.id, organization_id),
        ORG_UPDATE_PERMISSION,
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission denied. Required: {ORG_UPDATE_PERMISSION}",
    )


def _require_org_access(
    current_user: CurrentUser, organization_id: UUID, db: Session
) -> None:
    """System admins may touch any org; everyone else must be a member."""
    if not is_system_admin(current_user.permissions):
        validate_user_in_organization(current_user.id, organization_id, db)


@router.get(
    "/organizations/{organization_id}/dashboard-layout",
    response_model=DashboardLayoutResponse,
    summary="Get organization dashboard layout",
    description=(
        "Returns the server-owned widget catalogue merged with the organization's "
        "saved layout. Any authenticated member of the organization may read it."
    ),
)
async def get_dashboard_layout(
    organization_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardLayoutResponse:
    _require_org_access(current_user, organization_id, db)
    svc = DashboardLayoutService(db)
    try:
        return svc.get_layout(organization_id)
    except OrganizationNotFoundException:
        raise


@router.put(
    "/organizations/{organization_id}/dashboard-layout",
    response_model=DashboardLayoutResponse,
    summary="Save organization dashboard layout",
    description=(
        "Persists which dashboard widgets are shown and in what order. Widgets "
        "omitted from the payload fall back to their catalogue defaults. Unknown "
        "widget ids are ignored and reported in `ignored_widget_ids`. "
        "Requires 'org.update'."
    ),
)
async def save_dashboard_layout(
    organization_id: UUID,
    body: DashboardLayoutUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardLayoutResponse:
    _require_org_update(current_user, organization_id, db)
    _require_org_access(current_user, organization_id, db)
    svc = DashboardLayoutService(db)
    try:
        return svc.save_layout(
            organization_id, body.widgets, updated_by=current_user.id
        )
    except OrganizationNotFoundException:
        raise


@router.delete(
    "/organizations/{organization_id}/dashboard-layout",
    response_model=DashboardLayoutResponse,
    summary="Reset organization dashboard layout",
    description=(
        "Removes the saved layout so every widget returns to its catalogue "
        "default. Requires 'org.update'."
    ),
)
async def reset_dashboard_layout(
    organization_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardLayoutResponse:
    _require_org_update(current_user, organization_id, db)
    _require_org_access(current_user, organization_id, db)
    svc = DashboardLayoutService(db)
    try:
        return svc.reset_layout(organization_id)
    except OrganizationNotFoundException:
        raise
