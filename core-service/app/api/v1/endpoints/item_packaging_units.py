"""Item Packaging Units API endpoints

Provides CRUD operations for packaging units per item.
Packaging units define how an item is packaged (e.g., Each, Box of 12, Pallet of 144)
with physical dimensions and a conversion factor to base units (Eaches).

Requirements: 2.6
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.item_packaging_unit import (
    ItemPackagingUnitCreate,
    ItemPackagingUnitListResponse,
    ItemPackagingUnitResponse,
    ItemPackagingUnitUpdate,
)
from app.services.item_packaging_unit_service import ItemPackagingUnitService

router = APIRouter()


@router.get(
    "",
    response_model=ItemPackagingUnitListResponse,
    status_code=status.HTTP_200_OK,
    summary="List packaging units for an item",
    description="Get a paginated list of packaging units for a specific item.",
)
async def list_packaging_units(
    item_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    is_active: Optional[bool] = Query(
        None, description="Filter by active status (true/false)"
    ),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all packaging units for an item with pagination.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **is_active**: Optional filter by active status

    **Returns:** Paginated list of packaging units with pagination metadata
    """
    service = ItemPackagingUnitService()
    result = service.list_packaging_units(
        item_id=item_id,
        org_id=current_user.organization_id,
        db=db,
        page=page,
        page_size=page_size,
        is_active=is_active,
    )

    packaging_units = [
        ItemPackagingUnitResponse.model_validate(pu)
        for pu in result["packaging_units"]
    ]

    return ItemPackagingUnitListResponse(
        packaging_units=packaging_units,
        pagination=result["pagination"],
    )


@router.post(
    "",
    response_model=ItemPackagingUnitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a packaging unit for an item",
    description=(
        "Create a new packaging unit for a specific item. "
        "Returns 404 if the item is not found, 409 if a packaging unit with the same "
        "unit_name already exists for this item, and 422 if conversion_factor <= 0."
    ),
)
async def create_packaging_unit(
    item_id: UUID,
    data: ItemPackagingUnitCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new packaging unit for an item.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID

    **Request Body:**
    - **unit_name**: Name of the packaging unit (e.g. 'Box of 12') — required
    - **conversion_factor**: Number of base units (Eaches) in this packaging unit — must be > 0
    - **qr_identifier**: Optional unique QR identifier for this packaging unit
    - **length_mm**, **width_mm**, **height_mm**: Optional physical dimensions in mm
    - **weight_grams**: Optional weight in grams
    - **is_base_unit**: Whether this is the base unit (default: false)
    - **is_active**: Whether this packaging unit is active (default: true)

    **Returns:** Created packaging unit details

    **Errors:**
    - **404**: Item not found
    - **409**: Packaging unit with the same unit_name already exists for this item
    - **422**: conversion_factor <= 0
    """
    service = ItemPackagingUnitService()
    packaging_unit = service.create_packaging_unit(
        item_id=item_id,
        data=data,
        org_id=current_user.organization_id,
        db=db,
    )
    return ItemPackagingUnitResponse.model_validate(packaging_unit)


@router.patch(
    "/{id}",
    response_model=ItemPackagingUnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a packaging unit",
    description=(
        "Partially update a packaging unit. All fields are optional. "
        "Returns 404 if the packaging unit is not found or belongs to a different item/org."
    ),
)
async def update_packaging_unit(
    item_id: UUID,
    id: UUID,
    data: ItemPackagingUnitUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Partially update a packaging unit.

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID
    - **id**: Packaging unit UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated packaging unit details

    **Errors:**
    - **404**: Packaging unit not found or belongs to a different item/org
    """
    service = ItemPackagingUnitService()
    packaging_unit = service.update_packaging_unit(
        item_id=item_id,
        unit_id=id,
        data=data,
        org_id=current_user.organization_id,
        db=db,
    )
    return ItemPackagingUnitResponse.model_validate(packaging_unit)


@router.delete(
    "/{id}",
    response_model=ItemPackagingUnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a packaging unit",
    description=(
        "Soft-delete a packaging unit by setting is_active = false. "
        "Does not hard-delete the row to preserve FK references in scan_session_items "
        "and bin_stock_levels. Returns 404 if not found."
    ),
)
async def delete_packaging_unit(
    item_id: UUID,
    id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete a packaging unit (sets is_active = false).

    Requires authentication.

    **Path Parameters:**
    - **item_id**: Item UUID
    - **id**: Packaging unit UUID

    **Returns:** Updated packaging unit with is_active = false

    **Errors:**
    - **404**: Packaging unit not found
    """
    service = ItemPackagingUnitService()
    packaging_unit = service.soft_delete_packaging_unit(
        item_id=item_id,
        unit_id=id,
        org_id=current_user.organization_id,
        db=db,
    )
    return ItemPackagingUnitResponse.model_validate(packaging_unit)
