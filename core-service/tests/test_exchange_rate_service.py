"""Unit tests for Exchange Rate service

Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    ExchangeRateNotFoundException,
    ValidationException,
)
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateUpdate
from app.services.exchange_rate_service import ExchangeRateService


@pytest.fixture
def exchange_rate_service(db_session):
    """Create an Exchange Rate service instance with a test DB session."""
    return ExchangeRateService(db_session)


@pytest.fixture
def sample_exchange_rate(exchange_rate_service, sample_organization_id):
    """Create and return a sample exchange rate for reuse in tests."""
    data = ExchangeRateCreate(
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.85"),
        effective_date=date(2025, 1, 15),
    )
    return exchange_rate_service.create_exchange_rate(data, sample_organization_id)


# ── Create ──────────────────────────────────────────────────────────────


def test_create_exchange_rate_with_valid_data(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.2"""
    data = ExchangeRateCreate(
        from_currency="USD",
        to_currency="GBP",
        rate=Decimal("0.79"),
        effective_date=date(2025, 6, 1),
    )
    rate = exchange_rate_service.create_exchange_rate(data, sample_organization_id)

    assert rate.id is not None
    assert rate.from_currency == "USD"
    assert rate.to_currency == "GBP"
    assert rate.rate == Decimal("0.79")
    assert rate.effective_date == date(2025, 6, 1)
    assert rate.organization_id == sample_organization_id
    assert rate.captured_at is not None


def test_create_exchange_rate_default_effective_date(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.2 — effective_date defaults to today"""
    data = ExchangeRateCreate(
        from_currency="USD",
        to_currency="JPY",
        rate=Decimal("149.50"),
    )
    rate = exchange_rate_service.create_exchange_rate(data, sample_organization_id)

    assert rate.effective_date == date.today()


# ── Upsert idempotence ──────────────────────────────────────────────────


def test_upsert_updates_existing_rate(
    exchange_rate_service, sample_exchange_rate, sample_organization_id, db_session
):
    """Validates: Requirements 4.7 — same (org, from, to, date) updates existing"""
    from app.models.exchange_rate import ExchangeRate

    original_id = sample_exchange_rate.id

    # Create again with same key but different rate
    data = ExchangeRateCreate(
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.90"),
        effective_date=date(2025, 1, 15),
    )
    updated = exchange_rate_service.create_exchange_rate(data, sample_organization_id)

    # Should be the same record, not a new one
    assert updated.id == original_id
    assert updated.rate == Decimal("0.90")

    # Total count should remain 1
    count = (
        db_session.query(ExchangeRate)
        .filter(ExchangeRate.organization_id == sample_organization_id)
        .count()
    )
    assert count == 1


# ── Same-currency rejection ─────────────────────────────────────────────


def test_same_currency_raises_validation_exception(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.9"""
    data = ExchangeRateCreate(
        from_currency="USD",
        to_currency="USD",
        rate=Decimal("1.00"),
        effective_date=date(2025, 1, 1),
    )
    with pytest.raises(ValidationException):
        exchange_rate_service.create_exchange_rate(data, sample_organization_id)


# ── Positive rate validation (Pydantic) ─────────────────────────────────


def test_rate_rejects_zero():
    """Validates: Requirements 4.8"""
    with pytest.raises(PydanticValidationError):
        ExchangeRateCreate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("0"),
        )


def test_rate_rejects_negative():
    """Validates: Requirements 4.8"""
    with pytest.raises(PydanticValidationError):
        ExchangeRateCreate(
            from_currency="USD",
            to_currency="EUR",
            rate=Decimal("-1.5"),
        )


# ── Get ─────────────────────────────────────────────────────────────────


def test_get_exchange_rate_by_id(
    exchange_rate_service, sample_exchange_rate, sample_organization_id
):
    """Validates: Requirements 4.4"""
    fetched = exchange_rate_service.get_exchange_rate(
        sample_exchange_rate.id, sample_organization_id
    )

    assert fetched.id == sample_exchange_rate.id
    assert fetched.from_currency == "USD"
    assert fetched.to_currency == "EUR"
    assert fetched.rate == Decimal("0.85")


def test_get_exchange_rate_not_found(exchange_rate_service, sample_organization_id):
    """Validates: Requirements 4.4"""
    with pytest.raises(ExchangeRateNotFoundException):
        exchange_rate_service.get_exchange_rate(uuid.uuid4(), sample_organization_id)


# ── List with filters ───────────────────────────────────────────────────


