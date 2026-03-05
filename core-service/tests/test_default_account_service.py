"""Unit tests for DefaultAccountService"""

import uuid

import pytest

from app.core.exceptions import (
    ChartOfAccountNotFoundException,
    ValidationError,
)
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.services.default_account_service import DefaultAccountService


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def asset_account(db_session, organization_id):
    """Create a test asset account"""
    account = Account(
        organization_id=organization_id,
        account_code="1000",
        account_name="Cash",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def expense_account(db_session, organization_id):
    """Create a test expense account"""
    account = Account(
        organization_id=organization_id,
        account_code="5000",
        account_name="Purchase Expense",
        account_type=AccountType.EXPENSE,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def income_account(db_session, organization_id):
    """Create a test income account"""
    account = Account(
        organization_id=organization_id,
        account_code="4000",
        account_name="Sales Revenue",
        account_type=AccountType.INCOME,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def inactive_account(db_session, organization_id):
    """Create an inactive account"""
    account = Account(
        organization_id=organization_id,
        account_code="9000",
        account_name="Inactive Account",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.INACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def default_account_service(db_session):
    """Create DefaultAccountService instance"""
    return DefaultAccountService(db_session)



class TestSetDefaultAccount:
    """Tests for set_default_account method"""

    def test_set_default_account_success(
        self, default_account_service, asset_account, organization_id
    ):
        """Test successfully setting a default account"""
        result = default_account_service.set_default_account(
            transaction_type="cash",
            account_id=asset_account.id,
            organization_id=organization_id,
        )

        assert result.transaction_type == "cash"
        assert result.account_id == asset_account.id
        assert result.scenario is None
        assert result.organization_id == organization_id

    def test_set_default_account_with_scenario(
        self, default_account_service, asset_account, organization_id
    ):
        """Test setting a default account with a scenario"""
        result = default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
            scenario="domestic",
        )

        assert result.transaction_type == "inventory_purchase"
        assert result.account_id == asset_account.id
        assert result.scenario == "domestic"

    def test_set_default_account_updates_existing(
        self, default_account_service, asset_account, expense_account, organization_id
    ):
        """Test updating an existing default account"""
        # Set initial default
        default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
        )

        # Update to different account
        result = default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=expense_account.id,
            organization_id=organization_id,
        )

        assert result.account_id == expense_account.id

        # Verify only one default exists
        defaults = default_account_service.list_default_accounts(organization_id)
        assert len(defaults) == 1

    def test_set_default_account_validates_account_type(
        self, default_account_service, income_account, organization_id
    ):
        """Test validation of account type appropriateness"""
        # Try to set an INCOME account for inventory_purchase (should be ASSET or EXPENSE)
        with pytest.raises(ValidationError) as exc_info:
            default_account_service.set_default_account(
                transaction_type="inventory_purchase",
                account_id=income_account.id,
                organization_id=organization_id,
            )

        assert "not appropriate" in str(exc_info.value)
        assert "ASSET, EXPENSE" in str(exc_info.value)

    def test_set_default_account_rejects_inactive_account(
        self, default_account_service, inactive_account, organization_id
    ):
        """Test that inactive accounts cannot be set as defaults"""
        with pytest.raises(ValidationError) as exc_info:
            default_account_service.set_default_account(
                transaction_type="cash",
                account_id=inactive_account.id,
                organization_id=organization_id,
            )

        assert "inactive account" in str(exc_info.value).lower()

    def test_set_default_account_rejects_nonexistent_account(
        self, default_account_service, organization_id
    ):
        """Test that nonexistent accounts are rejected"""
        fake_account_id = uuid.uuid4()

        with pytest.raises(ChartOfAccountNotFoundException):
            default_account_service.set_default_account(
                transaction_type="cash",
                account_id=fake_account_id,
                organization_id=organization_id,
            )

    def test_set_default_account_requires_transaction_type(
        self, default_account_service, asset_account, organization_id
    ):
        """Test that transaction type is required"""
        with pytest.raises(ValidationError) as exc_info:
            default_account_service.set_default_account(
                transaction_type="",
                account_id=asset_account.id,
                organization_id=organization_id,
            )

        assert "required" in str(exc_info.value).lower()

    def test_set_default_account_multiple_scenarios(
        self, default_account_service, asset_account, expense_account, organization_id
    ):
        """Test setting multiple defaults for same transaction type with different scenarios"""
        # Set domestic scenario
        domestic = default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
            scenario="domestic",
        )

        # Set international scenario
        international = default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=expense_account.id,
            organization_id=organization_id,
            scenario="international",
        )

        assert domestic.scenario == "domestic"
        assert international.scenario == "international"
        assert domestic.account_id != international.account_id

        # Verify both exist
        defaults = default_account_service.list_default_accounts(
            organization_id, transaction_type="inventory_purchase"
        )
        assert len(defaults) == 2



