"""Destinations / Markets endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.database import get_db
from app.schemas.destination_market import (
    DestinationCurrencyResponse,
    DestinationMarketCreate,
    DestinationMarketListResponse,
    DestinationMarketResponse,
    DestinationMarketUpdate,
)
from app.services.destination_market_service import DestinationMarketService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> DestinationMarketService:
    return DestinationMarketService(db)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=DestinationMarketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a destination market",
)
def create_market(
    data: DestinationMarketCreate,
    service: DestinationMarketService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.create(data, org_id, user_id)


@router.get(
    "",
    response_model=DestinationMarketListResponse,
    summary="List destination markets",
)
def list_markets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    country: str | None = Query(None, description="Filter by country name"),
    search: str | None = Query(None, description="Search by name or code"),
    service: DestinationMarketService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_markets(org_id, page, page_size, is_active, country, search)


@router.get(
    "/{market_id}",
    response_model=DestinationMarketResponse,
    summary="Get a destination market",
)
def get_market(
    market_id: UUID,
    service: DestinationMarketService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_market(market_id, org_id)


@router.patch(
    "/{market_id}",
    response_model=DestinationMarketResponse,
    summary="Update a destination market",
)
def update_market(
    market_id: UUID,
    data: DestinationMarketUpdate,
    service: DestinationMarketService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.update_market(market_id, data, org_id, user_id)


@router.delete(
    "/{market_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a destination market",
)
def delete_market(
    market_id: UUID,
    service: DestinationMarketService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    service.delete_market(market_id, org_id, user_id)


# ── Currency by Destination ───────────────────────────────────────────────────

@router.get(
    "/{market_id}/currency",
    response_model=DestinationCurrencyResponse,
    summary="Get currency details for a destination market",
    description=(
        "Returns the market's linked currency and the latest exchange rate "
        "to the organization's base currency."
    ),
)
def get_market_currency(
    market_id: UUID,
    service: DestinationMarketService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_currency_for_market(market_id, org_id)
