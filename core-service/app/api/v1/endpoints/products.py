"""Product (shared catalog core) API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import ITEM_CREATE, ITEM_DELETE, ITEM_READ, ITEM_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter()


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
    description="Get paginated list of catalog products with optional search and filters",
)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search in name, sku or gtin"),
    is_active: bool | None = Query(None),
    product_type: str | None = Query(None, description="wms | qseal | both"),
    current_user: CurrentUser = Depends(require_permission(ITEM_READ)),
    db: Session = Depends(get_db),
):
    svc = ProductService(db)
    products, pagination = svc.list_products(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        product_type=product_type,
    )
    return ProductListResponse(
        products=[ProductResponse.model_validate(p) for p in products],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product",
)
async def get_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ITEM_READ)),
    db: Session = Depends(get_db),
):
    svc = ProductService(db)
    product = svc.get_product(product_id, current_user.organization_id)
    return ProductResponse.model_validate(product)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
)
async def create_product(
    body: ProductCreate,
    current_user: CurrentUser = Depends(require_permission(ITEM_CREATE)),
    db: Session = Depends(get_db),
):
    svc = ProductService(db)
    product = svc.create_product(body, current_user.organization_id, current_user.id)
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    current_user: CurrentUser = Depends(require_permission(ITEM_UPDATE)),
    db: Session = Depends(get_db),
):
    svc = ProductService(db)
    product = svc.update_product(
        product_id, body, current_user.organization_id, current_user.id
    )
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product (soft)",
)
async def delete_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ITEM_DELETE)),
    db: Session = Depends(get_db),
):
    svc = ProductService(db)
    svc.delete_product(product_id, current_user.organization_id)
