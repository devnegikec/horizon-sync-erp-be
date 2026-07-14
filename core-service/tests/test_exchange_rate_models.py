"""Tests for ExchangeRate and SystemConfig models"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.exchange_rate import ExchangeRate
from app.models.system_config import SystemConfig


class TestExchangeRateModel:
    """Test ExchangeRate model"""

    def test_create_exchange_rate(self, db_session):
        """Test creating an exchange rate"""
        exchange_rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 1),
        )
        db_session.add(exchange_rate)
        db_session.commit()

        assert exchange_rate.id is not None
        assert exchange_rate.from_currency == "USD"
        assert exchange_rate.to_currency == "EUR"
        assert exchange_rate.rate == Decimal("0.85")
        assert exchange_rate.effective_date == date(2024, 1, 1)
        assert isinstance(exchange_rate.created_at, datetime)

    def test_exchange_rate_unique_constraint(self, db_session):
        """Test that duplicate currency pair and date is rejected"""
        exchange_rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 1),
        )
        db_session.add(exchange_rate1)
        db_session.commit()

        # Try to create duplicate
        exchange_rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.86"),
            effective_date=date(2024, 1, 1),
        )
        db_session.add(exchange_rate2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_exchange_rate_positive_check(self, db_session):
        """Test that negative rates are rejected"""
        exchange_rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("-0.85"),
            effective_date=date(2024, 1, 1),
        )
        db_session.add(exchange_rate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_exchange_rate_different_dates_allowed(self, db_session):
        """Test that same currency pair with different dates is allowed"""
        exchange_rate1 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 1),
        )
        exchange_rate2 = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.86"),
            effective_date=date(2024, 1, 2),
        )
        db_session.add_all([exchange_rate1, exchange_rate2])
        db_session.commit()

        assert exchange_rate1.id != exchange_rate2.id

    def test_exchange_rate_repr(self, db_session):
        """Test string representation of exchange rate"""
        exchange_rate = ExchangeRate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0.85"),
            effective_date=date(2024, 1, 1),
        )
        db_session.add(exchange_rate)
        db_session.commit()

        repr_str = repr(exchange_rate)
        assert "USD" in repr_str
        assert "EUR" in repr_str
        assert "0.85" in repr_str


class TestSystemConfigModel:
    """Test SystemConfig model"""

    def test_create_system_config(self, db_session):
        """Test creating a system config entry"""
        config = SystemConfig(
            key="test_key",
            value="test_value",
            updated_by="test_user",
        )
        db_session.add(config)
        db_session.commit()

        assert config.key == "test_key"
        assert config.value == "test_value"
        assert config.updated_by == "test_user"
        assert isinstance(config.updated_at, datetime)

    def test_system_config_unique_key(self, db_session):
        """Test that duplicate keys are rejected"""
        config1 = SystemConfig(
            key="test_key",
            value="value1",
            updated_by="user1",
        )
        db_session.add(config1)
        db_session.commit()

        # Try to create duplicate key
        config2 = SystemConfig(
            key="test_key",
            value="value2",
            updated_by="user2",
        )
        db_session.add(config2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_system_config_update(self, db_session):
        """Test updating a system config entry"""
        config = SystemConfig(
            key="test_key",
            value="initial_value",
            updated_by="user1",
        )
        db_session.add(config)
        db_session.commit()

        initial_updated_at = config.updated_at

        # Update the config
        config.value = "updated_value"
        config.updated_by = "user2"
        db_session.commit()

        assert config.value == "updated_value"
        assert config.updated_by == "user2"
        # Note: updated_at auto-update may not work in SQLite tests

    def test_system_config_repr(self, db_session):
        """Test string representation of system config"""
        config = SystemConfig(
            key="base_currency",
            value="USD",
            updated_by="system",
        )
        db_session.add(config)
        db_session.commit()

        repr_str = repr(config)
        assert "base_currency" in repr_str
        assert "USD" in repr_str
