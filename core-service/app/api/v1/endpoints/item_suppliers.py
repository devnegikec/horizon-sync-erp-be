"""Item supplier management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.item_supplier import (
    ItemSupplierCreate,
    ItemSupplierListItem,
    ItemSupplierListResponse,
    ItemSupplierResponse,
    ItemSupplierUpdate,
)
from app.services.item_supplier_service import ItemSupplierService

router = APIRouter()


@router.post(
    "", response_model=ItemSupplierResponse, status_code=status.HTTP_201_CREATED
)
async def create_item_supplier(
    data: ItemSupplierCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new item-supplier link. Item and supplier must exist; (item_id, supplier_id) must be unique."""
    svc = ItemSupplierService(db)
    return ItemSupplierResponse.model_validate(
        svc.create(data, current_user.organization_id)
    )


@router.get("", response_model=ItemSupplierListResponse)
async def list_item_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = Query(None, description="Filter by item ID"),
    supplier_id: UUID | None = Query(None, description="Filter by supplier ID"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List item-supplier links with pagination and filters."""
    svc = ItemSupplierService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        item_id=item_id,
        supplier_id=supplier_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ItemSupplierListResponse(
        item_suppliers=[ItemSupplierListItem.model_validate(s) for s in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{item_supplier_id}", response_model=ItemSupplierResponse)
async def get_item_supplier(
    item_supplier_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get item supplier by ID."""
    svc = ItemSupplierService(db)
    return ItemSupplierResponse.model_validate(
        svc.get_by_id(item_supplier_id, current_user.organization_id)
    )


@router.put("/{item_supplier_id}", response_model=ItemSupplierResponse)
async def update_item_supplier(
    item_supplier_id: UUID,
    data: ItemSupplierUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an item supplier."""
    svc = ItemSupplierService(db)
    return ItemSupplierResponse.model_validate(
        svc.update(item_supplier_id, data, current_user.organization_id)
    )


@router.delete("/{item_supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_supplier(
    item_supplier_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an item supplier."""
    ItemSupplierService(db).delete(item_supplier_id, current_user.organization_id)
    return None
