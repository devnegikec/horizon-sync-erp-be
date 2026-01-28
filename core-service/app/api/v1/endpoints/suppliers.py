"""Supplier management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListItem,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.supplier_service import SupplierService

router = APIRouter()


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create supplier",
    description="Create a new supplier",
)
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new supplier.

    Requires authentication.

    **Request Body:**
    - **supplier_name**: Supplier name (required)
    - **supplier_code**: Unique supplier code (required)
    - **email**, **phone**: Contact information
    - **address**, **city**, **state**, etc.: Address information
    - **tax_number**: Tax identification
    - **status**: active, inactive, blocked (default: active)
    - **payment_terms**: Payment terms in days (default: 30)

    **Returns:** Created supplier details
    """
    supplier_service = SupplierService(db)
    supplier = supplier_service.create_supplier(
        supplier_data=supplier_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return SupplierResponse.model_validate(supplier)


@router.get(
    "",
    response_model=SupplierListResponse,
    summary="List suppliers",
    description="Get paginated list of suppliers with optional filters",
)
async def list_suppliers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: str | None = Query(
        None, description="Filter by status (active, inactive, blocked)"
    ),
    search: str | None = Query(None, description="Search in name, code, email, city"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List suppliers with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by status
    - **search**: Search term for name, code, email, city
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of suppliers
    """
    supplier_service = SupplierService(db)

    suppliers, pagination = supplier_service.get_suppliers(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    supplier_items = [SupplierListItem.model_validate(s) for s in suppliers]

    return SupplierListResponse(
        suppliers=supplier_items, pagination=PaginationMeta(**pagination)
    )


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Get supplier",
    description="Get supplier details by ID",
)
async def get_supplier(
    supplier_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get supplier details by ID.

    Requires authentication.

    **Path Parameters:**
    - **supplier_id**: Supplier UUID

    **Returns:** Supplier details
    """
    supplier_service = SupplierService(db)
    supplier = supplier_service.get_supplier_by_id(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
    )
    return SupplierResponse.model_validate(supplier)


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Update supplier",
    description="Update an existing supplier",
)
async def update_supplier(
    supplier_id: UUID,
    supplier_data: SupplierUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing supplier.

    Requires authentication.

    **Path Parameters:**
    - **supplier_id**: Supplier UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated supplier details
    """
    supplier_service = SupplierService(db)
    supplier = supplier_service.update_supplier(
        supplier_id=supplier_id,
        supplier_data=supplier_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return SupplierResponse.model_validate(supplier)


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete supplier",
    description="Soft delete a supplier",
)
async def delete_supplier(
    supplier_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete a supplier.

    Requires authentication.

    **Path Parameters:**
    - **supplier_id**: Supplier UUID

    **Returns:** 204 No Content on success
    """
    supplier_service = SupplierService(db)
    supplier_service.delete_supplier(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
