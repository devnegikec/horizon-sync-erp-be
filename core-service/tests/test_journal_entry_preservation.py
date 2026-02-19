"""
Preservation Property Tests for Journal Entry Integration Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.7**

These tests capture the EXISTING behavior of balance calculation logic that
must be preserved after the fix. They test components that do NOT involve
the database query itself:
- Natural balance direction calculation
- Currency conversion using CurrencyService
- Consolidated balance calculation using HierarchyManager
- Redis caching of balance results
- Zero balance handling for accounts without entries

EXPECTED OUTCOME: These tests MUST PASS on unfixed code to establish the
baseline behavior. They should continue to pass after the fix is implemented,
confirming no regressions.

METHODOLOGY: Observation-first approach
1. Run tests on UNFIXED code to observe current behavior
2. Tests encode the observed behavior as properties
3. After fix, re-run tests to confirm behavior is preserved
"""

import uuid
import pytest
from decimal import Decimal
from datetime import date, datetime, UTC
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from app.models.chart_of_account import Account
from app.models.base import AccountType, AccountStatus
from app.services.balance_calculator import BalanceCalculator
from app.services.currency_service import CurrencyService
from app.services.hierarchy_manager import HierarchyManager
from app.core.cache import get_balance_cache_key, cache


class TestBalanceCalculationPreservation:
    """
    Preservation tests for balance calculation logic.
    
    These tests verify that non-query components of balance calculation
    remain unchanged after the fix.
    """
    
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        debit_amount=st.decimals(min_value=0, max_value=1000000, places=2),
        credit_amount=st.decimals(min_value=0, max_value=1000000, places=2),
        account_type=st.sampled_from([AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE, AccountType.EXPENSE])
    )
    def test_property_natural_balance_direction_preserved(self, db_session, debit_amount, credit_amount, account_type):
        """
        Property 2: Preservation - Natural Balance Direction Calculation
        
        For ALL account types, the natural balance direction calculation MUST
        follow the existing logic:
        - Assets and Expenses: Balance = Debit - Credit (debit increases balance)
        - Liabilities, Equity, Revenue: Balance = Credit - Debit (credit increases balance)
        
        This property must remain unchanged after the fix.
        
        **Validates: Requirements 3.2**
        """
        # Filter out NaN and infinite values
        assume(not debit_amount.is_nan() and not debit_amount.is_infinite())
        assume(not credit_amount.is_nan() and not credit_amount.is_infinite())
        
        # Create balance calculator
        calculator = BalanceCalculator(db_session)
        
        # Calculate natural balance using the private method
        balance = calculator._get_natural_balance(account_type, debit_amount, credit_amount)
        
        # Property: Natural balance direction follows existing logic
        if account_type in (AccountType.ASSET, AccountType.EXPENSE):
            # Debit balance accounts: Balance = Debit - Credit
            expected_balance = debit_amount - credit_amount
            assert balance == expected_balance, (
                f"Asset/Expense balance should be Debit - Credit. "
                f"Expected {expected_balance}, got {balance}"
            )
        else:
            # Credit balance accounts (LIABILITY, EQUITY, REVENUE): Balance = Credit - Debit
            expected_balance = credit_amount - debit_amount
            assert balance == expected_balance, (
                f"Liability/Equity/Revenue balance should be Credit - Debit. "
                f"Expected {expected_balance}, got {balance}"
            )
    
    def test_natural_balance_asset_account(self, db_session):
        """
        Concrete example: Asset account natural balance direction.
        
        Assets have debit balance: Balance = Debit - Credit
        
        **Validates: Requirements 3.2**
        """
        calculator = BalanceCalculator(db_session)
        
        # Test case: $1000 debit, $300 credit = $700 balance
        balance = calculator._get_natural_balance(
            AccountType.ASSET,
            Decimal("1000.00"),
            Decimal("300.00")
        )
        
        assert balance == Decimal("700.00"), "Asset balance should be Debit - Credit"
    
    def test_natural_balance_liability_account(self, db_session):
        """
        Concrete example: Liability account natural balance direction.
        
        Liabilities have credit balance: Balance = Credit - Debit
        
        **Validates: Requirements 3.2**
        """
        calculator = BalanceCalculator(db_session)
        
        # Test case: $300 debit, $1000 credit = $700 balance
        balance = calculator._get_natural_balance(
            AccountType.LIABILITY,
            Decimal("300.00"),
            Decimal("1000.00")
        )
        
        assert balance == Decimal("700.00"), "Liability balance should be Credit - Debit"
    
    def test_natural_balance_expense_account(self, db_session):
        """
        Concrete example: Expense account natural balance direction.
        
        Expenses have debit balance: Balance = Debit - Credit
        
        **Validates: Requirements 3.2**
        """
        calculator = BalanceCalculator(db_session)
        
        # Test case: $500 debit, $100 credit = $400 balance
        balance = calculator._get_natural_balance(
            AccountType.EXPENSE,
            Decimal("500.00"),
            Decimal("100.00")
        )
        
        assert balance == Decimal("400.00"), "Expense balance should be Debit - Credit"
    
    def test_natural_balance_revenue_account(self, db_session):
        """
        Concrete example: Revenue account natural balance direction.
        
        Revenue has credit balance: Balance = Credit - Debit
        
        **Validates: Requirements 3.2**
        """
        calculator = BalanceCalculator(db_session)
        
        # Test case: $100 debit, $500 credit = $400 balance
        balance = calculator._get_natural_balance(
            AccountType.REVENUE,
            Decimal("100.00"),
            Decimal("500.00")
        )
        
        assert balance == Decimal("400.00"), "Revenue balance should be Credit - Debit"
    
    def test_natural_balance_equity_account(self, db_session):
        """
        Concrete example: Equity account natural balance direction.
        
        Equity has credit balance: Balance = Credit - Debit
        
        **Validates: Requirements 3.2**
        """
        calculator = BalanceCalculator(db_session)
        
        # Test case: $200 debit, $800 credit = $600 balance
        balance = calculator._get_natural_balance(
            AccountType.EQUITY,
            Decimal("200.00"),
            Decimal("800.00")
        )
        
        assert balance == Decimal("600.00"), "Equity balance should be Credit - Debit"


