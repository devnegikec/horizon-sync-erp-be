"""Currency service for multi-currency support and exchange rate management"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CurrencyNotFoundException,
    ExchangeRateNotFoundException,
    ValidationError,
)
from app.models.exchange_rate import ExchangeRate
from app.models.system_config import SystemConfig


class CurrencyService:
    """Service for currency operations and exchange rate management"""

    BASE_CURRENCY_KEY = "base_currency"
    DEFAULT_BASE_CURRENCY = "USD"

    def __init__(self, db: Session):
        """
        Initialize currency service.

        Args:
            db: Database session
        """
        self.db = db

    def get_base_currency(self) -> str:
        """
        Get the base currency for the organization.

        Returns:
            Base currency code (e.g., "USD")
        """
        config = self.db.query(SystemConfig).filter(
            SystemConfig.key == self.BASE_CURRENCY_KEY
        ).first()

        if config:
            return config.value

        # Return default if not configured
        return self.DEFAULT_BASE_CURRENCY

    def set_base_currency(self, currency: str, updated_by: str) -> None:
        """
        Set the base currency for the organization.

        Args:
            currency: Currency code to set as base (e.g., "USD")
            updated_by: User making the change

        Raises:
            ValidationError: If currency code is invalid
        """
        # Validate currency code format (ISO 4217: 3 uppercase letters)
        if not currency or len(currency) != 3 or not currency.isupper():
            raise ValidationError(
                f"Invalid currency code '{currency}'. Must be 3 uppercase letters (ISO 4217 format)"
            )

        # Check if config exists
        config = self.db.query(SystemConfig).filter(
            SystemConfig.key == self.BASE_CURRENCY_KEY
        ).first()

        if config:
            # Update existing
            config.value = currency
            config.updated_by = updated_by
            config.updated_at = datetime.now(UTC)
        else:
            # Create new
            config = SystemConfig(
                key=self.BASE_CURRENCY_KEY,
                value=currency,
                updated_by=updated_by,
            )
            self.db.add(config)

        self.db.commit()

    def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: Optional[date] = None,
    ) -> Decimal:
        """
        Get exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            effective_date: Date for which to get the rate (defaults to today)

        Returns:
            Exchange rate as Decimal

        Raises:
            ExchangeRateNotFoundException: If no rate found for the currency pair and date
            ValidationError: If currency codes are invalid
        """
        # Validate currency codes
        self._validate_currency_code(from_currency)
        self._validate_currency_code(to_currency)

        # Same currency has rate of 1
        if from_currency == to_currency:
            return Decimal("1.0")

        # Use today if no date specified
        if effective_date is None:
            effective_date = date.today()

        # Query for the most recent rate on or before the effective date
        rate_record = (
            self.db.query(ExchangeRate)
            .filter(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.effective_date <= effective_date,
                )
            )
            .order_by(desc(ExchangeRate.effective_date))
            .first()
        )

        if not rate_record:
            raise ExchangeRateNotFoundException(
                f"No exchange rate found for {from_currency} to {to_currency} "
                f"on or before {effective_date}"
            )

        return rate_record.rate

    def set_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        effective_date: date,
    ) -> ExchangeRate:
        """
        Set exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate: Exchange rate value
            effective_date: Date from which this rate is effective

        Returns:
            Created ExchangeRate record

        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate currency codes
        self._validate_currency_code(from_currency)
        self._validate_currency_code(to_currency)

        # Validate rate is positive
        if rate <= 0:
            raise ValidationError(f"Exchange rate must be positive, got {rate}")

        # Prevent setting rate for same currency
        if from_currency == to_currency:
            raise ValidationError(
                f"Cannot set exchange rate for same currency ({from_currency})"
            )

        # Check if rate already exists for this date
        existing_rate = (
            self.db.query(ExchangeRate)
            .filter(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.effective_date == effective_date,
                )
            )
            .first()
        )

        if existing_rate:
            # Update existing rate
            existing_rate.rate = rate
            self.db.commit()
            self.db.refresh(existing_rate)
            return existing_rate

        # Create new rate
        exchange_rate = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            effective_date=effective_date,
        )
        self.db.add(exchange_rate)
        self.db.commit()
        self.db.refresh(exchange_rate)

        return exchange_rate

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        effective_date: Optional[date] = None,
    ) -> Decimal:
        """
        Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            effective_date: Date for exchange rate (defaults to today)

        Returns:
            Converted amount as Decimal

        Raises:
            ExchangeRateNotFoundException: If no rate found
            ValidationError: If inputs are invalid
        """
        # Get exchange rate
        rate = self.get_exchange_rate(from_currency, to_currency, effective_date)

        # Convert amount
        converted = amount * rate

        # Round to 4 decimal places for currency precision
        return converted.quantize(Decimal("0.0001"))

    def get_historical_rates(
        self,
        from_currency: str,
        to_currency: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[ExchangeRate]:
        """
        Query historical exchange rates for a currency pair.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            List of ExchangeRate records ordered by effective_date descending

        Raises:
            ValidationError: If currency codes are invalid
        """
        # Validate currency codes
        self._validate_currency_code(from_currency)
        self._validate_currency_code(to_currency)

        # Build query
        query = self.db.query(ExchangeRate).filter(
            and_(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
            )
        )

        # Apply date filters if provided
        if start_date:
            query = query.filter(ExchangeRate.effective_date >= start_date)
        if end_date:
            query = query.filter(ExchangeRate.effective_date <= end_date)

        # Order by date descending (most recent first)
        query = query.order_by(desc(ExchangeRate.effective_date))

        return query.all()

    def _validate_currency_code(self, currency: str) -> None:
        """
        Validate currency code format.

        Args:
            currency: Currency code to validate

        Raises:
            ValidationError: If currency code is invalid
        """
        if not currency or len(currency) != 3 or not currency.isupper():
            raise ValidationError(
                f"Invalid currency code '{currency}'. Must be 3 uppercase letters (ISO 4217 format)"
            )
