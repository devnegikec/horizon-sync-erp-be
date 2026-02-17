"""Currency and Exchange Rate management API endpoints"""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.exchange_rate import ExchangeRate
from app.services.currency_service import CurrencyService

router = APIRouter()


# Schemas
class ExchangeRateResponse(BaseModel):
    """Exchange rate response schema"""

    id: UUID
    from_currency: str
    to_currency: str
    rate: Decimal
    effective_date: date
    created_at: str

    class Config:
        from_attributes = True


class ExchangeRateCreate(BaseModel):
    """Exchange rate creation schema"""

    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    rate: Decimal = Field(..., gt=0)
    effective_date: date


class ExchangeRateUpdate(BaseModel):
    """Exchange rate update schema"""

    rate: Decimal = Field(..., gt=0)
    effective_date: date


class BaseCurrencyResponse(BaseModel):
    """Base currency response schema"""

    base_currency: str


class BaseCurrencyUpdate(BaseModel):
    """Base currency update schema"""

    base_currency: str = Field(..., min_length=3, max_length=3)


class CurrencyConversionRequest(BaseModel):
    """Currency conversion request schema"""

    amount: Decimal
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    effective_date: Optional[date] = None


class CurrencyConversionResponse(BaseModel):
    """Currency conversion response schema"""

    amount: Decimal
    from_currency: str
    to_currency: str
    rate: Decimal
    converted_amount: Decimal
    effective_date: date


# Base Currency Endpoints


