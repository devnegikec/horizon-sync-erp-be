"""Packing slip endpoints (internal staging of picked goods).

Mounted under ``/outbound/packing-slips``:

- POST   ``/``                    create from completed order(s)
- GET    ``/``                    list packing slips
- GET    ``/{slip_id}``           detail
- POST   ``/{slip_id}/mark-loading``  draft → loading
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    PICK_LIST_CREATE,
    PICK_LIST_READ,
    PICK_LIST_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.dispatch import DispatchResponse
from app.schemas.packing_slip import (
    CreatePackingSlipRequest,
    PackingSlipListResponse,
    PackingSlipResponse,
    PackingSlipStatusCounts,
)
from app.services.packing_slip_service import PackingSlipService

router = APIRouter()


@router.post(
    "/",
    response_model=PackingSlipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a packing slip from completed orders",
)
async def create_packing_slip(
    data: CreatePackingSlipRequest,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_CREATE)),
    db: Session = Depends(get_db),
):
    service = PackingSlipService(db)
    slip = service.create_from_orders(
        data.order_ids, current_user.organization_id, current_user.id
    )
    return service._to_response(slip)


@router.get(
    "/",
    response_model=PackingSlipListResponse,
    summary="List packing slips",
)
async def list_packing_slips(
    warehouse_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    service = PackingSlipService(db)
    items, pagination = service.list_packing_slips(
        org_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        warehouse_id=warehouse_id,
        status=status_filter,
    )
    status_counts = service.get_status_counts(
        org_id=current_user.organization_id,
        warehouse_id=warehouse_id,
    )
    return {
        "packing_slips": items,
        "pagination": pagination,
        "status_counts": PackingSlipStatusCounts(**status_counts),
    }


@router.get(
    "/{slip_id}",
    response_model=PackingSlipResponse,
    summary="Get packing slip detail",
)
async def get_packing_slip(
    slip_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
):
    service = PackingSlipService(db)
    slip = service.get_packing_slip(slip_id, current_user.organization_id)
    return service._to_response(slip)


@router.post(
    "/{slip_id}/mark-loading",
    response_model=PackingSlipResponse,
    summary="Move a packing slip to loading",
)
async def mark_packing_slip_loading(
    slip_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    service = PackingSlipService(db)
    slip = service.mark_loading(slip_id, current_user.organization_id, current_user.id)
    return service._to_response(slip)


@router.post(
    "/{slip_id}/dispatch",
    response_model=DispatchResponse,
    summary="Dispatch a loading packing slip",
)
async def dispatch_packing_slip(
    slip_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
):
    service = PackingSlipService(db)
    return service.dispatch(slip_id, current_user.organization_id, current_user.id)
