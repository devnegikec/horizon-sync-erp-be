"""Serial numbers and history API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.serial_no import (
    SerialNoCreate,
    SerialNoHistoryCreate,
    SerialNoHistoryResponse,
    SerialNoListItem,
    SerialNoListResponse,
    SerialNoResponse,
    SerialNoUpdate,
)
from app.services.serial_no_service import SerialNoService

router = APIRouter()


@router.post("", response_model=SerialNoResponse, status_code=status.HTTP_201_CREATED)
async def create_serial_no(
    data: SerialNoCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new serial number. Serial must be unique per item."""
    svc = SerialNoService(db)
    return SerialNoResponse.model_validate(
        svc.create(data, current_user.organization_id)
    )


@router.get("", response_model=SerialNoListResponse)
async def list_serial_nos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    search: str | None = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List serial numbers with filters."""
    svc = SerialNoService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return SerialNoListResponse(
        serial_nos=[SerialNoListItem.model_validate(s) for s in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{serial_no_id}", response_model=SerialNoResponse)
async def get_serial_no(
    serial_no_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get serial number by ID."""
    svc = SerialNoService(db)
    return SerialNoResponse.model_validate(
        svc.get_by_id(serial_no_id, current_user.organization_id)
    )


@router.put("/{serial_no_id}", response_model=SerialNoResponse)
async def update_serial_no(
    serial_no_id: UUID,
    data: SerialNoUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a serial number."""
    svc = SerialNoService(db)
    return SerialNoResponse.model_validate(
        svc.update(serial_no_id, data, current_user.organization_id)
    )


@router.delete("/{serial_no_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_serial_no(
    serial_no_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a serial number (hard delete)."""
    SerialNoService(db).delete(serial_no_id, current_user.organization_id)
    return None


# ----- History (sub-resource) -----


@router.get("/{serial_no_id}/history", response_model=list[SerialNoHistoryResponse])
async def list_serial_no_history(
    serial_no_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List history entries for a serial number."""
    svc = SerialNoService(db)
    items = svc.list_history(serial_no_id, current_user.organization_id, limit=limit)
    return [SerialNoHistoryResponse.model_validate(h) for h in items]


@router.post(
    "/{serial_no_id}/history",
    response_model=SerialNoHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_serial_no_history(
    serial_no_id: UUID,
    data: SerialNoHistoryCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a history entry for a serial number (e.g. movement, sale)."""
    svc = SerialNoService(db)
    h = svc.add_history(serial_no_id, data, current_user.organization_id)
    return SerialNoHistoryResponse.model_validate(h)
