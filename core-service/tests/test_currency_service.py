"""Unit tests for CurrencyService"""

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import (
    ExchangeRateNotFoundException,
    ValidationError,
)
from app.models.exchange_rate import ExchangeRate
from app.models.system_config import SystemConfig
from app.services.currency_service import CurrencyService


class TestCurrencyService:
    """Test CurrencyService functionality"""

    def test_get_base_currency_default(self, db_session):
        """Test getting base currency returns default when not configured"""
        service = CurrencyService(db_session)
        base_currency = service.get_base_currency()
        assert base_currency == "USD"

    def test_set_and_get_base_currency(self, db_session):
        """Test setting and getting base currency"""
        service = CurrencyService(db_session)

        # Set base currency
        service.set_base_currency("EUR", "test_user")

        # Get base currency
        base_currency = service.get_base_currency()
        assert base_currency == "EUR"

    def test_set_base_currency_updates_existing(self, db_session):
        """Test that setting base currency updates existing config"""
        service = CurrencyService(db_session)

        # Set initial
        service.set_base_currency("EUR", "user1")
        assert service.get_base_currency() == "EUR"

        # Update
        service.set_base_currency("GBP", "user2")
        assert service.get_base_currency() == "GBP"

        # Verify only one config record exists
        configs = (
            db_session.query(SystemConfig)
            .filter(SystemConfig.key == "base_currency")
            .all()
        )
        assert len(configs) == 1

    def test_set_base_currency_invalid_format(self, db_session):
        """Test that invalid currency codes are rejected"""
        service = CurrencyService(db_session)

        # Too short
        with pytest.raises(ValidationError, match="Invalid currency code"):
            service.set_base_currency("US", "test_user")

        # Too long
        with pytest.raises(ValidationError, match="Invalid currency code"):
            service.set_base_currency("USDD", "test_user")

        # Lowercase
        with pytest.raises(ValidationError, match="Invalid currency code"):
            service.set_base_currency("usd", "test_user")

        # Empty
        with pytest.raises(ValidationError, match="Invalid currency code"):
            service.set_base_currency("", "test_user")

    def test_get_exchange_rate_same_currency(self, db_session):
        """Test that same currency returns rate of 1"""
        service = CurrencyService(db_session)
        rate = service.get_exchange_rate("USD", "USD")
        assert rate == Decimal("1.0")

    def test_set_and_get_exchange_rate(self, db_session):
        """Test setting and getting exchange rate"""
        service = CurrencyService(db_session)
        effective_date = date(2024, 1, 1)

        # Set rate
        exchange_rate = service.set_exchange_rate(
            "USD", "EUR", Decimal("0.85"), effective_date
        )
        assert exchange_rate.from_currency == "USD"
        assert exchange_rate.to_currency == "EUR"
        assert exchange_rate.rate == Decimal("0.85")
        assert exchange_rate.effective_date == effective_date

        # Get rate
        rate = service.get_exchange_rate("USD", "EUR", effective_date)
        assert rate == Decimal("0.85")

    def test_set_exchange_rate_updates_existing(self, db_session):
        """Test that setting rate for same date updates existing record"""
        service = CurrencyService(db_session)
        effective_date = date(2024, 1, 1)

        # Set initial rate
        service.set_exchange_rate("USD", "EUR", Decimal("0.85"), effective_date)

        # Update rate for same date
        service.set_exchange_rate("USD", "EUR", Decimal("0.87"), effective_date)

        # Verify only one record exists
        rates = (
            db_session.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency == "USD",
                ExchangeRate.to_currency == "EUR",
                ExchangeRate.effective_date == effective_date,
            )
            .all()
        )
        assert len(rates) == 1
        assert rates[0].rate == Decimal("0.87")

    def test_set_exchange_rate_invalid_inputs(self, db_session):
        """Test that invalid inputs are rejected"""
        service = CurrencyService(db_session)
        effective_date = date(2024, 1, 1)

        # Negative rate
        with pytest.raises(ValidationError, match="must be positive"):
            service.set_exchange_rate("USD", "EUR", Decimal("-0.85"), effective_date)

        # Zero rate
        with pytest.raises(ValidationError, match="must be positive"):
            service.set_exchange_rate("USD", "EUR", Decimal("0"), effective_date)

        # Same currency
        with pytest.raises(
            ValidationError, match="Cannot set exchange rate for same currency"
        ):
            service.set_exchange_rate("USD", "USD", Decimal("1.0"), effective_date)

        # Invalid currency codes
        with pytest.raises(ValidationError, match="Invalid currency code"):
            service.set_exchange_rate("US", "EUR", Decimal("0.85"), effective_date)

    def test_get_exchange_rate_uses_most_recent(self, db_session):
        """Test that get_exchange_rate uses most recent rate on or before date"""
        service = CurrencyService(db_session)

        # Set rates for different dates
        service.set_exchange_rate("USD", "EUR", Decimal("0.85"), date(2024, 1, 1))
        service.set_exchange_rate("USD", "EUR", Decimal("0.87"), date(2024, 1, 15))
        service.set_exchange_rate("USD", "EUR", Decimal("0.90"), date(2024, 2, 1))

        # Query for date between rates
        rate = service.get_exchange_rate("USD", "EUR", date(2024, 1, 20))
        assert rate == Decimal("0.87")  # Should use Jan 15 rate

        # Query for date before all rates
        with pytest.raises(ExchangeRateNotFoundException):
            service.get_exchange_rate("USD", "EUR", date(2023, 12, 31))

        # Query for date after all rates
        rate = service.get_exchange_rate("USD", "EUR", date(2024, 3, 1))
        assert rate == Decimal("0.90")  # Should use Feb 1 rate

    def test_get_exchange_rate_defaults_to_today(self, db_session):
        """Test that get_exchange_rate defaults to today's date"""
        service = CurrencyService(db_session)
        today = date.today()

        # Set rate for today
        service.set_exchange_rate("USD", "EUR", Decimal("0.85"), today)

        # Get rate without specifying date
        rate = service.get_exchange_rate("USD", "EUR")
        assert rate == Decimal("0.85")

    def test_get_exchange_rate_not_found(self, db_session):
        """Test that missing exchange rate raises exception"""
        service = CurrencyService(db_session)

        with pytest.raises(
            ExchangeRateNotFoundException, match="No exchange rate found"
        ):
            service.get_exchange_rate("USD", "EUR", date(2024, 1, 1))

    def test_convert_currency(self, db_session):
        """Test currency conversion"""
        service = CurrencyService(db_session)
        effective_date = date(2024, 1, 1)

        # Set exchange rate
        service.set_exchange_rate("USD", "EUR", Decimal("0.85"), effective_date)

        # Convert amount
        converted = service.convert(Decimal("100"), "USD", "EUR", effective_date)
        assert converted == Decimal("85.0000")

    def test_convert_same_currency(self, db_session):
        """Test converting same currency returns same amount"""
        service = CurrencyService(db_session)

        converted = service.convert(Decimal("100"), "USD", "USD")
        assert converted == Decimal("100.0000")

    def test_convert_rounds_to_4_decimals(self, db_session):
        """Test that conversion rounds to 4 decimal places"""
        service = CurrencyService(db_session)
        effective_date = date(2024, 1, 1)

        # Set rate that will produce many decimals
        service.set_exchange_rate("USD", "EUR", Decimal("0.857142857"), effective_date)

        # Convert
        converted = service.convert(Decimal("100"), "USD", "EUR", effective_date)
        # Should be rounded to 4 decimals
        assert str(converted) == "85.7143"

    def test_get_historical_rates(self, db_session):
        """Test querying historical exchange rates"""
        service = CurrencyService(db_session)

        # Create multiple rates
        service.set_exchange_rate("USD", "EUR", Decimal("0.85"), date(2024, 1, 1))
        service.set_exchange_rate("USD", "EUR", Decimal("0.87"), date(2024, 1, 15))
        service.set_exchange_rate("USD", "EUR", Decimal("0.90"), date(2024, 2, 1))

        # Get all historical rates
        rates = service.get_historical_rates("USD", "EUR")
        assert len(rates) == 3
        # Should be ordered by date descending
        assert rates[0].effective_date == date(2024, 2, 1)
        assert rates[1].effective_date == date(2024, 1, 15)
        assert rates[2].effective_date == date(2024, 1, 1)

    def test_get_historical_rates_with_date_range(self, db_session):
        """Test querying historical rates with date range"""
        service = CurrencyService(db_session)

        # Create multiple rates
        service.set_exchange_rate("USD", "EUR", Decimal("0.85"), date(2024, 1, 1))
        service.set_exchange_rate("USD", "EUR", Decimal("0.87"), date(2024, 1, 15))
        service.set_exchange_rate("USD", "EUR", Decimal("0.90"), date(2024, 2, 1))

        # Get rates for January only
        rates = service.get_historical_rates(
            "USD", "EUR", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert len(rates) == 2
        assert all(rate.effective_date.month == 1 for rate in rates)

    def test_get_historical_rates_empty(self, db_session):
        """Test that querying non-existent rates returns empty list"""
        service = CurrencyService(db_session)

        rates = service.get_historical_rates("USD", "EUR")
        assert rates == []

    def test_validate_currency_code(self, db_session):
        """Test currency code validation"""
        service = CurrencyService(db_session)

        # Valid codes should not raise
        service._validate_currency_code("USD")
        service._validate_currency_code("EUR")
        service._validate_currency_code("GBP")

        # Invalid codes should raise
        with pytest.raises(ValidationError):
            service._validate_currency_code("US")  # Too short

        with pytest.raises(ValidationError):
            service._validate_currency_code("USDD")  # Too long

        with pytest.raises(ValidationError):
            service._validate_currency_code("usd")  # Lowercase

        with pytest.raises(ValidationError):
            service._validate_currency_code("")  # Empty
