"""Stock settings API - one per organization"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.stock_settings import (
    StockSettingsCreate,
    StockSettingsResponse,
    StockSettingsUpdate,
)
from app.services.stock_settings_service import StockSettingsService

router = APIRouter()


@router.get("", response_model=StockSettingsResponse)
async def get_stock_settings(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get stock settings for the current organization. 404 if not created yet."""
    svc = StockSettingsService(db)
    s = svc.get(current_user.organization_id)
    return StockSettingsResponse.model_validate(s)


@router.put("", response_model=StockSettingsResponse)
async def upsert_stock_settings(
    data: StockSettingsUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create or update stock settings for the current organization (upsert)."""
    svc = StockSettingsService(db)
    s = svc.upsert(data, current_user.organization_id, current_user.id)
    return StockSettingsResponse.model_validate(s)


@router.post(
    "", response_model=StockSettingsResponse, status_code=status.HTTP_201_CREATED
)
async def create_stock_settings(
    data: StockSettingsCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create or overwrite stock settings for the current organization."""
    svc = StockSettingsService(db)
    s = svc.create(data, current_user.organization_id, current_user.id)
    return StockSettingsResponse.model_validate(s)
