"""Brand API endpoints

Requirements: 1.1, 1.7, 2.1, 2.2, 3.1, 3.3, 3.4
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.brand import (
    BrandCreate,
    BrandListResponse,
    BrandResponse,
    BrandUpdate,
)
from app.services.brand_service import BrandService

router = APIRouter()


@router.post(
    "",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create brand",
)
async def create_brand(
    data: BrandCreate,
    current_user: CurrentUser = Depends(require_permission("brand.create")),
    db: Session = Depends(get_db),
):
    svc = BrandService(db)
    brand = svc.create(data, current_user.organization_id, current_user.id)
    return BrandResponse.model_validate(brand)


@router.get(
    "",
    response_model=BrandListResponse,
    summary="List brands",
)
async def list_brands(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("brand.read")),
    db: Session = Depends(get_db),
):
    svc = BrandService(db)
    brands, pagination = svc.list(current_user.organization_id, page, page_size, search)
    return BrandListResponse(
        brands=[BrandResponse.model_validate(b) for b in brands],
        pagination=pagination,
    )


@router.get(
    "/{brand_id}",
    response_model=BrandResponse,
    summary="Get brand",
)
async def get_brand(
    brand_id: UUID,
    current_user: CurrentUser = Depends(require_permission("brand.read")),
    db: Session = Depends(get_db),
):
    svc = BrandService(db)
    return BrandResponse.model_validate(
        svc.get_by_id(brand_id, current_user.organization_id)
    )


@router.patch(
    "/{brand_id}",
    response_model=BrandResponse,
    summary="Update brand",
)
async def update_brand(
    brand_id: UUID,
    data: BrandUpdate,
    current_user: CurrentUser = Depends(require_permission("brand.update")),
    db: Session = Depends(get_db),
):
    svc = BrandService(db)
    brand = svc.update(brand_id, data, current_user.organization_id, current_user.id)
    return BrandResponse.model_validate(brand)
