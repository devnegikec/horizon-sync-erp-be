"""Bin stock API endpoints for managing stock at the bin level"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_CREATE, WAREHOUSE_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.bin_stock import (
    AddStockRequest,
    BinStockForItemResponse,
    BinStockInfoResponse,
    BinStockLevelResponse,
    BinStockListResponse,
    RemoveStockRequest,
)
from app.services.bin_stock_service import BinStockService

router = APIRouter()


@router.get(
    "/item/{item_id}",
    response_model=BinStockForItemResponse,
    summary="Get bins for item",
    description="Get all bins containing a specific item with quantities and capacity info",
)
async def get_bins_for_item(
    item_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get all bins containing a specific item.

    Returns bin details, quantities, and available capacity for each bin.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Returns:** List of bins with stock info for the item
    """
    service = BinStockService(db)
    bins = service.get_bins_for_item(
        item_id=item_id,
        org_id=current_user.organization_id,
    )
    return BinStockForItemResponse(bins=[BinStockInfoResponse(**b) for b in bins])


@router.post(
    "/add",
    response_model=BinStockLevelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add stock to bin",
    description="Add stock to a bin location with capacity validation",
)
async def add_stock(
    data: AddStockRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Add stock to a bin location.

    Validates:
    - Bin exists and is active
    - Bin is of type 'bin'
    - Adding quantity won't exceed bin capacity

    After adding:
    - Updates bin stock level
    - Syncs warehouse-level stock
    - Triggers capacity rollup

    **Request Body:**
    - **bin_id**: Bin location UUID
    - **item_id**: Item UUID
    - **quantity**: Quantity to add (positive)
    - **batch_number**: Optional batch number

    **Returns:** Updated bin stock level record
    """
    service = BinStockService(db)
    bin_stock = service.add_stock(
        bin_id=data.bin_id,
        item_id=data.item_id,
        quantity=data.quantity,
        org_id=current_user.organization_id,
        batch_number=data.batch_number,
    )
    return BinStockLevelResponse.model_validate(bin_stock)


@router.post(
    "/remove",
    response_model=BinStockLevelResponse,
    summary="Remove stock from bin",
    description="Remove stock from a bin location with on-hand validation",
)
async def remove_stock(
    data: RemoveStockRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Remove stock from a bin location.

    Validates:
    - Bin exists and is active
    - Sufficient on-hand quantity exists

    After removing:
    - Decrements bin stock level
    - Syncs warehouse-level stock
    - Triggers capacity rollup

    **Request Body:**
    - **bin_id**: Bin location UUID
    - **item_id**: Item UUID
    - **quantity**: Quantity to remove (positive)
    - **batch_number**: Optional batch number

    **Returns:** Updated bin stock level record
    """
    service = BinStockService(db)
    bin_stock = service.remove_stock(
        bin_id=data.bin_id,
        item_id=data.item_id,
        quantity=data.quantity,
        org_id=current_user.organization_id,
        batch_number=data.batch_number,
    )
    return BinStockLevelResponse.model_validate(bin_stock)


@router.get(
    "/{bin_id}",
    response_model=BinStockListResponse,
    summary="Get bin stock levels",
    description="Get all stock records for a specific bin location",
)
async def get_bin_stock(
    bin_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get all stock records for a specific bin.

    **Path Parameters:**
    - **bin_id**: Bin location UUID

    **Returns:** List of bin stock level records for the bin
    """
    service = BinStockService(db)
    stock_levels = service.get_bin_stock(
        bin_id=bin_id,
        org_id=current_user.organization_id,
    )
    return BinStockListResponse(
        bin_stock_levels=[
            BinStockLevelResponse.model_validate(sl) for sl in stock_levels
        ]
    )
