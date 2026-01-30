"""Journal entries API endpoints (Phase 7)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    JOURNAL_ENTRY_CREATE,
    JOURNAL_ENTRY_READ,
    JOURNAL_ENTRY_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.journal_entry import (
    JournalEntryCreate,
    JournalEntryListItem,
    JournalEntryListResponse,
    JournalEntryResponse,
    JournalEntryUpdate,
)
from app.services.journal_entry_service import JournalEntryService

router = APIRouter()


@router.post(
    "", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED
)
async def create_journal_entry(
    body: JournalEntryCreate,
    current_user: CurrentUser = Depends(require_permission(JOURNAL_ENTRY_CREATE)),
    db: Session = Depends(get_db),
):
    """Create journal entry. Requires journal_entry.create."""
    svc = JournalEntryService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return JournalEntryResponse.model_validate(data)


@router.get("", response_model=JournalEntryListResponse)
async def list_journal_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(draft|posted|cancelled)$"),
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(JOURNAL_ENTRY_READ)),
    db: Session = Depends(get_db),
):
    """List journal entries. Requires journal_entry.read."""
    svc = JournalEntryService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return JournalEntryListResponse(
        journal_entries=[JournalEntryListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    entry_id: UUID,
    current_user: CurrentUser = Depends(require_permission(JOURNAL_ENTRY_READ)),
    db: Session = Depends(get_db),
):
    """Get journal entry by ID. Requires journal_entry.read."""
    svc = JournalEntryService(db)
    data = svc.get_by_id(entry_id, current_user.organization_id)
    return JournalEntryResponse.model_validate(data)


@router.put("/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    entry_id: UUID,
    body: JournalEntryUpdate,
    current_user: CurrentUser = Depends(require_permission(JOURNAL_ENTRY_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update journal entry. Requires journal_entry.update."""
    svc = JournalEntryService(db)
    data = svc.update(
        entry_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return JournalEntryResponse.model_validate(data)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: UUID,
    current_user: CurrentUser = Depends(require_permission(JOURNAL_ENTRY_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete journal entry. Requires journal_entry.update."""
    svc = JournalEntryService(db)
    svc.delete(entry_id, current_user.organization_id)
    return None
