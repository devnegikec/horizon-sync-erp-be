"""WMS Device API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.wms_device import (
    WMSDeviceCreate,
    WMSDeviceListResponse,
    WMSDeviceResponse,
    WMSDeviceUpdate,
)
from app.services.wms_device_service import WMSDeviceService

router = APIRouter()


@router.post("", response_model=WMSDeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    body: WMSDeviceCreate,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Create a new warehouse device."""
    svc = WMSDeviceService(db)
    device = svc.create(
        data=body.model_dump(),
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    return WMSDeviceResponse.model_validate(device)


@router.get("", response_model=WMSDeviceListResponse)
async def list_devices(
    warehouse_id: UUID | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """List warehouse devices with optional filters."""
    svc = WMSDeviceService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return WMSDeviceListResponse(
        devices=[WMSDeviceResponse.model_validate(d) for d in items],
        pagination=pagination,
    )


@router.get("/{device_id}", response_model=WMSDeviceResponse)
async def get_device(
    device_id: UUID,
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """Get a specific warehouse device by ID."""
    svc = WMSDeviceService(db)
    device = svc.get_by_id(device_id, current_user.organization_id)
    return WMSDeviceResponse.model_validate(device)


@router.patch("/{device_id}", response_model=WMSDeviceResponse)
async def update_device(
    device_id: UUID,
    body: WMSDeviceUpdate,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Update a warehouse device."""
    svc = WMSDeviceService(db)
    device = svc.update(
        device_id=device_id,
        data=body.model_dump(exclude_none=True),
        organization_id=current_user.organization_id,
    )
    return WMSDeviceResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: UUID,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Delete a warehouse device."""
    svc = WMSDeviceService(db)
    svc.delete(device_id, current_user.organization_id)
    return None