@router.get(
    "/base-currency",
    response_model=BaseCurrencyResponse,
    summary="Get base currency",
    description="Get the organization's base currency",
)
async def get_base_currency(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the organization's base currency.

    Requires authentication.

    **Returns:** Base currency code
    """
    service = CurrencyService(db)
    base_currency = service.get_base_currency()
    return BaseCurrencyResponse(base_currency=base_currency)


@router.put(
    "/base-currency",
    response_model=BaseCurrencyResponse,
    summary="Set base currency",
    description="Set the organization's base currency",
)
async def set_base_currency(
    data: BaseCurrencyUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Set the organization's base currency.

    Requires authentication.

    **Request Body:**
    - **base_currency**: Currency code (3 uppercase letters, ISO 4217)

    **Returns:** Updated base currency
    """
    service = CurrencyService(db)
    service.set_base_currency(data.base_currency, current_user.id)
    return BaseCurrencyResponse(base_currency=data.base_currency)


# Exchange Rate Endpoints


@router.get(
    "/exchange-rates",
    response_model=list[ExchangeRateResponse],
    summary="List exchange rates",
    description="Get all exchange rates with optional filters",
)
async def list_exchange_rates(
    from_currency: Optional[str] = Query(None, description="Filter by source currency"),
    to_currency: Optional[str] = Query(None, description="Filter by target currency"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List exchange rates with optional filters.

    Requires authentication.

    **Query Parameters:**
    - **from_currency**: Filter by source currency (optional)
    - **to_currency**: Filter by target currency (optional)
    - **start_date**: Filter by start date (optional)
    - **end_date**: Filter by end date (optional)

    **Returns:** List of exchange rates
    """
    service = CurrencyService(db)

    if from_currency and to_currency:
        # Get historical rates for specific currency pair
        rates = service.get_historical_rates(
            from_currency, to_currency, start_date, end_date
        )
    else:
        # Get all rates (with optional date filtering)
        query = db.query(ExchangeRate)

        if from_currency:
            query = query.filter(ExchangeRate.from_currency == from_currency)
        if to_currency:
            query = query.filter(ExchangeRate.to_currency == to_currency)
        if start_date:
            query = query.filter(ExchangeRate.effective_date >= start_date)
        if end_date:
            query = query.filter(ExchangeRate.effective_date <= end_date)

        rates = query.order_by(ExchangeRate.effective_date.desc()).all()

    return [ExchangeRateResponse.model_validate(rate) for rate in rates]


@router.get(
    "/exchange-rates/{from_currency}/{to_currency}",
    response_model=ExchangeRateResponse,
    summary="Get exchange rate",
    description="Get the current exchange rate for a currency pair",
)
async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    effective_date: Optional[date] = Query(None, description="Date for exchange rate"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get exchange rate for a currency pair.

    Requires authentication.

    **Path Parameters:**
    - **from_currency**: Source currency code
    - **to_currency**: Target currency code

    **Query Parameters:**
    - **effective_date**: Date for exchange rate (defaults to today)

    **Returns:** Exchange rate details
    """
    service = CurrencyService(db)
    rate_value = service.get_exchange_rate(from_currency, to_currency, effective_date)

    # Get the actual rate record for response
    query = db.query(ExchangeRate).filter(
        ExchangeRate.from_currency == from_currency,
        ExchangeRate.to_currency == to_currency,
    )

    if effective_date:
        query = query.filter(ExchangeRate.effective_date <= effective_date)

    rate_record = query.order_by(ExchangeRate.effective_date.desc()).first()

    if rate_record:
        return ExchangeRateResponse.model_validate(rate_record)

    # If no record found but rate is 1.0 (same currency), create a virtual response
    return ExchangeRateResponse(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        from_currency=from_currency,
        to_currency=to_currency,
        rate=rate_value,
        effective_date=effective_date or date.today(),
        created_at=str(date.today()),
    )


@router.post(
    "/exchange-rates",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create exchange rate",
    description="Create or update an exchange rate",
)
async def create_exchange_rate(
    data: ExchangeRateCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create or update an exchange rate.

    If a rate already exists for the same currency pair and date, it will be updated.

    Requires authentication.

    **Request Body:**
    - **from_currency**: Source currency code (3 uppercase letters)
    - **to_currency**: Target currency code (3 uppercase letters)
    - **rate**: Exchange rate value (must be positive)
    - **effective_date**: Date from which this rate is effective

    **Returns:** Created/updated exchange rate
    """
    service = CurrencyService(db)
    rate = service.set_exchange_rate(
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        rate=data.rate,
        effective_date=data.effective_date,
    )
    return ExchangeRateResponse.model_validate(rate)


@router.put(
    "/exchange-rates/{rate_id}",
    response_model=ExchangeRateResponse,
    summary="Update exchange rate",
    description="Update an existing exchange rate",
)
async def update_exchange_rate(
    rate_id: UUID,
    data: ExchangeRateUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing exchange rate.

    Requires authentication.

    **Path Parameters:**
    - **rate_id**: Exchange rate UUID

    **Request Body:**
    - **rate**: New exchange rate value (must be positive)
    - **effective_date**: New effective date

    **Returns:** Updated exchange rate
    """
    # Get existing rate
    rate_record = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()

    if not rate_record:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Exchange rate not found")

    # Update fields
    rate_record.rate = data.rate
    rate_record.effective_date = data.effective_date

    db.commit()
    db.refresh(rate_record)

    return ExchangeRateResponse.model_validate(rate_record)


@router.delete(
    "/exchange-rates/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete exchange rate",
    description="Delete an exchange rate",
)
async def delete_exchange_rate(
    rate_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete an exchange rate.

    Requires authentication.

    **Path Parameters:**
    - **rate_id**: Exchange rate UUID

    **Returns:** 204 No Content on success
    """
    rate_record = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()

    if not rate_record:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Exchange rate not found")

    db.delete(rate_record)
    db.commit()

    return None


# Currency Conversion Endpoint


@router.post(
    "/convert",
    response_model=CurrencyConversionResponse,
    summary="Convert currency",
    description="Convert an amount from one currency to another",
)
async def convert_currency(
    data: CurrencyConversionRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Convert an amount from one currency to another.

    Requires authentication.

    **Request Body:**
    - **amount**: Amount to convert
    - **from_currency**: Source currency code
    - **to_currency**: Target currency code
    - **effective_date**: Date for exchange rate (optional, defaults to today)

    **Returns:** Conversion details including rate and converted amount
    """
    service = CurrencyService(db)

    effective_date = data.effective_date or date.today()
    rate = service.get_exchange_rate(
        data.from_currency, data.to_currency, effective_date
    )
    converted_amount = service.convert(
        data.amount, data.from_currency, data.to_currency, effective_date
    )

    return CurrencyConversionResponse(
        amount=data.amount,
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        rate=rate,
        converted_amount=converted_amount,
        effective_date=effective_date,
    )

