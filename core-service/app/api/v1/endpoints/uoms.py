"""UOM management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import UOM_CREATE, UOM_DELETE, UOM_READ, UOM_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.uom import (
    UOMCreate,
    UOMListResponse,
    UOMResponse,
    UOMUpdate,
)
from app.services.uom_service import UOMService

router = APIRouter()


@router.post(
    "",
    response_model=UOMResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create UOM",
    description="Create a new unit of measure",
)
async def create_uom(
    body: UOMCreate,
    current_user: CurrentUser = Depends(require_permission(UOM_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a new UOM. Requires uom.create permission."""
    svc = UOMService(db)
    uom = svc.create_uom(
        uom_data=body,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return UOMResponse.model_validate(uom)


@router.get(
    "",
    response_model=UOMListResponse,
    summary="List UOMs",
    description="Get paginated list of UOMs with optional search",
)
async def list_uoms(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in name or abbreviation"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(require_permission(UOM_READ)),
    db: Session = Depends(get_db),
):
    """List UOMs with pagination and search. Requires uom.read permission."""
    svc = UOMService(db)
    uoms, pagination = svc.list_uoms(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return UOMListResponse(
        uoms=[UOMResponse.model_validate(u) for u in uoms],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{uom_id}",
    response_model=UOMResponse,
    summary="Get UOM",
    description="Get UOM details by ID",
)
async def get_uom(
    uom_id: UUID,
    current_user: CurrentUser = Depends(require_permission(UOM_READ)),
    db: Session = Depends(get_db),
):
    """Get UOM by ID. Requires uom.read permission."""
    svc = UOMService(db)
    uom = svc.get_uom(
        uom_id=uom_id,
        organization_id=current_user.organization_id,
    )
    return UOMResponse.model_validate(uom)


@router.patch(
    "/{uom_id}",
    response_model=UOMResponse,
    summary="Update UOM",
    description="Update an existing UOM",
)
async def update_uom(
    uom_id: UUID,
    body: UOMUpdate,
    current_user: CurrentUser = Depends(require_permission(UOM_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update a UOM. Requires uom.update permission."""
    svc = UOMService(db)
    uom = svc.update_uom(
        uom_id=uom_id,
        uom_data=body,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return UOMResponse.model_validate(uom)


@router.delete(
    "/{uom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete UOM",
    description="Soft delete a UOM",
)
async def delete_uom(
    uom_id: UUID,
    current_user: CurrentUser = Depends(require_permission(UOM_DELETE)),
    db: Session = Depends(get_db),
):
    """Soft delete a UOM. Requires uom.delete permission."""
    svc = UOMService(db)
    svc.delete_uom(
        uom_id=uom_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
