"""Exchange Rate management API endpoints"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    EXCHANGE_RATE_CREATE,
    EXCHANGE_RATE_DELETE,
    EXCHANGE_RATE_READ,
    EXCHANGE_RATE_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.exchange_rate import (
    ExchangeRateCreate,
    ExchangeRateListResponse,
    ExchangeRateResponse,
    ExchangeRateUpdate,
)
from app.services.exchange_rate_service import ExchangeRateService

router = APIRouter()


@router.post(
    "",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Exchange Rate",
    description="Create a new exchange rate (upserts if same org/pair/date exists)",
)
async def create_exchange_rate(
    body: ExchangeRateCreate,
    current_user: CurrentUser = Depends(require_permission(EXCHANGE_RATE_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a new Exchange Rate. Requires exchange_rate.create permission."""
    svc = ExchangeRateService(db)
    exchange_rate = svc.create_exchange_rate(
        rate_data=body,
        organization_id=current_user.organization_id,
    )
    return ExchangeRateResponse.model_validate(exchange_rate)


@router.get(
    "",
    response_model=ExchangeRateListResponse,
    summary="List Exchange Rates",
    description="Get paginated list of exchange rates with optional filters",
)
async def list_exchange_rates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    from_currency: str | None = Query(None, description="Filter by source currency"),
    to_currency: str | None = Query(None, description="Filter by target currency"),
    start_date: date | None = Query(None, description="Filter by start of effective date range"),
    end_date: date | None = Query(None, description="Filter by end of effective date range"),
    sort_by: str = Query("effective_date", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(require_permission(EXCHANGE_RATE_READ)),
    db: Session = Depends(get_db),
):
    """List Exchange Rates with pagination and filters. Requires exchange_rate.read permission."""
    svc = ExchangeRateService(db)
    exchange_rates, pagination = svc.list_exchange_rates(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        from_currency=from_currency,
        to_currency=to_currency,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ExchangeRateListResponse(
        exchange_rates=[ExchangeRateResponse.model_validate(r) for r in exchange_rates],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{rate_id}",
    response_model=ExchangeRateResponse,
    summary="Get Exchange Rate",
    description="Get exchange rate details by ID",
)
async def get_exchange_rate(
    rate_id: UUID,
    current_user: CurrentUser = Depends(require_permission(EXCHANGE_RATE_READ)),
    db: Session = Depends(get_db),
):
    """Get Exchange Rate by ID. Requires exchange_rate.read permission."""
    svc = ExchangeRateService(db)
    exchange_rate = svc.get_exchange_rate(
        rate_id=rate_id,
        organization_id=current_user.organization_id,
    )
    return ExchangeRateResponse.model_validate(exchange_rate)


@router.put(
    "/{rate_id}",
    response_model=ExchangeRateResponse,
    summary="Update Exchange Rate",
    description="Update an existing exchange rate",
)
async def update_exchange_rate(
    rate_id: UUID,
    body: ExchangeRateUpdate,
    current_user: CurrentUser = Depends(require_permission(EXCHANGE_RATE_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update an Exchange Rate. Requires exchange_rate.update permission."""
    svc = ExchangeRateService(db)
    exchange_rate = svc.update_exchange_rate(
        rate_id=rate_id,
        rate_data=body,
        organization_id=current_user.organization_id,
    )
    return ExchangeRateResponse.model_validate(exchange_rate)


@router.delete(
    "/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Exchange Rate",
    description="Hard delete an exchange rate",
)
async def delete_exchange_rate(
    rate_id: UUID,
    current_user: CurrentUser = Depends(require_permission(EXCHANGE_RATE_DELETE)),
    db: Session = Depends(get_db),
):
    """Hard delete an Exchange Rate. Requires exchange_rate.delete permission."""
    svc = ExchangeRateService(db)
    svc.delete_exchange_rate(
        rate_id=rate_id,
        organization_id=current_user.organization_id,
    )
    return None
