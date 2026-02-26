"""Currency Master management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    CURRENCY_CREATE,
    CURRENCY_DELETE,
    CURRENCY_READ,
    CURRENCY_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.currency_master import (
    CurrencyMasterCreate,
    CurrencyMasterListResponse,
    CurrencyMasterResponse,
    CurrencyMasterUpdate,
)
from app.services.currency_master_service import CurrencyMasterService

router = APIRouter()


@router.post(
    "",
    response_model=CurrencyMasterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Currency",
    description="Create a new currency",
)
async def create_currency(
    body: CurrencyMasterCreate,
    current_user: CurrentUser = Depends(require_permission(CURRENCY_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a new Currency. Requires currency.create permission."""
    svc = CurrencyMasterService(db)
    currency = svc.create_currency(
        currency_data=body,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return CurrencyMasterResponse.model_validate(currency)


@router.get(
    "",
    response_model=CurrencyMasterListResponse,
    summary="List Currencies",
    description="Get paginated list of currencies with optional search",
)
async def list_currencies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search in code or name"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(require_permission(CURRENCY_READ)),
    db: Session = Depends(get_db),
):
    """List Currencies with pagination and search. Requires currency.read permission."""
    svc = CurrencyMasterService(db)
    currencies, pagination = svc.list_currencies(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return CurrencyMasterListResponse(
        currencies=[CurrencyMasterResponse.model_validate(c) for c in currencies],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{currency_id}",
    response_model=CurrencyMasterResponse,
    summary="Get Currency",
    description="Get currency details by ID",
)
async def get_currency(
    currency_id: UUID,
    current_user: CurrentUser = Depends(require_permission(CURRENCY_READ)),
    db: Session = Depends(get_db),
):
    """Get Currency by ID. Requires currency.read permission."""
    svc = CurrencyMasterService(db)
    currency = svc.get_currency(
        currency_id=currency_id,
        organization_id=current_user.organization_id,
    )
    return CurrencyMasterResponse.model_validate(currency)


@router.patch(
    "/{currency_id}",
    response_model=CurrencyMasterResponse,
    summary="Update Currency",
    description="Update an existing currency",
)
async def update_currency(
    currency_id: UUID,
    body: CurrencyMasterUpdate,
    current_user: CurrentUser = Depends(require_permission(CURRENCY_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update a Currency. Requires currency.update permission."""
    svc = CurrencyMasterService(db)
    currency = svc.update_currency(
        currency_id=currency_id,
        currency_data=body,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return CurrencyMasterResponse.model_validate(currency)


@router.delete(
    "/{currency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Currency",
    description="Soft delete a currency",
)
async def delete_currency(
    currency_id: UUID,
    current_user: CurrentUser = Depends(require_permission(CURRENCY_DELETE)),
    db: Session = Depends(get_db),
):
    """Soft delete a Currency. Requires currency.delete permission."""
    svc = CurrencyMasterService(db)
    svc.delete_currency(
        currency_id=currency_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