def test_list_exchange_rates_with_pagination(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.3"""
    pairs = [("USD", "EUR"), ("USD", "GBP"), ("EUR", "JPY")]
    for from_c, to_c in pairs:
        exchange_rate_service.create_exchange_rate(
            ExchangeRateCreate(
                from_currency=from_c,
                to_currency=to_c,
                rate=Decimal("1.23"),
                effective_date=date(2025, 1, 1),
            ),
            sample_organization_id,
        )

    rates, pagination = exchange_rate_service.list_exchange_rates(
        sample_organization_id, page=1, page_size=2
    )

    assert len(rates) == 2
    assert pagination["total_items"] == 3
    assert pagination["total_pages"] == 2
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False


def test_list_exchange_rates_filter_by_from_currency(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.3"""
    exchange_rate_service.create_exchange_rate(
        ExchangeRateCreate(
            from_currency="USD", to_currency="EUR", rate=Decimal("0.85")
        ),
        sample_organization_id,
    )
    exchange_rate_service.create_exchange_rate(
        ExchangeRateCreate(
            from_currency="GBP", to_currency="EUR", rate=Decimal("1.17")
        ),
        sample_organization_id,
    )

    rates, pagination = exchange_rate_service.list_exchange_rates(
        sample_organization_id, from_currency="USD"
    )

    assert len(rates) == 1
    assert rates[0].from_currency == "USD"
    assert pagination["total_items"] == 1


def test_list_exchange_rates_filter_by_to_currency(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.3"""
    exchange_rate_service.create_exchange_rate(
        ExchangeRateCreate(
            from_currency="USD", to_currency="EUR", rate=Decimal("0.85")
        ),
        sample_organization_id,
    )
    exchange_rate_service.create_exchange_rate(
        ExchangeRateCreate(
            from_currency="USD", to_currency="JPY", rate=Decimal("149.50")
        ),
        sample_organization_id,
    )

    rates, pagination = exchange_rate_service.list_exchange_rates(
        sample_organization_id, to_currency="JPY"
    )

    assert len(rates) == 1
    assert rates[0].to_currency == "JPY"


def test_list_exchange_rates_filter_by_date_range(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.3"""
    dates = [date(2025, 1, 1), date(2025, 3, 15), date(2025, 6, 30)]
    for d in dates:
        exchange_rate_service.create_exchange_rate(
            ExchangeRateCreate(
                from_currency="USD",
                to_currency="EUR",
                rate=Decimal("0.85"),
                effective_date=d,
            ),
            sample_organization_id,
        )

    rates, pagination = exchange_rate_service.list_exchange_rates(
        sample_organization_id,
        start_date=date(2025, 2, 1),
        end_date=date(2025, 5, 1),
    )

    assert len(rates) == 1
    assert rates[0].effective_date == date(2025, 3, 15)
    assert pagination["total_items"] == 1


# ── Update ──────────────────────────────────────────────────────────────


def test_update_exchange_rate(
    exchange_rate_service, sample_exchange_rate, sample_organization_id
):
    """Validates: Requirements 4.5"""
    update_data = ExchangeRateUpdate(
        rate=Decimal("0.92"), effective_date=date(2025, 2, 1)
    )
    updated = exchange_rate_service.update_exchange_rate(
        sample_exchange_rate.id, update_data, sample_organization_id
    )

    assert updated.rate == Decimal("0.92")
    assert updated.effective_date == date(2025, 2, 1)
    # Currency pair should remain unchanged
    assert updated.from_currency == "USD"
    assert updated.to_currency == "EUR"


def test_update_exchange_rate_not_found(exchange_rate_service, sample_organization_id):
    """Validates: Requirements 4.5"""
    with pytest.raises(ExchangeRateNotFoundException):
        exchange_rate_service.update_exchange_rate(
            uuid.uuid4(),
            ExchangeRateUpdate(rate=Decimal("1.00")),
            sample_organization_id,
        )


# ── Hard-delete ─────────────────────────────────────────────────────────


def test_hard_delete_exchange_rate(
    exchange_rate_service, sample_exchange_rate, sample_organization_id
):
    """Validates: Requirements 4.6"""
    exchange_rate_service.delete_exchange_rate(
        sample_exchange_rate.id, sample_organization_id
    )

    # Should not be retrievable
    with pytest.raises(ExchangeRateNotFoundException):
        exchange_rate_service.get_exchange_rate(
            sample_exchange_rate.id, sample_organization_id
        )

    # Should not appear in list
    rates, pagination = exchange_rate_service.list_exchange_rates(
        sample_organization_id
    )
    assert len(rates) == 0
    assert pagination["total_items"] == 0


def test_hard_delete_not_found_raises_404(
    exchange_rate_service, sample_organization_id
):
    """Validates: Requirements 4.6"""
    with pytest.raises(ExchangeRateNotFoundException):
        exchange_rate_service.delete_exchange_rate(uuid.uuid4(), sample_organization_id)


# ── Organization isolation ──────────────────────────────────────────────


def test_org_scoped_get_isolation(exchange_rate_service, sample_exchange_rate):
    """Validates: Requirements 4.4 (org isolation)"""
    other_org_id = uuid.uuid4()
    with pytest.raises(ExchangeRateNotFoundException):
        exchange_rate_service.get_exchange_rate(sample_exchange_rate.id, other_org_id)


def test_org_scoped_list_isolation(exchange_rate_service, sample_exchange_rate):
    """Validates: Requirements 4.3 (org isolation)"""
    other_org_id = uuid.uuid4()
    rates, pagination = exchange_rate_service.list_exchange_rates(other_org_id)

    assert len(rates) == 0
    assert pagination["total_items"] == 0
