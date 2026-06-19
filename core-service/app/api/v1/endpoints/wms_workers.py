"""WMS Worker API endpoints"""

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import WMS_WORKER_PERMISSIONS
from app.core.security import create_access_token
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user, require_permission
from app.schemas.wms_worker import (
    BarcodeLoginRequest,
    BarcodeLoginResponse,
    CredentialsLoginRequest,
    WMSWorkerCreate,
    WMSWorkerListResponse,
    WMSWorkerResponse,
    WMSWorkerUpdate,
)
from app.services.wms_worker_service import WMSWorkerService

router = APIRouter()


@router.post("", response_model=WMSWorkerResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(
    body: WMSWorkerCreate,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Create a new warehouse worker with optional login credentials and barcode."""
    svc = WMSWorkerService(db)
    worker = svc.create(
        data=body.model_dump(),
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    return WMSWorkerResponse.model_validate(worker)


@router.get("", response_model=WMSWorkerListResponse)
async def list_workers(
    warehouse_id: UUID | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """List warehouse workers with optional filters."""
    svc = WMSWorkerService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return WMSWorkerListResponse(
        workers=[WMSWorkerResponse.model_validate(w) for w in items],
        pagination=pagination,
    )


@router.get("/{worker_id}", response_model=WMSWorkerResponse)
async def get_worker(
    worker_id: UUID,
    current_user: CurrentUser = Depends(require_permission("warehouse.read")),
    db: Session = Depends(get_db),
):
    """Get a specific warehouse worker by ID."""
    svc = WMSWorkerService(db)
    worker = svc.get_by_id(worker_id, current_user.organization_id)
    return WMSWorkerResponse.model_validate(worker)


@router.patch("/{worker_id}", response_model=WMSWorkerResponse)
async def update_worker(
    worker_id: UUID,
    body: WMSWorkerUpdate,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Update a warehouse worker."""
    svc = WMSWorkerService(db)
    worker = svc.update(
        worker_id=worker_id,
        data=body.model_dump(exclude_none=True),
        organization_id=current_user.organization_id,
    )
    return WMSWorkerResponse.model_validate(worker)


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worker(
    worker_id: UUID,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Soft-delete (disable) a warehouse worker."""
    svc = WMSWorkerService(db)
    svc.delete(worker_id, current_user.organization_id)
    return None


@router.post("/{worker_id}/regenerate-barcode", response_model=WMSWorkerResponse)
async def regenerate_barcode(
    worker_id: UUID,
    current_user: CurrentUser = Depends(require_permission("warehouse.manage")),
    db: Session = Depends(get_db),
):
    """Generate a new barcode for a worker."""
    svc = WMSWorkerService(db)
    worker = svc.regenerate_barcode(worker_id, current_user.organization_id)
    return WMSWorkerResponse.model_validate(worker)


@router.post("/login/barcode", response_model=BarcodeLoginResponse)
async def barcode_login(
    body: BarcodeLoginRequest,
    db: Session = Depends(get_db),
):
    """Login a worker using their barcode/QR code. Returns a long-lived access token for mobile."""
    from app.config import settings

    svc = WMSWorkerService(db)
    worker = svc.authenticate_by_barcode(body.barcode)
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid barcode or worker inactive")

    worker_token_ttl_seconds = settings.wms_worker_token_expire_hours * 60 * 60

    access_token = create_access_token(
        {
            "sub": str(worker.id),
            "token_use": "wms_worker",
            "client_type": "mobile",
            "organization_id": str(worker.organization_id),
            "warehouse_id": str(worker.warehouse_id),
            "role": worker.role,
            "permissions": WMS_WORKER_PERMISSIONS,
        },
        expires_delta=timedelta(seconds=worker_token_ttl_seconds),
    )

    return BarcodeLoginResponse(
        access_token=access_token,
        expires_in=worker_token_ttl_seconds,
        worker=WMSWorkerResponse.model_validate(worker),
    )


@router.get("/login/qr")
async def qr_login(
    code: str = Query(..., description="Worker QR code value"),
    db: Session = Depends(get_db),
):
    """Login a worker via QR code scan (GET endpoint for mobile browser).

    When a worker scans their QR code, the phone opens this URL directly.
    Returns a JSON token response the mobile client can use for the session.
    """
    from app.config import settings

    svc = WMSWorkerService(db)
    worker = svc.authenticate_by_barcode(code)
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid QR code or worker inactive")

    worker_token_ttl_seconds = settings.wms_worker_token_expire_hours * 60 * 60

    access_token = create_access_token(
        {
            "sub": str(worker.id),
            "token_use": "wms_worker",
            "client_type": "mobile",
            "organization_id": str(worker.organization_id),
            "warehouse_id": str(worker.warehouse_id),
            "role": worker.role,
            "permissions": WMS_WORKER_PERMISSIONS,
        },
        expires_delta=timedelta(seconds=worker_token_ttl_seconds),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": worker_token_ttl_seconds,
        "worker_id": str(worker.id),
        "worker_name": worker.display_name or f"{worker.first_name} {worker.last_name}",
        "warehouse_id": str(worker.warehouse_id),
    }


@router.post("/login/credentials", response_model=BarcodeLoginResponse)
async def credentials_login(
    body: CredentialsLoginRequest,
    db: Session = Depends(get_db),
):
    """Login a worker using username/password (fallback when QR scan fails).

    Returns the same token format as barcode/QR login, restricted to mobile client.
    """
    from app.config import settings

    svc = WMSWorkerService(db)
    worker = svc.authenticate_by_credentials(body.username, body.password)
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    worker_token_ttl_seconds = settings.wms_worker_token_expire_hours * 60 * 60

    access_token = create_access_token(
        {
            "sub": str(worker.id),
            "token_use": "wms_worker",
            "client_type": "mobile",
            "organization_id": str(worker.organization_id),
            "warehouse_id": str(worker.warehouse_id),
            "role": worker.role,
            "permissions": WMS_WORKER_PERMISSIONS,
        },
        expires_delta=timedelta(seconds=worker_token_ttl_seconds),
    )

    return BarcodeLoginResponse(
        access_token=access_token,
        expires_in=worker_token_ttl_seconds,
        worker=WMSWorkerResponse.model_validate(worker),
    )