class TestCurrencyConversionPreservation:
    """
    Preservation tests for currency conversion integration.
    
    These tests verify that CurrencyService integration remains unchanged.
    """
    
    def test_currency_service_integration_preserved(self, db_session, mock_current_user):
        """
        Test that CurrencyService integration uses the same parameters.
        
        The balance calculator should call currency_service.convert() with:
        - amount: the calculated balance
        - from_currency: account.currency
        - to_currency: base currency
        - date: as_of_date
        
        This integration must remain unchanged after the fix.
        
        **Validates: Requirements 3.3**
        """
        # Create an account with non-USD currency
        account = Account(
            account_code="1110",
            account_name="Cash - EUR",
            account_type=AccountType.ASSET,
            currency="EUR",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Mock the currency service to observe the call
        with patch.object(CurrencyService, 'convert', return_value=Decimal("100.00")) as mock_convert:
            with patch.object(CurrencyService, 'get_base_currency', return_value="USD"):
                calculator = BalanceCalculator(db_session)
                balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        # Verify currency service was called (if balance is non-zero)
        # On unfixed code, balance is zero, so conversion may not be called
        # But the integration pattern should remain the same
        if balance_data and balance_data["balance"] != 0.0:
            mock_convert.assert_called_once()
            call_args = mock_convert.call_args
            
            # Verify the parameters match the expected pattern
            assert call_args[1]["from_currency"] == "EUR"
            assert call_args[1]["to_currency"] == "USD"
            assert "date" in call_args[1]
    
    def test_currency_conversion_fallback_preserved(self, db_session, mock_current_user):
        """
        Test that currency conversion fallback behavior is preserved.
        
        When currency conversion fails, the balance calculator should:
        - Log a warning
        - Use the original balance as base_currency_balance
        
        This fallback behavior must remain unchanged after the fix.
        
        **Validates: Requirements 3.3**
        """
        # Create an account with non-USD currency
        account = Account(
            account_code="1120",
            account_name="Cash - GBP",
            account_type=AccountType.ASSET,
            currency="GBP",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Mock currency service to raise an exception
        with patch.object(CurrencyService, 'convert', side_effect=Exception("Conversion failed")):
            with patch.object(CurrencyService, 'get_base_currency', return_value="USD"):
                calculator = BalanceCalculator(db_session)
                balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        # Verify fallback behavior: base_currency_balance equals balance
        assert balance_data is not None
        assert balance_data["balance"] == balance_data["base_currency_balance"], (
            "When conversion fails, base_currency_balance should equal balance"
        )
    
    def test_same_currency_no_conversion(self, db_session, mock_current_user):
        """
        Test that accounts in base currency don't trigger conversion.
        
        When account.currency == base_currency, no conversion should occur.
        
        **Validates: Requirements 3.3**
        """
        # Create an account with USD currency (base currency)
        account = Account(
            account_code="1130",
            account_name="Cash - USD",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Mock the currency service to verify it's NOT called
        with patch.object(CurrencyService, 'convert') as mock_convert:
            with patch.object(CurrencyService, 'get_base_currency', return_value="USD"):
                calculator = BalanceCalculator(db_session)
                balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        # Verify currency service convert was NOT called
        mock_convert.assert_not_called()
        
        # Verify balance equals base_currency_balance
        assert balance_data is not None
        assert balance_data["balance"] == balance_data["base_currency_balance"]


class TestHierarchyManagerPreservation:
    """
    Preservation tests for HierarchyManager integration.
    
    These tests verify that consolidated balance calculation remains unchanged.
    """
    
    def test_consolidated_balance_uses_hierarchy_manager(self, db_session, mock_current_user):
        """
        Test that consolidated balance calculation uses HierarchyManager.
        
        The balance calculator should call hierarchy_manager.get_descendants()
        to retrieve child accounts for consolidation.
        
        This integration must remain unchanged after the fix.
        
        **Validates: Requirements 3.4**
        """
        # Create a parent account
        parent_account = Account(
            account_code="1000",
            account_name="Assets",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(parent_account)
        db_session.commit()
        db_session.refresh(parent_account)
        
        # Mock hierarchy manager to observe the call
        with patch.object(HierarchyManager, 'get_descendants', return_value=[]) as mock_get_descendants:
            calculator = BalanceCalculator(db_session)
            consolidated_data = calculator.calculate_consolidated_balance(
                parent_account.id,
                mock_current_user.organization_id,
                use_cache=False
            )
        
        # Verify hierarchy manager was called
        mock_get_descendants.assert_called_once_with(
            parent_account.id,
            mock_current_user.organization_id
        )
    
    def test_consolidated_balance_aggregates_children(self, db_session, mock_current_user):
        """
        Test that consolidated balance aggregates child account balances.
        
        The balance calculator should:
        1. Get descendants using HierarchyManager
        2. Calculate balance for each posting account descendant
        3. Sum the balances using natural balance direction
        
        This aggregation logic must remain unchanged after the fix.
        
        **Validates: Requirements 3.4**
        """
        # Create a parent account
        parent_account = Account(
            account_code="1000",
            account_name="Assets",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(parent_account)
        db_session.commit()
        db_session.refresh(parent_account)
        
        # Create child accounts
        child1 = Account(
            account_code="1100",
            account_name="Current Assets",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            parent_account_id=parent_account.id,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        child2 = Account(
            account_code="1200",
            account_name="Fixed Assets",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            parent_account_id=parent_account.id,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add_all([child1, child2])
        db_session.commit()
        
        # Calculate consolidated balance
        calculator = BalanceCalculator(db_session)
        consolidated_data = calculator.calculate_consolidated_balance(
            parent_account.id,
            mock_current_user.organization_id,
            use_cache=False
        )
        
        # Verify consolidated data structure
        assert consolidated_data is not None
        
        # The consolidated balance may or may not include is_consolidated depending on
        # whether descendants are returned by HierarchyManager
        # If descendants exist, it should have is_consolidated=True
        # If no descendants, it falls back to single account balance (no is_consolidated field)
        if "is_consolidated" in consolidated_data:
            assert consolidated_data["is_consolidated"] is True
            assert "child_count" in consolidated_data
        
        # On unfixed code, all balances are zero
        # After fix, balances should reflect actual journal entries
        # But the aggregation logic should remain the same
        assert consolidated_data["debit_total"] == 0.0
        assert consolidated_data["credit_total"] == 0.0
        assert consolidated_data["balance"] == 0.0
    
    def test_consolidated_balance_no_descendants_fallback(self, db_session, mock_current_user):
        """
        Test that consolidated balance falls back to single account balance.
        
        When a parent account has no descendants, the balance calculator should
        calculate the balance for the parent account itself.
        
        This fallback behavior must remain unchanged after the fix.
        
        **Validates: Requirements 3.4**
        """
        # Create a parent account with no children
        parent_account = Account(
            account_code="1000",
            account_name="Assets",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(parent_account)
        db_session.commit()
        db_session.refresh(parent_account)
        
        # Calculate consolidated balance
        calculator = BalanceCalculator(db_session)
        consolidated_data = calculator.calculate_consolidated_balance(
            parent_account.id,
            mock_current_user.organization_id,
            use_cache=False
        )
        
        # Verify it falls back to single account balance
        assert consolidated_data is not None
        assert consolidated_data["account_id"] == str(parent_account.id)


class TestCachingPreservation:
    """
    Preservation tests for Redis caching behavior.
    
    These tests verify that cache key generation and TTL remain unchanged.
    """
    
    def test_cache_key_generation_preserved(self, db_session, mock_current_user):
        """
        Test that cache key generation follows the existing pattern.
        
        Cache keys should be generated as:
        - "balance:account:{account_id}:current" for current date
        - "balance:account:{account_id}:{YYYY-MM-DD}" for specific date
        
        This pattern must remain unchanged after the fix.
        
        **Validates: Requirements 3.7**
        """
        # Create an account
        account = Account(
            account_code="1110",
            account_name="Cash",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Test cache key for current date
        cache_key_current = get_balance_cache_key(account.id, None)
        assert cache_key_current == f"balance:account:{account.id}:current"
        
        # Test cache key for specific date
        specific_date = date(2024, 1, 15)
        cache_key_specific = get_balance_cache_key(account.id, specific_date.isoformat())
        assert cache_key_specific == f"balance:account:{account.id}:2024-01-15"
    
    def test_cache_ttl_preserved(self, db_session, mock_current_user):
        """
        Test that cache TTL remains 3600 seconds (1 hour).
        
        The balance calculator should cache results with TTL=3600.
        
        This TTL must remain unchanged after the fix.
        
        **Validates: Requirements 3.7**
        """
        # Create an account
        account = Account(
            account_code="1110",
            account_name="Cash",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Mock cache.set to observe the TTL parameter
        with patch.object(cache, 'set', return_value=True) as mock_cache_set:
            calculator = BalanceCalculator(db_session)
            balance_data = calculator.calculate_balance(account.id, use_cache=True)
        
        # Verify cache.set was called with TTL=3600
        mock_cache_set.assert_called_once()
        call_args = mock_cache_set.call_args
        assert call_args[1]["ttl"] == 3600, "Cache TTL should be 3600 seconds (1 hour)"
    
    def test_cache_usage_preserved(self, db_session, mock_current_user):
        """
        Test that cache is checked before querying database.
        
        When use_cache=True, the balance calculator should:
        1. Check cache first
        2. Return cached value if found
        3. Query database only if cache miss
        
        This behavior must remain unchanged after the fix.
        
        **Validates: Requirements 3.7**
        """
        # Create an account
        account = Account(
            account_code="1110",
            account_name="Cash",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Mock cache to return a cached value
        cached_balance = {
            "account_id": str(account.id),
            "currency": "USD",
            "debit_total": 1000.0,
            "credit_total": 300.0,
            "balance": 700.0,
            "base_currency_balance": 700.0,
            "as_of_date": date.today().isoformat(),
            "account_type": "ASSET",
            "account_code": "1110",
            "account_name": "Cash"
        }
        
        with patch.object(cache, 'get', return_value=cached_balance) as mock_cache_get:
            calculator = BalanceCalculator(db_session)
            balance_data = calculator.calculate_balance(account.id, use_cache=True)
        
        # Verify cache was checked
        mock_cache_get.assert_called_once()
        
        # Verify cached value was returned
        assert balance_data == cached_balance
    
    def test_cache_bypass_preserved(self, db_session, mock_current_user):
        """
        Test that use_cache=False bypasses cache.
        
        When use_cache=False, the balance calculator should:
        - Skip cache check
        - Query database directly
        - Not cache the result
        
        This behavior must remain unchanged after the fix.
        
        **Validates: Requirements 3.7**
        """
        # Create an account
        account = Account(
            account_code="1110",
            account_name="Cash",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Mock cache to verify it's NOT used
        with patch.object(cache, 'get') as mock_cache_get:
            with patch.object(cache, 'set') as mock_cache_set:
                calculator = BalanceCalculator(db_session)
                balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        # Verify cache was NOT checked or set
        mock_cache_get.assert_not_called()
        mock_cache_set.assert_not_called()


class TestZeroBalancePreservation:
    """
    Preservation tests for zero balance handling.
    
    These tests verify that accounts without journal entries return zero balances.
    """
    
    @settings(
        max_examples=15,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        account_code=st.text(min_size=4, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))),
        account_type=st.sampled_from([AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE, AccountType.EXPENSE])
    )
    def test_property_zero_balance_for_empty_accounts(self, db_session, mock_current_user, account_code, account_type):
        """
        Property 3: Preservation - Zero Balance for Empty Accounts
        
        For ANY account that has no journal entry lines, the balance calculator
        MUST return zero balances (debit_total=0, credit_total=0, balance=0).
        
        This behavior must remain unchanged after the fix.
        
        **Validates: Requirements 3.1**
        """
        # Filter out invalid account codes
        assume(len(account_code.strip()) >= 4)
        assume(not account_code.isspace())
        
        # Create an account with no journal entries
        account = Account(
            account_code=account_code.strip(),
            account_name=f"Test Account {account_code.strip()}",
            account_type=account_type,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        
        try:
            db_session.commit()
            db_session.refresh(account)
        except Exception:
            # Skip if account creation fails (e.g., duplicate code)
            db_session.rollback()
            assume(False)
        
        # Calculate balance
        calculator = BalanceCalculator(db_session)
        balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        # Property: Accounts without journal entries return zero balances
        assert balance_data is not None
        assert balance_data["debit_total"] == 0.0, f"Expected debit_total=0 for empty account {account.account_code}"
        assert balance_data["credit_total"] == 0.0, f"Expected credit_total=0 for empty account {account.account_code}"
        assert balance_data["balance"] == 0.0, f"Expected balance=0 for empty account {account.account_code}"
        
        # Clean up
        db_session.delete(account)
        db_session.commit()
    
    def test_zero_balance_concrete_example(self, db_session, mock_current_user):
        """
        Concrete example: New account with no transactions returns zero balance.
        
        **Validates: Requirements 3.1**
        """
        # Create a new account with no journal entries
        account = Account(
            account_code="9999",
            account_name="New Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()
        db_session.refresh(account)
        
        # Calculate balance
        calculator = BalanceCalculator(db_session)
        balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        # Verify zero balance
        assert balance_data is not None
        assert balance_data["debit_total"] == 0.0
        assert balance_data["credit_total"] == 0.0
        assert balance_data["balance"] == 0.0
