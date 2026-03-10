"""Tests for balance calculator service"""

from decimal import Decimal

from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.services.balance_calculator import BalanceCalculator


class TestBalanceCalculator:
    """Test balance calculator functionality"""

    def test_natural_balance_asset_account(self, db_session, sample_organization):
        """Test natural balance calculation for asset account"""
        # Create an asset account
        account = Account(
            organization_id=sample_organization.id,
            account_code="1000",
            account_name="Cash",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test-user",
            updated_by="test-user",
        )
        db_session.add(account)
        db_session.commit()

        # Test balance calculator
        calculator = BalanceCalculator(db_session)

        # Test natural balance direction (Asset: Debit - Credit)
        balance = calculator._get_natural_balance(
            AccountType.ASSET, Decimal("1000.00"), Decimal("500.00")
        )

        assert balance == Decimal("500.00")

    def test_natural_balance_liability_account(self, db_session, sample_organization):
        """Test natural balance calculation for liability account"""
        calculator = BalanceCalculator(db_session)

        # Test natural balance direction (Liability: Credit - Debit)
        balance = calculator._get_natural_balance(
            AccountType.LIABILITY, Decimal("500.00"), Decimal("1000.00")
        )

        assert balance == Decimal("500.00")

    def test_calculate_balance_no_transactions(self, db_session, sample_organization):
        """Test balance calculation for account with no transactions"""
        # Create an account
        account = Account(
            organization_id=sample_organization.id,
            account_code="1000",
            account_name="Cash",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test-user",
            updated_by="test-user",
        )
        db_session.add(account)
        db_session.commit()

        # Calculate balance
        calculator = BalanceCalculator(db_session)
        balance_data = calculator.calculate_balance(account.id, use_cache=False)

        assert balance_data is not None
        assert balance_data["account_id"] == str(account.id)
        assert balance_data["balance"] == 0.0
        assert balance_data["debit_total"] == 0.0
        assert balance_data["credit_total"] == 0.0
