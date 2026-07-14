"""Unit tests for Currency Master service

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
"""

import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    CurrencyNotFoundException,
    DuplicateCurrencyCodeException,
)
from app.schemas.currency_master import CurrencyMasterCreate, CurrencyMasterUpdate
from app.services.currency_master_service import CurrencyMasterService


@pytest.fixture
def currency_service(db_session):
    """Create a Currency Master service instance with a test DB session."""
    return CurrencyMasterService(db_session)


@pytest.fixture
def sample_currency(currency_service, sample_organization_id, sample_user_id):
    """Create and return a sample currency for reuse in tests."""
    data = CurrencyMasterCreate(
        code="USD", name="US Dollar", symbol="$", is_base_currency=False
    )
    return currency_service.create_currency(
        data, sample_organization_id, sample_user_id
    )


# ── Create ──────────────────────────────────────────────────────────────


def test_create_currency_with_valid_data(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.1"""
    data = CurrencyMasterCreate(
        code="EUR", name="Euro", symbol="€", is_base_currency=False
    )
    currency = currency_service.create_currency(
        data, sample_organization_id, sample_user_id
    )

    assert currency.id is not None
    assert currency.code == "EUR"
    assert currency.name == "Euro"
    assert currency.symbol == "€"
    assert currency.is_base_currency is False
    assert currency.organization_id == sample_organization_id
    assert currency.created_by == sample_user_id
    assert currency.updated_by == sample_user_id
    assert currency.deleted_at is None


def test_create_currency_without_symbol(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.1 — symbol is optional"""
    data = CurrencyMasterCreate(code="GBP", name="British Pound")
    currency = currency_service.create_currency(
        data, sample_organization_id, sample_user_id
    )

    assert currency.code == "GBP"
    assert currency.symbol is None


def test_create_currency_duplicate_code_raises_409(
    currency_service, sample_currency, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.7"""
    duplicate = CurrencyMasterCreate(code="USD", name="United States Dollar")
    with pytest.raises(DuplicateCurrencyCodeException):
        currency_service.create_currency(
            duplicate, sample_organization_id, sample_user_id
        )


# ── Code format validation (Pydantic) ──────────────────────────────────


def test_code_format_rejects_lowercase():
    """Validates: Requirements 3.8"""
    with pytest.raises(PydanticValidationError):
        CurrencyMasterCreate(code="usd", name="US Dollar")


def test_code_format_rejects_wrong_length_short():
    """Validates: Requirements 3.8"""
    with pytest.raises(PydanticValidationError):
        CurrencyMasterCreate(code="US", name="US Dollar")


def test_code_format_rejects_wrong_length_long():
    """Validates: Requirements 3.8"""
    with pytest.raises(PydanticValidationError):
        CurrencyMasterCreate(code="USDD", name="US Dollar")


def test_code_format_rejects_digits():
    """Validates: Requirements 3.8"""
    with pytest.raises(PydanticValidationError):
        CurrencyMasterCreate(code="U1D", name="US Dollar")


# ── Base currency toggle ────────────────────────────────────────────────


def test_create_with_base_currency_clears_others(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.6"""
    # Create first currency as base
    usd = currency_service.create_currency(
        CurrencyMasterCreate(code="USD", name="US Dollar", is_base_currency=True),
        sample_organization_id,
        sample_user_id,
    )
    assert usd.is_base_currency is True

    # Create second currency as base — should clear USD
    eur = currency_service.create_currency(
        CurrencyMasterCreate(code="EUR", name="Euro", is_base_currency=True),
        sample_organization_id,
        sample_user_id,
    )
    assert eur.is_base_currency is True

    # Refresh USD and verify it's no longer base
    refreshed_usd = currency_service.get_currency(usd.id, sample_organization_id)
    assert refreshed_usd.is_base_currency is False


# ── Get ─────────────────────────────────────────────────────────────────


def test_get_currency_by_id(currency_service, sample_currency, sample_organization_id):
    """Validates: Requirements 3.3"""
    fetched = currency_service.get_currency(sample_currency.id, sample_organization_id)

    assert fetched.id == sample_currency.id
    assert fetched.code == "USD"
    assert fetched.name == "US Dollar"
    assert fetched.symbol == "$"


def test_get_currency_not_found_raises_404(currency_service, sample_organization_id):
    """Validates: Requirements 3.9"""
    with pytest.raises(CurrencyNotFoundException):
        currency_service.get_currency(uuid.uuid4(), sample_organization_id)


def test_get_currency_different_org_raises_404(currency_service, sample_currency):
    """Validates: Requirements 3.9 (organization isolation)"""
    other_org_id = uuid.uuid4()
    with pytest.raises(CurrencyNotFoundException):
        currency_service.get_currency(sample_currency.id, other_org_id)


# ── List ────────────────────────────────────────────────────────────────


def test_list_currencies_with_pagination(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.2"""
    codes = ["USD", "EUR", "GBP"]
    for code in codes:
        currency_service.create_currency(
            CurrencyMasterCreate(code=code, name=f"{code} Currency"),
            sample_organization_id,
            sample_user_id,
        )

    currencies, pagination = currency_service.list_currencies(
        sample_organization_id, page=1, page_size=2
    )

    assert len(currencies) == 2
    assert pagination["total_items"] == 3
    assert pagination["total_pages"] == 2
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False

    # Page 2
    currencies_p2, pag_p2 = currency_service.list_currencies(
        sample_organization_id, page=2, page_size=2
    )
    assert len(currencies_p2) == 1
    assert pag_p2["has_next"] is False
    assert pag_p2["has_prev"] is True


def test_list_currencies_with_search(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.2"""
    currency_service.create_currency(
        CurrencyMasterCreate(code="USD", name="US Dollar"),
        sample_organization_id,
        sample_user_id,
    )
    currency_service.create_currency(
        CurrencyMasterCreate(code="EUR", name="Euro"),
        sample_organization_id,
        sample_user_id,
    )

    currencies, pagination = currency_service.list_currencies(
        sample_organization_id, search="dollar"
    )

    assert len(currencies) == 1
    assert currencies[0].code == "USD"
    assert pagination["total_items"] == 1


def test_list_currencies_org_isolation(currency_service, sample_currency):
    """Validates: Requirements 3.9"""
    other_org_id = uuid.uuid4()
    currencies, pagination = currency_service.list_currencies(other_org_id)

    assert len(currencies) == 0
    assert pagination["total_items"] == 0


# ── Update ──────────────────────────────────────────────────────────────


def test_update_currency(
    currency_service, sample_currency, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.4"""
    update_data = CurrencyMasterUpdate(name="United States Dollar", symbol="US$")
    updated = currency_service.update_currency(
        sample_currency.id, update_data, sample_organization_id, sample_user_id
    )

    assert updated.name == "United States Dollar"
    assert updated.symbol == "US$"
    # Code should remain unchanged
    assert updated.code == "USD"


def test_update_currency_base_toggle(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.6"""
    usd = currency_service.create_currency(
        CurrencyMasterCreate(code="USD", name="US Dollar", is_base_currency=True),
        sample_organization_id,
        sample_user_id,
    )
    eur = currency_service.create_currency(
        CurrencyMasterCreate(code="EUR", name="Euro", is_base_currency=False),
        sample_organization_id,
        sample_user_id,
    )

    # Update EUR to be base currency
    currency_service.update_currency(
        eur.id,
        CurrencyMasterUpdate(is_base_currency=True),
        sample_organization_id,
        sample_user_id,
    )

    refreshed_usd = currency_service.get_currency(usd.id, sample_organization_id)
    refreshed_eur = currency_service.get_currency(eur.id, sample_organization_id)

    assert refreshed_eur.is_base_currency is True
    assert refreshed_usd.is_base_currency is False


def test_update_currency_not_found_raises_404(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.9"""
    with pytest.raises(CurrencyNotFoundException):
        currency_service.update_currency(
            uuid.uuid4(),
            CurrencyMasterUpdate(name="Nope"),
            sample_organization_id,
            sample_user_id,
        )


# ── Soft-delete ─────────────────────────────────────────────────────────


def test_soft_delete_currency(
    currency_service, sample_currency, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.5"""
    currency_service.delete_currency(
        sample_currency.id, sample_organization_id, sample_user_id
    )

    # Should not be retrievable
    with pytest.raises(CurrencyNotFoundException):
        currency_service.get_currency(sample_currency.id, sample_organization_id)

    # Should not appear in list
    currencies, pagination = currency_service.list_currencies(sample_organization_id)
    assert len(currencies) == 0
    assert pagination["total_items"] == 0


def test_soft_delete_not_found_raises_404(
    currency_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 3.9"""
    with pytest.raises(CurrencyNotFoundException):
        currency_service.delete_currency(
            uuid.uuid4(), sample_organization_id, sample_user_id
        )


def test_service_duplicate_check_ignores_soft_deleted(
    currency_service, sample_currency, sample_organization_id, sample_user_id
):
    """Verify the service-level duplicate check correctly ignores soft-deleted records.

    After soft-deleting a currency, the repository's get_by_code should return None,
    so the service should NOT raise DuplicateCurrencyCodeException for the same code.

    Validates: Requirements 3.7
    """
    currency_service.delete_currency(
        sample_currency.id, sample_organization_id, sample_user_id
    )

    # After soft-delete, the repository should NOT find the old record
    assert (
        currency_service.currency_repo.get_by_code("USD", sample_organization_id)
        is None
    )