class TestGetDefaultAccount:
    """Tests for get_default_account method"""

    def test_get_default_account_success(
        self, default_account_service, asset_account, organization_id
    ):
        """Test successfully retrieving a default account"""
        # Set up default
        default_account_service.set_default_account(
            transaction_type="cash",
            account_id=asset_account.id,
            organization_id=organization_id,
        )

        # Retrieve it
        result = default_account_service.get_default_account(
            transaction_type="cash",
            organization_id=organization_id,
        )

        assert result.account_id == asset_account.id
        assert result.transaction_type == "cash"

    def test_get_default_account_with_scenario(
        self, default_account_service, asset_account, organization_id
    ):
        """Test retrieving a default account with scenario"""
        # Set up default with scenario
        default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
            scenario="domestic",
        )

        # Retrieve it
        result = default_account_service.get_default_account(
            transaction_type="inventory_purchase",
            organization_id=organization_id,
            scenario="domestic",
        )

        assert result.account_id == asset_account.id
        assert result.scenario == "domestic"

    def test_get_default_account_not_found(
        self, default_account_service, organization_id
    ):
        """Test error when default account is not configured"""
        with pytest.raises(ValidationError) as exc_info:
            default_account_service.get_default_account(
                transaction_type="nonexistent_type",
                organization_id=organization_id,
            )

        assert "No default account configured" in str(exc_info.value)
        assert "nonexistent_type" in str(exc_info.value)

    def test_get_default_account_scenario_not_found(
        self, default_account_service, asset_account, organization_id
    ):
        """Test error when scenario is not configured"""
        # Set up default without scenario
        default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
        )

        # Try to get with different scenario
        with pytest.raises(ValidationError) as exc_info:
            default_account_service.get_default_account(
                transaction_type="inventory_purchase",
                organization_id=organization_id,
                scenario="international",
            )

        assert "No default account configured" in str(exc_info.value)
        assert "international" in str(exc_info.value)


class TestListDefaultAccounts:
    """Tests for list_default_accounts method"""

    def test_list_default_accounts_empty(
        self, default_account_service, organization_id
    ):
        """Test listing when no defaults are configured"""
        result = default_account_service.list_default_accounts(organization_id)
        assert result == []

    def test_list_default_accounts_all(
        self, default_account_service, asset_account, expense_account, organization_id
    ):
        """Test listing all default accounts"""
        # Set up multiple defaults
        default_account_service.set_default_account(
            transaction_type="cash",
            account_id=asset_account.id,
            organization_id=organization_id,
        )
        default_account_service.set_default_account(
            transaction_type="purchase_expense",
            account_id=expense_account.id,
            organization_id=organization_id,
        )

        result = default_account_service.list_default_accounts(organization_id)
        assert len(result) == 2

        transaction_types = [d.transaction_type for d in result]
        assert "cash" in transaction_types
        assert "purchase_expense" in transaction_types

    def test_list_default_accounts_filtered_by_type(
        self, default_account_service, asset_account, expense_account, organization_id
    ):
        """Test listing default accounts filtered by transaction type"""
        # Set up multiple defaults
        default_account_service.set_default_account(
            transaction_type="cash",
            account_id=asset_account.id,
            organization_id=organization_id,
        )
        default_account_service.set_default_account(
            transaction_type="purchase_expense",
            account_id=expense_account.id,
            organization_id=organization_id,
        )

        result = default_account_service.list_default_accounts(
            organization_id, transaction_type="cash"
        )
        assert len(result) == 1
        assert result[0].transaction_type == "cash"

    def test_list_default_accounts_with_scenarios(
        self, default_account_service, asset_account, expense_account, organization_id
    ):
        """Test listing includes scenarios"""
        # Set up defaults with scenarios
        default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
            scenario="domestic",
        )
        default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=expense_account.id,
            organization_id=organization_id,
            scenario="international",
        )

        result = default_account_service.list_default_accounts(
            organization_id, transaction_type="inventory_purchase"
        )
        assert len(result) == 2

        scenarios = [d.scenario for d in result]
        assert "domestic" in scenarios
        assert "international" in scenarios

    def test_list_default_accounts_sorted(
        self, default_account_service, asset_account, expense_account, organization_id
    ):
        """Test that results are sorted by transaction_type and scenario"""
        # Set up defaults in non-alphabetical order
        default_account_service.set_default_account(
            transaction_type="purchase_expense",
            account_id=expense_account.id,
            organization_id=organization_id,
        )
        default_account_service.set_default_account(
            transaction_type="cash",
            account_id=asset_account.id,
            organization_id=organization_id,
        )

        result = default_account_service.list_default_accounts(organization_id)
        assert len(result) == 2
        # Should be sorted alphabetically by transaction_type
        assert result[0].transaction_type == "cash"
        assert result[1].transaction_type == "purchase_expense"


class TestDeleteDefaultAccount:
    """Tests for delete_default_account method"""

    def test_delete_default_account_success(
        self, default_account_service, asset_account, organization_id
    ):
        """Test successfully deleting a default account"""
        # Set up default
        default_account_service.set_default_account(
            transaction_type="cash",
            account_id=asset_account.id,
            organization_id=organization_id,
        )

        # Delete it
        default_account_service.delete_default_account(
            transaction_type="cash",
            organization_id=organization_id,
        )

        # Verify it's gone
        with pytest.raises(ValidationError):
            default_account_service.get_default_account(
                transaction_type="cash",
                organization_id=organization_id,
            )

    def test_delete_default_account_with_scenario(
        self, default_account_service, asset_account, organization_id
    ):
        """Test deleting a default account with scenario"""
        # Set up default with scenario
        default_account_service.set_default_account(
            transaction_type="inventory_purchase",
            account_id=asset_account.id,
            organization_id=organization_id,
            scenario="domestic",
        )

        # Delete it
        default_account_service.delete_default_account(
            transaction_type="inventory_purchase",
            organization_id=organization_id,
            scenario="domestic",
        )

        # Verify it's gone
        with pytest.raises(ValidationError):
            default_account_service.get_default_account(
                transaction_type="inventory_purchase",
                organization_id=organization_id,
                scenario="domestic",
            )

    def test_delete_default_account_not_found(
        self, default_account_service, organization_id
    ):
        """Test error when trying to delete non-existent default"""
        with pytest.raises(ValidationError) as exc_info:
            default_account_service.delete_default_account(
                transaction_type="nonexistent_type",
                organization_id=organization_id,
            )

        assert "No default account configured" in str(exc_info.value)
