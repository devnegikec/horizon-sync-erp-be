"""Catalog import (product/item) API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.authorization import ITEM_CREATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.catalog_import import CatalogImportRequest, CatalogImportResponse
from app.services.catalog_import_service import CatalogImportService

router = APIRouter()


@router.post(
    "",
    response_model=CatalogImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk import products/items (idempotent upsert)",
)
async def import_catalog(
    body: CatalogImportRequest,
    current_user: CurrentUser = Depends(require_permission(ITEM_CREATE)),
    db: Session = Depends(get_db),
):
    """One import engine, three modes.

    - ``product_only``: upsert products only.
    - ``product_with_items``: upsert products + items.
    - ``item_with_auto_product``: upsert items + auto-create 1:1 products.

    Idempotent on ``(organization_id, sku)`` fallback ``(organization_id, gtin)``.
    """
    svc = CatalogImportService(db)
    result = svc.import_catalog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        mode=body.mode,
        rows=body.rows,
    )
    return CatalogImportResponse(**result)
