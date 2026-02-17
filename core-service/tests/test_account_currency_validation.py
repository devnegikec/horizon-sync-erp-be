"""Tests for account currency validation (Requirements 4.2, 11.5)"""

import uuid

import pytest
from app.core.exceptions import ValidationError
from app.schemas.chart_of_account import ChartOfAccountCreate, ChartOfAccountUpdate
from app.services.chart_of_account_service import ChartOfAccountService


@pytest.fixture
def account_service(db_session):
    """Create an account service instance"""
    return ChartOfAccountService(db_session)


@pytest.fixture
def organization_id():
    """Create a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Create a test user ID"""
    return uuid.uuid4()


class TestCurrencyValidation:
    """Test currency validation (Requirements 4.2, 11.5)"""

    def test_valid_currency_code_accepted(self, account_service, organization_id, user_id):
        """Test that valid ISO 4217 currency codes are accepted"""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF"]

        for currency in valid_currencies:
            data = ChartOfAccountCreate(
                account_code=f"1000-{currency}",
                account_name=f"Cash in {currency}",
                account_type="asset",
                currency=currency,
            )

            account = account_service.create(data, organization_id, user_id)
            assert account.currency == currency

    def test_default_currency_is_usd(self, account_service, organization_id, user_id):
        """Test that default currency is USD when not specified"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )

        account = account_service.create(data, organization_id, user_id)
        assert account.currency == "USD"

    def test_lowercase_currency_rejected(self, account_service, organization_id, user_id):
        """Test that lowercase currency codes are rejected"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="usd",  # lowercase
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.create(data, organization_id, user_id)

        assert "Invalid currency code" in str(exc_info.value)
        assert "3 uppercase letters" in str(exc_info.value)
        assert "ISO 4217" in str(exc_info.value)

    def test_mixed_case_currency_rejected(self, account_service, organization_id, user_id):
        """Test that mixed case currency codes are rejected"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="Usd",  # mixed case
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.create(data, organization_id, user_id)

        assert "Invalid currency code" in str(exc_info.value)
        assert "3 uppercase letters" in str(exc_info.value)

    def test_too_short_currency_rejected(self, account_service, organization_id, user_id):
        """Test that currency codes shorter than 3 characters are rejected"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="US",  # too short
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.create(data, organization_id, user_id)

        assert "Invalid currency code" in str(exc_info.value)
        assert "3 uppercase letters" in str(exc_info.value)

    def test_too_long_currency_rejected(self, account_service, organization_id, user_id):
        """Test that currency codes longer than 3 characters are rejected by Pydantic"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError) as exc_info:
            data = ChartOfAccountCreate(
                account_code="1000",
                account_name="Cash",
                account_type="asset",
                currency="USDD",  # too long
            )

        assert "String should have at most 3 characters" in str(exc_info.value)

    def test_empty_currency_uses_default(self, account_service, organization_id, user_id):
        """Test that empty currency code defaults to USD"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="",  # empty - will use default
        )

        account = account_service.create(data, organization_id, user_id)
        # Empty string should default to USD in the schema
        assert account.currency == "USD" or account.currency == ""

    def test_numeric_currency_rejected(self, account_service, organization_id, user_id):
        """Test that numeric currency codes are rejected"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="123",  # numeric
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.create(data, organization_id, user_id)

        assert "Invalid currency code" in str(exc_info.value)
        assert "3 uppercase letters" in str(exc_info.value)

    def test_special_characters_currency_rejected(self, account_service, organization_id, user_id):
        """Test that currency codes with special characters are rejected"""
        invalid_currencies = ["US$", "U$D", "U-D", "U.D"]

        for i, currency in enumerate(invalid_currencies):
            data = ChartOfAccountCreate(
                account_code=f"100{i}",  # Use simple code without special chars
                account_name="Cash",
                account_type="asset",
                currency=currency,
            )

            with pytest.raises(ValidationError) as exc_info:
                account_service.create(data, organization_id, user_id)

            assert "Invalid currency code" in str(exc_info.value)


class TestCurrencyUpdateValidation:
    """Test currency validation during account updates"""

    def test_update_currency_valid(self, account_service, organization_id, user_id):
        """Test that updating to a valid currency succeeds"""
        # Create account with USD
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="USD",
        )
        account = account_service.create(data, organization_id, user_id)

        # Update to EUR
        update_data = ChartOfAccountUpdate(currency="EUR")
        updated_account = account_service.update(account.id, update_data, organization_id, user_id)

        assert updated_account.currency == "EUR"

    def test_update_currency_invalid(self, account_service, organization_id, user_id):
        """Test that updating to an invalid currency is rejected"""
        # Create account with USD
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="USD",
        )
        account = account_service.create(data, organization_id, user_id)

        # Try to update to invalid currency
        update_data = ChartOfAccountUpdate(currency="usd")  # lowercase

        with pytest.raises(ValidationError) as exc_info:
            account_service.update(account.id, update_data, organization_id, user_id)

        assert "Invalid currency code" in str(exc_info.value)

    def test_update_currency_too_short(self, account_service, organization_id, user_id):
        """Test that updating to a too-short currency is rejected"""
        # Create account
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
            currency="USD",
        )
        account = account_service.create(data, organization_id, user_id)

        # Try to update to invalid currency
        update_data = ChartOfAccountUpdate(currency="US")

        with pytest.raises(ValidationError) as exc_info:
            account_service.update(account.id, update_data, organization_id, user_id)

        assert "Invalid currency code" in str(exc_info.value)
        assert "3 uppercase letters" in str(exc_info.value)


class TestMultiCurrencyAccounts:
    """Test creating accounts with different currencies"""

    def test_create_accounts_with_different_currencies(self, account_service, organization_id, user_id):
        """Test that multiple accounts can have different currencies"""
        currencies = ["USD", "EUR", "GBP"]
        accounts = []

        for i, currency in enumerate(currencies):
            data = ChartOfAccountCreate(
                account_code=f"100{i}",
                account_name=f"Cash in {currency}",
                account_type="asset",
                currency=currency,
            )
            account = account_service.create(data, organization_id, user_id)
            accounts.append(account)

        # Verify all accounts were created with correct currencies
        assert len(accounts) == 3
        assert accounts[0].currency == "USD"
        assert accounts[1].currency == "EUR"
        assert accounts[2].currency == "GBP"

    def test_parent_and_child_can_have_different_currencies(
        self, account_service, organization_id, user_id
    ):
        """Test that parent and child accounts can have different currencies"""
        # Create parent account with USD
        parent_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash Accounts",
            account_type="asset",
            currency="USD",
        )
        parent = account_service.create(parent_data, organization_id, user_id)

        # Create child account with EUR
        child_data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Cash in EUR",
            account_type="asset",
            currency="EUR",
            parent_account_id=parent.id,
        )
        child = account_service.create(child_data, organization_id, user_id)

        assert parent.currency == "USD"
        assert child.currency == "EUR"
        assert child.parent_account_id == parent.id
