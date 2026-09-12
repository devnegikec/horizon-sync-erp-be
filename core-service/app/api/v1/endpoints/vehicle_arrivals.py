"""Vehicle arrival API endpoints for inbound receiving."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    RECEIVING_SLIP_CREATE,
    RECEIVING_SLIP_UPDATE,
    WAREHOUSE_READ,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.vehicle import (
    AsnOrderRef,
    VehicleArrivalCreate,
    VehicleArrivalLinkRequest,
    VehicleArrivalListItem,
    VehicleArrivalListResponse,
    VehicleArrivalResponse,
    VehicleArrivalUpdate,
    VehicleInfo,
)
from app.services.vehicle_service import VehicleArrivalService

router = APIRouter()


def _to_response(arrival) -> VehicleArrivalResponse:
    vehicle = arrival.vehicle
    return VehicleArrivalResponse(
        id=arrival.id,
        organization_id=arrival.organization_id,
        vehicle=(
            VehicleInfo(
                id=vehicle.id,
                vehicle_no=vehicle.vehicle_no,
                driver_name=vehicle.driver_name,
                driver_contact=vehicle.driver_contact,
                transporter=vehicle.transporter,
            )
            if vehicle
            else None
        ),
        warehouse_id=arrival.warehouse_id,
        dock=arrival.dock,
        status=arrival.status,
        arrived_at=arrival.arrived_at,
        notes=arrival.notes,
        asn_orders=[
            AsnOrderRef(id=a.id, asn_order_no=a.asn_order_no, status=a.status)
            for a in arrival.asn_orders
        ],
        created_by=arrival.created_by,
        created_at=arrival.created_at,
        updated_at=arrival.updated_at,
    )


@router.post(
    "",
    response_model=VehicleArrivalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register vehicle arrival",
)
async def register_vehicle_arrival(
    body: VehicleArrivalCreate,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """Register a vehicle arrival and optionally link one or more ASN orders."""
    svc = VehicleArrivalService(db)
    arrival = svc.create(
        body.model_dump(),
        current_user.organization_id,
        current_user.id,
    )
    return _to_response(arrival)


@router.get("", response_model=VehicleArrivalListResponse)
async def list_vehicle_arrivals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: UUID | None = Query(None),
    status: str | None = Query(None, pattern="^(arrived|unloaded|closed)$"),
    search: str | None = Query(None, description="Search by vehicle number"),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """List vehicle arrivals for the user's organization."""
    svc = VehicleArrivalService(db)
    arrivals, pagination = svc.list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        warehouse_id=warehouse_id,
        status=status,
        search=search,
    )
    items = [
        VehicleArrivalListItem(
            id=a.id,
            vehicle_no=a.vehicle.vehicle_no if a.vehicle else None,
            driver_name=a.vehicle.driver_name if a.vehicle else None,
            driver_contact=a.vehicle.driver_contact if a.vehicle else None,
            transporter=a.vehicle.transporter if a.vehicle else None,
            warehouse_id=a.warehouse_id,
            dock=a.dock,
            notes=a.notes,
            status=a.status,
            arrived_at=a.arrived_at,
            asn_order_count=len(a.asn_orders),
            receiving_slip_count=len(a.receiving_slips),
        )
        for a in arrivals
    ]
    return VehicleArrivalListResponse(
        vehicle_arrivals=items,
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{arrival_id}", response_model=VehicleArrivalResponse)
async def get_vehicle_arrival(
    arrival_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Get a vehicle arrival by ID."""
    svc = VehicleArrivalService(db)
    arrival = svc.get(arrival_id, current_user.organization_id)
    return _to_response(arrival)


@router.patch("/{arrival_id}", response_model=VehicleArrivalResponse)
async def update_vehicle_arrival(
    arrival_id: UUID,
    body: VehicleArrivalUpdate,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update editable vehicle arrival details (vehicle no., driver, transporter, dock, notes)."""
    svc = VehicleArrivalService(db)
    arrival = svc.update(
        arrival_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
    )
    return _to_response(arrival)


@router.post("/{arrival_id}/asns", response_model=VehicleArrivalResponse)
async def link_asns_to_arrival(
    arrival_id: UUID,
    body: VehicleArrivalLinkRequest,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """Link one or more ASN orders to an existing vehicle arrival."""
    svc = VehicleArrivalService(db)
    arrival = svc.link_asns(
        arrival_id,
        [UUID(str(x)) for x in body.asn_order_ids],
        current_user.organization_id,
    )
    return _to_response(arrival)


@router.delete(
    "/{arrival_id}/asns/{asn_order_id}",
    response_model=VehicleArrivalResponse,
)
async def unlink_asn_from_arrival(
    arrival_id: UUID,
    asn_order_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RECEIVING_SLIP_CREATE)),
    db: Session = Depends(get_db),
):
    """Unlink an ASN order from a vehicle arrival."""
    svc = VehicleArrivalService(db)
    arrival = svc.unlink_asn(arrival_id, asn_order_id, current_user.organization_id)
    return _to_response(arrival)
