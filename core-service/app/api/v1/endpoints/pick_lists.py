"""Pick lists API endpoints (Phase 5)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import PICK_LIST_CREATE, PICK_LIST_READ, PICK_LIST_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.sales_order import SalesOrder
from app.schemas.common import PaginationMeta
from app.schemas.pick_list import (
    PickListCreate,
    PickListListItem,
    PickListListResponse,
    PickListResponse,
    PickListUpdate,
)
from app.services.pick_list_service import PickListService

router = APIRouter()


@router.post("", response_model=PickListResponse, status_code=status.HTTP_201_CREATED)
async def create_pick_list(
    body: PickListCreate,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    """Create pick list. Requires pick_list.create."""
    svc = PickListService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return PickListResponse.model_validate(data)


@router.get("", response_model=PickListListResponse)
async def list_pick_lists(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: UUID | None = None,
    status: str | None = Query(
        None, pattern="^(draft|in_progress|completed|cancelled)$"
    ),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """List pick lists. Requires pick_list.read."""
    svc = PickListService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        warehouse_id=warehouse_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    # Look up sales order numbers for pick lists that reference sales orders
    so_ids = [x['reference_id'] for x in items if x.get('reference_type') and x.get('reference_id')]
    so_map: dict = {}
    if so_ids:
        sos = db.query(SalesOrder.id, SalesOrder.sales_order_no).filter(
            SalesOrder.id.in_(so_ids)
        ).all()
        so_map = {str(so.id): so.sales_order_no for so in sos}

    return PickListListResponse(
        pick_lists=[
            PickListListItem(
                id=x['id'],
                organization_id=x['organization_id'],
                pick_list_no=x['pick_list_no'],
                warehouse_id=x['warehouse_id'],
                status=x['status'],
                pick_date=x.get('pick_date'),
                reference_type=x.get('reference_type'),
                reference_id=x.get('reference_id'),
                sales_order_no=so_map.get(str(x['reference_id'])) if x.get('reference_id') else None,
                items_count=x.get('items_count', 0),
                created_at=x['created_at'],
            )
            for x in items
        ],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{pick_list_id}", response_model=PickListResponse)
async def get_pick_list(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    """Get pick list by ID. Requires pick_list.read."""
    svc = PickListService(db)
    data = svc.get_by_id(pick_list_id, current_user.organization_id)
    return PickListResponse.model_validate(data)


@router.put("/{pick_list_id}", response_model=PickListResponse)
async def update_pick_list(
    pick_list_id: UUID,
    body: PickListUpdate,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update pick list. Requires pick_list.update."""
    svc = PickListService(db)
    data = svc.update(
        pick_list_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return PickListResponse.model_validate(data)


@router.delete("/{pick_list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pick_list(
    pick_list_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete pick list. Requires pick_list.update."""
    svc = PickListService(db)
    svc.delete(pick_list_id, current_user.organization_id)
    return None
