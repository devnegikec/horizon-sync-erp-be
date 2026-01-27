"""Batch management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.batch import (
    BatchCreate,
    BatchListItem,
    BatchListResponse,
    BatchResponse,
    BatchUpdate,
)
from app.schemas.common import PaginationMeta
from app.services.batch_service import BatchService

router = APIRouter()


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    data: BatchCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new batch. Batch number must be unique per item."""
    svc = BatchService(db)
    batch = svc.create(data, current_user.organization_id)
    return BatchResponse.model_validate(batch)


@router.get("", response_model=BatchListResponse)
async def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = Query(None, description="Filter by item ID"),
    status: str | None = Query(None, description="active, expired, consumed"),
    search: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List batches with pagination and filters."""
    svc = BatchService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        item_id=item_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return BatchListResponse(
        batches=[BatchListItem.model_validate(b) for b in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get batch by ID."""
    svc = BatchService(db)
    return BatchResponse.model_validate(
        svc.get_by_id(batch_id, current_user.organization_id)
    )


@router.put("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    data: BatchUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a batch."""
    svc = BatchService(db)
    return BatchResponse.model_validate(
        svc.update(batch_id, data, current_user.organization_id)
    )


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a batch (hard delete)."""
    BatchService(db).delete(batch_id, current_user.organization_id)
    return None
