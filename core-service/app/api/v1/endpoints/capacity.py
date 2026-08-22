"""Warehouse capacity endpoints — bin volume/weight capacity and availability."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_READ, WAREHOUSE_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.capacity import (
    AvailableBinResponse,
    BinCapacityResponse,
    BinStateResponse,
    CapacityTreeNode,
)
from app.services.bin_capacity_service import BinCapacityService

router = APIRouter()


@router.get(
    "/bins/available",
    response_model=list[AvailableBinResponse],
    summary="List available bins",
    description="Return availability-filtered candidate bins for put-away or pick.",
)
async def list_available_bins(
    warehouse_id: UUID,
    task_type: str = Query("put_away", description="'put_away' or 'pick'"),
    item_id: UUID | None = Query(None),
    qty: Decimal | None = Query(None),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    service = BinCapacityService(db)
    return service.get_available_bins(
        warehouse_id=warehouse_id,
        org_id=current_user.organization_id,
        task_type=task_type,
        item_id=item_id,
        qty=qty,
    )


@router.get(
    "/bins/{bin_id}",
    response_model=BinCapacityResponse,
    summary="Get one bin's capacity",
    description="Live volume/weight occupancy, percentage, state and availability for one bin.",
)
async def get_bin_capacity(
    bin_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    service = BinCapacityService(db)
    return service.get_bin_capacity(
        bin_id=bin_id,
        org_id=current_user.organization_id,
    )


@router.get(
    "/warehouses/{warehouse_id}/tree",
    response_model=CapacityTreeNode,
    summary="Full capacity rollup tree",
    description="Volume/weight occupancy rolled up warehouse → zone → aisle → bay → level → bin.",
)
async def get_capacity_tree(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    service = BinCapacityService(db)
    return service.get_capacity_tree(
        warehouse_id=warehouse_id,
        org_id=current_user.organization_id,
    )


@router.get(
    "/warehouses/{warehouse_id}/bin-states",
    response_model=list[BinStateResponse],
    summary="Bin states for the 3-D view",
    description="Every bin with its position, colour state and availability.",
)
async def get_bin_states(
    warehouse_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    service = BinCapacityService(db)
    return service.get_bin_states(
        warehouse_id=warehouse_id,
        org_id=current_user.organization_id,
    )


@router.post(
    "/bins/{bin_id}/refresh",
    response_model=BinCapacityResponse,
    summary="Force recompute of a bin",
    description="Recompute and persist a bin's cached capacity state and publish a 3-D event.",
)
async def refresh_bin(
    bin_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_UPDATE)),
    db: Session = Depends(get_db),
):
    service = BinCapacityService(db)
    return service.refresh_bin(
        bin_id=bin_id,
        org_id=current_user.organization_id,
    )
