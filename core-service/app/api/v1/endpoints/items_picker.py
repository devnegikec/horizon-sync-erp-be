"""Item picker API - separate router to avoid /picker matching /{item_id}"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.item import ItemPickerListResponse
from app.services.item_service import ItemService

router = APIRouter()


@router.get(
    "",
    response_model=ItemPickerListResponse,
    summary="Item picker",
    description="Search items for picker/dropdown with stock levels, item group, and tax info",
)
async def item_picker(
    search: str | None = Query(
        None, description="Search by item name, item code, or barcode"
    ),
    warehouse_id: UUID | None = Query(
        None, description="Filter stock levels to a specific warehouse"
    ),
    limit: int = Query(
        20, ge=1, le=50, description="Maximum number of items to return"
    ),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Search items for picker/dropdown.

    Returns items matching the search term within the user's organization,
    including aggregated stock levels, item group, and sales tax template info.

    **Query Parameters:**
    - **search**: Optional search term (item name, code, or barcode)
    - **warehouse_id**: Optional warehouse UUID — stock levels shown only for that warehouse
    - **limit**: Max items to return (default: 20, max: 50)

    **Returns:** List of items with stock_levels, item_group, and tax_info
    """
    item_service = ItemService(db)
    items = item_service.get_items_for_picker(
        organization_id=current_user.organization_id,
        search=search,
        limit=limit,
        warehouse_id=warehouse_id,
    )
    return ItemPickerListResponse(items=items)
