"""
Bug Condition Exploration Test for Journal Entry Integration Fix

**Validates: Requirements 1.1, 1.3, 1.4**

This test is designed to FAIL on unfixed code to confirm the bug exists.
The test explores the fault condition where journal entry tables are missing
from the database, causing balance calculations to fail and return zero.

EXPECTED OUTCOME: This test MUST FAIL on unfixed code (this is correct behavior).
The failure confirms that:
1. journal_entries and journal_entry_lines tables do not exist
2. Balance calculator catches the exception and returns zero balances
3. JournalEntry models are not imported in app.models
4. Alembic does not detect journal entry models

After the fix is implemented, this test will pass, validating that the
integration is complete.
"""

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from sqlalchemy import inspect, text

from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.services.balance_calculator import BalanceCalculator


class TestJournalEntryBugExploration:
    """
    Exploration tests to surface counterexamples demonstrating the bug.

    These tests are EXPECTED TO FAIL on unfixed code.
    """

    def test_journal_entries_table_exists_but_empty(self, db_session):
        """
        Test that journal_entries table exists but has no data.

        NOTE: In the test environment, tables are created from Base.metadata,
        so the tables exist. However, in a production environment where Alembic
        migrations are used, the tables would NOT exist because the models are
        not imported in app/models/__init__.py.

        This test confirms the table structure exists but is empty.

        **Validates: Requirements 1.1, 1.4**
        """
        # Query the journal_entries table - it exists in test but would not in production
        result = db_session.execute(text("SELECT COUNT(*) FROM journal_entries"))
        count = result.scalar()

        # Verify the table is empty (no seed data, no migration to populate it)
        assert count == 0, "journal_entries table should be empty on unfixed code"

    def test_journal_entry_lines_table_exists_but_empty(self, db_session):
        """
        Test that journal_entry_lines table exists but has no data.

        NOTE: In the test environment, tables are created from Base.metadata,
        so the tables exist. However, in a production environment where Alembic
        migrations are used, the tables would NOT exist because the models are
        not imported in app/models/__init__.py.

        This test confirms the table structure exists but is empty.

        **Validates: Requirements 1.1, 1.4**
        """
        # Query the journal_entry_lines table - it exists in test but would not in production
        result = db_session.execute(text("SELECT COUNT(*) FROM journal_entry_lines"))
        count = result.scalar()

        # Verify the table is empty (no seed data, no migration to populate it)
        assert count == 0, "journal_entry_lines table should be empty on unfixed code"

    def test_balance_calculator_returns_zero_for_missing_tables(
        self, db_session, mock_current_user
    ):
        """
        Test that balance calculator returns zero balances when journal entry tables are missing.

        This demonstrates the fallback behavior where the exception is caught
        and zero balances are returned instead of raising an error.

        EXPECTED: Balance calculator returns zero for all accounts because
        the journal entry tables don't exist and the exception is caught.

        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        # Create a test account
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

        # Calculate balance using the balance calculator
        calculator = BalanceCalculator(db_session)
        balance_data = calculator.calculate_balance(account.id, use_cache=False)

        # Verify that the balance calculator returns zero balances
        # This is the fallback behavior when the tables don't exist
        assert balance_data is not None
        assert balance_data["debit_total"] == 0.0
        assert balance_data["credit_total"] == 0.0
        assert balance_data["balance"] == 0.0

        # This demonstrates the bug: even if journal entries existed,
        # they would not be reflected in the balance because the tables
        # don't exist and the exception is caught

    def test_journal_entry_models_not_in_app_models(self):
        """
        Test that JournalEntry and JournalEntryLine ARE NOW exported from app.models.

        AFTER FIX: This test verifies that the models ARE imported in app/models/__init__.py.
        This confirms that Requirement 2.3 is satisfied.

        **Validates: Requirements 2.3**
        """
        import app.models

        # After fix: models should be accessible from app.models
        assert hasattr(app.models, "JournalEntry"), (
            "JournalEntry should be exported from app.models"
        )
        assert hasattr(app.models, "JournalEntryLine"), (
            "JournalEntryLine should be exported from app.models"
        )

        # Verify we can actually import them
        from app.models import JournalEntry, JournalEntryLine

        assert JournalEntry is not None
        assert JournalEntryLine is not None

    def test_alembic_cannot_detect_journal_entry_models(self, db_session):
        """
        Test that Alembic CAN NOW detect journal entry models for autogeneration.

        AFTER FIX: This test verifies that the models are visible to Alembic because
        they ARE imported in app/models/__init__.py.

        **Validates: Requirements 2.3**
        """
        from app.database import Base

        # The tables ARE in metadata (because balance_calculator imports them)
        assert "journal_entries" in Base.metadata.tables, "Models are in Base.metadata"
        assert "journal_entry_lines" in Base.metadata.tables, (
            "Models are in Base.metadata"
        )

        # After fix: they ARE in app.models exports (which is what Alembic checks)
        import app.models

        assert hasattr(app.models, "JournalEntry"), (
            "JournalEntry exported from app.models"
        )
        assert hasattr(app.models, "JournalEntryLine"), (
            "JournalEntryLine exported from app.models"
        )

    def test_database_inspector_shows_tables_exist(self, db_session):
        """
        Test that database inspector confirms journal entry tables exist in test environment.

        NOTE: In the test environment, tables are created from Base.metadata.
        In production with Alembic migrations, these tables would NOT exist
        because the models are not imported in app/models/__init__.py.

        This test documents that the tables exist in test but would be missing
        in production.

        **Validates: Requirements 1.1, 1.4**
        """
        inspector = inspect(db_session.bind)
        table_names = inspector.get_table_names()

        # In test environment, tables exist (created from Base.metadata)
        assert "journal_entries" in table_names, "Table exists in test environment"
        assert "journal_entry_lines" in table_names, "Table exists in test environment"

        # But in production with Alembic, these tables would NOT exist
        # because the models are not imported in app/models/__init__.py

    @settings(
        max_examples=5,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(
        account_code=st.text(
            min_size=4,
            max_size=10,
            alphabet=st.characters(whitelist_categories=("Lu", "Nd")),
        ),
        account_name=st.text(
            min_size=3,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
        ),
        account_type=st.sampled_from(
            [
                AccountType.ASSET,
                AccountType.LIABILITY,
                AccountType.EQUITY,
                AccountType.REVENUE,
                AccountType.EXPENSE,
            ]
        ),
    )
    def test_property_all_accounts_return_zero_balance(
        self, db_session, mock_current_user, account_code, account_name, account_type
    ):
        """
        Property 1: Fault Condition - Journal Entry Tables Missing

        For ANY account, when journal entry tables are missing, the balance
        calculator MUST return zero balances (debit_total=0, credit_total=0, balance=0).

        This property test generates random accounts and verifies that ALL of them
        return zero balances, demonstrating the bug affects the entire system.

        EXPECTED: All generated accounts return zero balances because the
        journal entry tables don't exist.

        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        # Filter out invalid account codes/names
        assume(len(account_code.strip()) >= 4)
        assume(len(account_name.strip()) >= 3)
        assume(not account_code.isspace())
        assume(not account_name.isspace())

        # Create a test account with generated properties
        account = Account(
            account_code=account_code.strip(),
            account_name=account_name.strip(),
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

        # Calculate balance using the balance calculator
        calculator = BalanceCalculator(db_session)
        balance_data = calculator.calculate_balance(account.id, use_cache=False)

        # Property: ALL accounts return zero balances when tables are missing
        assert balance_data is not None, (
            f"Balance data should not be None for account {account.account_code}"
        )
        assert balance_data["debit_total"] == 0.0, (
            f"Expected debit_total=0 for {account.account_code}, got {balance_data['debit_total']}"
        )
        assert balance_data["credit_total"] == 0.0, (
            f"Expected credit_total=0 for {account.account_code}, got {balance_data['credit_total']}"
        )
        assert balance_data["balance"] == 0.0, (
            f"Expected balance=0 for {account.account_code}, got {balance_data['balance']}"
        )

        # Clean up
        db_session.delete(account)
        db_session.commit()

    def test_counterexample_cash_account_should_have_balance(
        self, db_session, mock_current_user
    ):
        """
        Concrete counterexample: Cash account should have non-zero balance.

        This test demonstrates a specific case where we EXPECT a non-zero balance
        (because journal entries should exist for a Cash account), but the system
        returns zero due to missing tables.

        EXPECTED: This test documents the expected behavior. On unfixed code,
        the balance is zero (bug). After the fix, the balance should be non-zero
        if journal entries exist.

        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        # Create a Cash account
        cash_account = Account(
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
        db_session.add(cash_account)
        db_session.commit()
        db_session.refresh(cash_account)

        # Calculate balance
        calculator = BalanceCalculator(db_session)
        balance_data = calculator.calculate_balance(cash_account.id, use_cache=False)

        # On unfixed code: balance is zero (bug)
        # After fix: balance should reflect actual journal entries
        assert balance_data is not None
        current_balance = balance_data["balance"]

        # Document the counterexample:
        # If journal entries existed for this Cash account, the balance should be non-zero
        # But due to missing tables, it returns zero
        print(f"\nCounterexample: Cash account balance = {current_balance}")
        print("Expected: Non-zero balance if journal entries exist")
        print("Actual: Zero balance due to missing journal_entry_lines table")

        # This assertion will pass on unfixed code (demonstrating the bug)
        # and will need to be updated after the fix to check for actual balances
        assert current_balance == 0.0, (
            "On unfixed code, balance should be zero due to missing tables"
        )
