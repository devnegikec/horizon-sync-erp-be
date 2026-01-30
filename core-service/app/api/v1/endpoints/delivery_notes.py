"""Delivery notes API endpoints (Phase 5)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    DELIVERY_NOTE_CREATE,
    DELIVERY_NOTE_READ,
    DELIVERY_NOTE_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.delivery_note import (
    DeliveryNoteCreate,
    DeliveryNoteListItem,
    DeliveryNoteListResponse,
    DeliveryNoteResponse,
    DeliveryNoteUpdate,
)
from app.services.delivery_note_service import DeliveryNoteService

router = APIRouter()


@router.post(
    "", response_model=DeliveryNoteResponse, status_code=status.HTTP_201_CREATED
)
async def create_delivery_note(
    body: DeliveryNoteCreate,
    current_user: CurrentUser = Depends(require_permission(DELIVERY_NOTE_CREATE)),
    db: Session = Depends(get_db),
):
    """Create delivery note. Requires delivery_note.create."""
    svc = DeliveryNoteService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return DeliveryNoteResponse.model_validate(data)


@router.get("", response_model=DeliveryNoteListResponse)
async def list_delivery_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: UUID | None = None,
    status: str | None = Query(None, pattern="^(draft|submitted|cancelled)$"),
    sort_by: str = Query("delivery_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(DELIVERY_NOTE_READ)),
    db: Session = Depends(get_db),
):
    """List delivery notes. Requires delivery_note.read."""
    svc = DeliveryNoteService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return DeliveryNoteListResponse(
        delivery_notes=[DeliveryNoteListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{delivery_note_id}", response_model=DeliveryNoteResponse)
async def get_delivery_note(
    delivery_note_id: UUID,
    current_user: CurrentUser = Depends(require_permission(DELIVERY_NOTE_READ)),
    db: Session = Depends(get_db),
):
    """Get delivery note by ID. Requires delivery_note.read."""
    svc = DeliveryNoteService(db)
    data = svc.get_by_id(delivery_note_id, current_user.organization_id)
    return DeliveryNoteResponse.model_validate(data)


@router.put("/{delivery_note_id}", response_model=DeliveryNoteResponse)
async def update_delivery_note(
    delivery_note_id: UUID,
    body: DeliveryNoteUpdate,
    current_user: CurrentUser = Depends(require_permission(DELIVERY_NOTE_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update delivery note. Requires delivery_note.update."""
    svc = DeliveryNoteService(db)
    data = svc.update(
        delivery_note_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return DeliveryNoteResponse.model_validate(data)


@router.delete("/{delivery_note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_note(
    delivery_note_id: UUID,
    current_user: CurrentUser = Depends(require_permission(DELIVERY_NOTE_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete delivery note. Requires delivery_note.update."""
    svc = DeliveryNoteService(db)
    svc.delete(delivery_note_id, current_user.organization_id)
    return None
