"""QR Product Settings API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user, require_permission
from app.schemas.qr_product_setting import (
    QRProductSettingCreate,
    QRProductSettingListResponse,
    QRProductSettingResponse,
    QRProductSettingUpdate,
)
from app.services.qr_product_setting_service import QRProductSettingService

router = APIRouter()


@router.post(
    "",
    response_model=QRProductSettingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a QR product setting",
)
async def create_setting(
    data: QRProductSettingCreate,
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
    db: Session = Depends(get_db),
):
    svc = QRProductSettingService(db)
    setting = svc.create(data, current_user.organization_id, current_user.id)
    return QRProductSettingResponse.model_validate(setting)


@router.get(
    "",
    response_model=QRProductSettingListResponse,
    summary="List QR product settings",
    description="Filter by setting_type to get only serial_prefix, channel, destination, or shelf_life options.",
)
async def list_settings(
    setting_type: str | None = Query(None, description="serial_prefix | channel | destination | shelf_life"),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductSettingService(db)
    result = svc.list_settings(
        current_user.organization_id, setting_type, is_active, search, page, page_size
    )
    return QRProductSettingListResponse(
        settings=[QRProductSettingResponse.model_validate(s) for s in result["settings"]],
        pagination=result["pagination"],
    )


@router.get(
    "/{setting_id}",
    response_model=QRProductSettingResponse,
    summary="Get a QR product setting",
)
async def get_setting(
    setting_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductSettingService(db)
    return QRProductSettingResponse.model_validate(
        svc.get_setting(setting_id, current_user.organization_id)
    )


@router.patch(
    "/{setting_id}",
    response_model=QRProductSettingResponse,
    summary="Update a QR product setting",
)
async def update_setting(
    setting_id: UUID,
    data: QRProductSettingUpdate,
    current_user: CurrentUser = Depends(require_permission("qr_product.update")),
    db: Session = Depends(get_db),
):
    svc = QRProductSettingService(db)
    setting = svc.update_setting(
        setting_id, data, current_user.organization_id, current_user.id
    )
    return QRProductSettingResponse.model_validate(setting)


@router.delete(
    "/{setting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a QR product setting",
)
async def delete_setting(
    setting_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.delete")),
    db: Session = Depends(get_db),
):
    svc = QRProductSettingService(db)
    svc.delete_setting(setting_id, current_user.organization_id, current_user.id)
