"""Item management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.item import Item
from app.schemas.common import PaginationMeta
from app.schemas.item import (
    ItemCreate,
    ItemListItem,
    ItemListResponse,
    ItemResponse,
    ItemSkuLookupResponse,
    ItemUpdate,
)
from app.services.item_service import ItemService

router = APIRouter()


class RejectItemRequest(BaseModel):
    """Request body for rejecting a pending item."""

    reason: str = Field(..., min_length=1, max_length=1000, description="Rejection reason")


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
    description="Create a new inventory item",
)
async def create_item(
    item_data: ItemCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new inventory item.

    Requires authentication.

    **Request Body:**
    - **item_code**: Unique item code (optional, auto-generated if not provided)
    - **item_name**: Item name (required)
    - **description**: Item description
    - **uom**: Unit of measure (default: Nos) (e.g. Kg, Nos, L, etc.)
    - **maintain_stock**: Track inventory levels (default: true)
    - **standard_rate**: Standard selling rate
    - **valuation_rate**: Valuation rate for inventory
    - **qr_product_id**: Link to a QR Product profile for unit-level tracking
    - And more...

    **Returns:** Created item details
    """
    item_service = ItemService(db)
    item = item_service.create_item(
        item_data=item_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemResponse.model_validate(item)


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List items",
    description="Get paginated list of items with optional filters",
)
async def list_items(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: str | None = Query(
        None, description="Filter by status (active, inactive, discontinued)"
    ),
    item_type: str | None = Query(
        None,
        description="Filter by item type (stock, non_stock, service, fixed_asset)",
    ),
    item_group_id: UUID | None = Query(None, description="Filter by item group ID"),
    maintain_stock: bool | None = Query(
        None, description="Filter by maintain_stock flag"
    ),
    search: str | None = Query(
        None, description="Search in item_code, item_name, barcode, sku"
    ),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List inventory items with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by item status
    - **item_type**: Filter by item type
    - **item_group_id**: Filter by item group
    - **maintain_stock**: Filter by inventory tracking flag
    - **search**: Search term for item_code, item_name, barcode
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of items
    """
    item_service = ItemService(db)

    items, pagination = item_service.get_items(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        item_type=item_type,
        item_group_id=item_group_id,
        maintain_stock=maintain_stock,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Convert to response schema
    item_items = [ItemListItem.model_validate(item) for item in items]

    return ItemListResponse(items=item_items, pagination=PaginationMeta(**pagination))


@router.get(
    "/by-sku/{sku}",
    response_model=ItemSkuLookupResponse,
    summary="Lookup item by SKU or barcode",
    description="Find an item by item_code or barcode. Used by mobile app when scanning items during inbound.",
)
async def get_item_by_sku(
    sku: str,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lookup an item by SKU, item_code, or barcode.

    Returns item details for inbound scanning. Searches in order:
    sku → item_code → barcode.
    """
    import logging

    _log = logging.getLogger(__name__)
    org_id = current_user.organization_id
    _log.info("SKU lookup: sku=%s org_id=%s", sku, org_id)

    # Search order: sku → item_code → barcode
    item = None
    base_query = db.query(Item).filter(Item.deleted_at.is_(None))
    if org_id:
        base_query = base_query.filter(Item.organization_id == org_id)

    for field in [Item.sku, Item.item_code, Item.barcode]:
        item = base_query.filter(field == sku).first()
        if item:
            break

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No item found for SKU: {sku}",
        )

    return ItemSkuLookupResponse.model_validate(item)


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item",
    description="Get item details by ID",
)
async def get_item(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get inventory item details by ID.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Returns:** Item details including item group info
    """
    item_service = ItemService(db)
    item = item_service.get_item_by_id(
        item_id=item_id,
        organization_id=current_user.organization_id,
        include_group=True,
    )
    return ItemResponse.model_validate(item)


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Update an existing item",
)
async def update_item(
    item_id: UUID,
    item_data: ItemUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing inventory item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated item details
    """
    item_service = ItemService(db)
    item = item_service.update_item(
        item_id=item_id,
        item_data=item_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
    description="Soft delete an item",
)
async def delete_item(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete an inventory item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Returns:** 204 No Content on success
    """
    item_service = ItemService(db)
    item_service.delete_item(
        item_id=item_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None


@router.post(
    "/{item_id}/submit",
    response_model=ItemResponse,
    summary="Submit item for approval",
)
async def submit_item_for_approval(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item_service = ItemService(db)
    item = item_service.submit_for_approval(
        item_id=item_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemResponse.model_validate(item)


@router.post(
    "/{item_id}/approve",
    response_model=ItemResponse,
    summary="Approve item",
)
async def approve_item(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item_service = ItemService(db)
    item = item_service.approve_item(
        item_id=item_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ItemResponse.model_validate(item)


@router.post(
    "/{item_id}/reject",
    response_model=ItemResponse,
    summary="Reject item",
)
async def reject_item(
    item_id: UUID,
    body: RejectItemRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item_service = ItemService(db)
    item = item_service.reject_item(
        item_id=item_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        reason=body.reason,
    )
    return ItemResponse.model_validate(item)


@router.get(
    "/{item_id}/qr-product",
    summary="Get linked QR product",
    description="Returns the QR product profile linked to this item, if any.",
)
async def get_item_qr_product(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the QR product linked to an inventory item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Returns:** QR product details, or 404 if the item has no linked QR product.
    """
    from fastapi import HTTPException

    from app.schemas.qr_product import QRProductResponse
    from app.services.qr_product_service import QRProductService

    item_service = ItemService(db)
    item = item_service.get_item_by_id(
        item_id=item_id,
        organization_id=current_user.organization_id,
    )

    if not item.qr_product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This item has no linked QR product",
        )

    qr_service = QRProductService(db)
    qr_product = qr_service.get_product(
        item.qr_product_id, current_user.organization_id
    )
    return QRProductResponse.model_validate(qr_product)


@router.get(
    "/{item_id}/qr-serials",
    summary="List QR serial numbers for an item",
    description=(
        "Returns all ProductItem serial numbers generated under the QR product "
        "linked to this item. Paginated."
    ),
)
async def list_item_qr_serials(
    item_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List QR serial numbers (ProductItems) for an inventory item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 200)

    **Returns:** Paginated list of ProductItem serial numbers, or 404 if no QR product is linked.
    """
    from fastapi import HTTPException

    from app.schemas.qr_product import ProductItemListResponse, ProductItemResponse
    from app.services.qr_product_service import QRProductService

    item_service = ItemService(db)
    item = item_service.get_item_by_id(
        item_id=item_id,
        organization_id=current_user.organization_id,
    )

    if not item.qr_product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This item has no linked QR product",
        )

    qr_service = QRProductService(db)
    # Validate the QR product belongs to this org
    qr_service.get_product(item.qr_product_id, current_user.organization_id)

    from app.repositories.qr_product_repository import ProductItemRepository

    item_repo = ProductItemRepository(db)
    serials, total = item_repo.list_by_product(
        item.qr_product_id, current_user.organization_id, page, page_size
    )
    total_pages = (total + page_size - 1) // page_size

    return ProductItemListResponse(
        items=[ProductItemResponse.model_validate(s) for s in serials],
        pagination={
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    )
