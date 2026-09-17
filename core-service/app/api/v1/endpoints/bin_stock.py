"""Bin stock API endpoints for managing stock at the bin level"""

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.authorization import STOCK_ENTRY_CREATE, WAREHOUSE_READ
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.bin_stock_level import BinStockLevel
from app.models.item import Item
from app.models.warehouse_location import WarehouseLocation
from app.schemas.bin_stock import (
    AddStockRequest,
    BinStockForItemResponse,
    BinStockInfoResponse,
    BinStockLevelResponse,
    BinStockListResponse,
    BinStockParentResponse,
    BinStockParentsResponse,
    BulkAddStockRequest,
    BulkAddStockResponse,
    CopyStockRequest,
    RemoveStockRequest,
    StockImportRequest,
    StockImportResult,
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
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
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
    "/bulk-add",
    response_model=BulkAddStockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add stock to bin",
    description="Add multiple items to a single bin in one API call. Each item is processed independently — failures for individual items do not affect others.",
)
async def bulk_add_stock(
    data: BulkAddStockRequest,
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Add multiple items to a single bin in one API call.

    Validates per-item:
    - Quantity must be positive
    - Cumulative capacity won't be exceeded (per-item check against running total)

    After adding:
    - Creates/updates BinStockLevel records for each item
    - Syncs warehouse-level stock
    - Triggers capacity rollup (once for all items)

    **Request Body:**
    - **bin_id**: Bin location UUID (all items go to this bin)
    - **items**: List of { item_id, quantity, batch_number? } (max 50)

    **Returns:** Per-item status with "added" or "error", plus summary counts
    """
    service = BinStockService(db)
    items_dicts = [
        {
            "item_id": item.item_id,
            "quantity": item.quantity,
            "batch_number": item.batch_number,
        }
        for item in data.items
    ]
    result = service.bulk_add_stock(
        bin_id=data.bin_id,
        items=items_dicts,
        org_id=current_user.organization_id,
    )
    return BulkAddStockResponse(**result)


@router.post(
    "/remove",
    response_model=BinStockLevelResponse,
    summary="Remove stock from bin",
    description="Remove stock from a bin location with on-hand validation",
)
async def remove_stock(
    data: RemoveStockRequest,
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
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
    levels = []
    for sl in stock_levels:
        resp = BinStockLevelResponse.model_validate(sl)
        item = sl.item
        resp.item_name = item.item_name if item else None
        resp.sku = item.sku if item else None
        levels.append(resp)
    return BinStockListResponse(bin_stock_levels=levels)


@router.get(
    "/{bin_id}/parents",
    response_model=BinStockParentsResponse,
    summary="Get parent boxes in a bin",
    description="Get the master-pack (parent) boxes present in a bin, aggregated from child units",
)
async def get_bin_parents(
    bin_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get the parent (master-pack) boxes present in a bin.

    Child units are stored individually in bin stock; this endpoint groups them
    by their QSeal parent so the warehouse manager can see box-level counts.

    **Path Parameters:**
    - **bin_id**: Bin location UUID

    **Returns:** Parent boxes with child-unit counts for the bin
    """
    service = BinStockService(db)
    parents = service.get_parent_boxes(
        bin_id=bin_id,
        org_id=current_user.organization_id,
    )
    return BinStockParentsResponse(
        bin_id=bin_id,
        total_parent_boxes=len(parents),
        parents=[BinStockParentResponse(**p) for p in parents],
    )


@router.post(
    "/copy",
    response_model=BinStockLevelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Copy stock between bins",
    description="Copy a specific quantity of stock from one bin to another",
)
async def copy_stock(
    data: CopyStockRequest,
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
    db: Session = Depends(get_db),
):
    """Copy stock from source bin to target bin."""
    service = BinStockService(db)
    # Remove from source
    service.remove_stock(
        bin_id=data.source_bin_id,
        item_id=data.item_id,
        quantity=data.quantity,
        org_id=current_user.organization_id,
        batch_number=data.batch_number,
    )
    # Add to target
    bin_stock = service.add_stock(
        bin_id=data.target_bin_id,
        item_id=data.item_id,
        quantity=data.quantity,
        org_id=current_user.organization_id,
        batch_number=data.batch_number,
    )
    return BinStockLevelResponse.model_validate(bin_stock)


@router.get(
    "/export/csv",
    summary="Export stock levels to CSV",
    description="Export bin stock levels as a downloadable CSV file",
)
async def export_stock_csv(
    warehouse_id: UUID | None = Query(None),
    item_id: UUID | None = Query(None),
    bin_id: UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Export stock levels as CSV."""
    from app.models.bin_stock_level import BinStockLevel

    query = db.query(BinStockLevel).filter(
        BinStockLevel.organization_id == current_user.organization_id
    )
    if warehouse_id:
        from app.models.warehouse_location import WarehouseLocation

        bin_ids = [
            b.id
            for b in db.query(WarehouseLocation)
            .filter(WarehouseLocation.warehouse_id == warehouse_id)
            .all()
        ]
        query = query.filter(BinStockLevel.bin_location_id.in_(bin_ids))
    if item_id:
        query = query.filter(BinStockLevel.item_id == item_id)
    if bin_id:
        query = query.filter(BinStockLevel.bin_location_id == bin_id)

    records = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "bin_location_id",
            "item_id",
            "quantity_on_hand",
            "batch_number",
            "created_at",
            "updated_at",
        ]
    )
    for r in records:
        writer.writerow(
            [
                str(r.bin_location_id),
                str(r.item_id),
                str(r.quantity_on_hand),
                r.batch_number or "",
                r.created_at.isoformat() if r.created_at else "",
                r.updated_at.isoformat() if r.updated_at else "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_levels.csv"},
    )


@router.post(
    "/import",
    response_model=StockImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Import stock levels",
    description="Import stock levels from structured data rows",
)
async def import_stock(
    data: StockImportRequest,
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
    db: Session = Depends(get_db),
):
    """Import stock levels into bins."""
    service = BinStockService(db)
    imported = 0
    updated = 0
    errors: list[str] = []

    # Build SKU -> item_id map
    items = (
        db.query(Item)
        .filter(
            Item.organization_id == current_user.organization_id,
            Item.item_code.in_([r.sku for r in data.rows]),
        )
        .all()
    )
    sku_to_item = {item.item_code: item.id for item in items}

    # Build bin_code -> bin_id map within warehouse
    bins = (
        db.query(WarehouseLocation)
        .filter(
            WarehouseLocation.warehouse_id == data.warehouse_id,
        )
        .all()
    )
    code_to_bin = {bin_loc.code: bin_loc.id for bin_loc in bins}

    for row in data.rows:
        item_id = sku_to_item.get(row.sku)
        if not item_id:
            errors.append(f"SKU not found: {row.sku}")
            continue
        bin_id = code_to_bin.get(row.bin_code)
        if not bin_id:
            errors.append(f"Bin code not found: {row.bin_code}")
            continue

        try:
            existing = (
                db.query(BinStockLevel)
                .filter(
                    BinStockLevel.bin_location_id == bin_id,
                    BinStockLevel.item_id == item_id,
                    BinStockLevel.batch_number == row.batch_number,
                )
                .first()
            )

            if existing and data.overwrite_existing:
                existing.quantity_on_hand = row.quantity
                updated += 1
            elif existing:
                errors.append(
                    f"Stock already exists for bin {row.bin_code}, SKU {row.sku}, batch {row.batch_number or 'N/A'}"
                )
                continue
            else:
                service.add_stock(
                    bin_id=bin_id,
                    item_id=item_id,
                    quantity=row.quantity,
                    org_id=current_user.organization_id,
                    batch_number=row.batch_number,
                )
                imported += 1
        except Exception as e:
            errors.append(f"Error importing {row.sku} to {row.bin_code}: {str(e)}")

    db.commit()
    return StockImportResult(imported=imported, updated=updated, errors=errors)
