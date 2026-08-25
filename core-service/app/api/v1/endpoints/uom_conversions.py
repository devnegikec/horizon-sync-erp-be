"""UOM Conversion management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import UOM_CREATE, UOM_DELETE, UOM_READ, UOM_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.uom_conversion import (
    UOMConversionBulkRequest,
    UOMConversionBulkResponse,
    UOMConversionCreate,
    UOMConversionListResponse,
    UOMConversionResponse,
    UOMConversionUpdate,
)
from app.services.uom_conversion_service import UOMConversionService

router = APIRouter()


@router.put(
    "/bulk",
    response_model=UOMConversionBulkResponse,
    summary="Bulk upsert UOM conversions",
    description="Upsert a list of UOM conversions in one request. Returns created/updated counts and per-row errors.",
)
async def bulk_upsert_uom_conversions(
    body: UOMConversionBulkRequest,
    current_user: CurrentUser = Depends(require_permission(UOM_UPDATE)),
    db: Session = Depends(get_db),
):
    """Bulk upsert UOM conversions. Requires uom.update permission."""
    svc = UOMConversionService(db)
    created, updated, deleted, errors = svc.bulk_upsert_conversions(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        conversions=body.conversions,
    )
    return UOMConversionBulkResponse(
        created=created,
        updated=updated,
        deleted=deleted,
        errors=errors,
    )


@router.post(
    "",
    response_model=UOMConversionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create UOM Conversion",
    description="Create a new UOM conversion for an item",
)
async def create_uom_conversion(
    body: UOMConversionCreate,
    current_user: CurrentUser = Depends(require_permission(UOM_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a new UOM Conversion. Requires uom.create permission."""
    svc = UOMConversionService(db)
    conversion = svc.create_conversion(
        conversion_data=body,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return UOMConversionResponse.model_validate(conversion)


@router.get(
    "",
    response_model=UOMConversionListResponse,
    summary="List UOM Conversions",
    description="Get paginated list of UOM conversions, optionally filtered by item_id",
)
async def list_uom_conversions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    item_id: UUID | None = Query(None, description="Filter by item ID"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(require_permission(UOM_READ)),
    db: Session = Depends(get_db),
):
    """List UOM Conversions with pagination and optional item_id filter. Requires uom.read permission."""
    svc = UOMConversionService(db)
    conversions, pagination = svc.list_conversions(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        item_id=item_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return UOMConversionListResponse(
        uom_conversions=[UOMConversionResponse.model_validate(c) for c in conversions],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{conversion_id}",
    response_model=UOMConversionResponse,
    summary="Get UOM Conversion",
    description="Get UOM conversion details by ID",
)
async def get_uom_conversion(
    conversion_id: UUID,
    current_user: CurrentUser = Depends(require_permission(UOM_READ)),
    db: Session = Depends(get_db),
):
    """Get UOM Conversion by ID. Requires uom.read permission."""
    svc = UOMConversionService(db)
    conversion = svc.get_conversion(
        conversion_id=conversion_id,
        organization_id=current_user.organization_id,
    )
    return UOMConversionResponse.model_validate(conversion)


@router.patch(
    "/{conversion_id}",
    response_model=UOMConversionResponse,
    summary="Update UOM Conversion",
    description="Update an existing UOM conversion",
)
async def update_uom_conversion(
    conversion_id: UUID,
    body: UOMConversionUpdate,
    current_user: CurrentUser = Depends(require_permission(UOM_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update a UOM Conversion. Requires uom.update permission."""
    svc = UOMConversionService(db)
    conversion = svc.update_conversion(
        conversion_id=conversion_id,
        conversion_data=body,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return UOMConversionResponse.model_validate(conversion)


@router.delete(
    "/{conversion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete UOM Conversion",
    description="Soft delete a UOM conversion",
)
async def delete_uom_conversion(
    conversion_id: UUID,
    current_user: CurrentUser = Depends(require_permission(UOM_DELETE)),
    db: Session = Depends(get_db),
):
    """Soft delete a UOM Conversion. Requires uom.delete permission."""
    svc = UOMConversionService(db)
    svc.delete_conversion(
        conversion_id=conversion_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
