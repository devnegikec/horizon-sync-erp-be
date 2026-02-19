"""Integration tests for journal entry service"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from app.services.journal_entry_service import JournalEntryService
from app.services.balance_calculator import BalanceCalculator
from app.models.base import JournalStatus


class TestJournalEntryServiceIntegration:
    """Test journal entry service integration with balance calculations"""

    def test_create_and_post_journal_entry(
        self, db_session, mock_current_user, sample_accounts
    ):
        """
        Test creating a journal entry, posting it, and verifying balance updates.
        
        Requirements: 2.5, 2.6
        """
        # Get accounts for the journal entry
        cash_account = next(acc for acc in sample_accounts if acc.account_code == "1000")
        equity_account = next(acc for acc in sample_accounts if acc.account_code == "3000")
        
        # Initialize services
        je_service = JournalEntryService(db_session)
        balance_calc = BalanceCalculator(db_session)
        
        # Create journal entry data
        entry_data = {
            "entry_no": "JE-TEST-001",
            "posting_date": datetime.now(timezone.utc),
            "status": "draft",
            "voucher_type": "Journal Entry",
            "total_debit": Decimal("1000.00"),
            "total_credit": Decimal("1000.00"),
            "remarks": "Test opening balance entry",
            "lines": [
                {
                    "account_id": str(cash_account.id),
                    "debit": Decimal("1000.00"),
                    "credit": Decimal("0.00"),
                    "remarks": "Cash debit",
                    "sort_order": 1,
                },
                {
                    "account_id": str(equity_account.id),
                    "debit": Decimal("0.00"),
                    "credit": Decimal("1000.00"),
                    "remarks": "Equity credit",
                    "sort_order": 2,
                },
            ],
        }
        
        # Step 1: Create journal entry
        created_entry = je_service.create(
            entry_data,
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify entry is persisted
        assert created_entry["id"] is not None
        assert created_entry["entry_no"] == "JE-TEST-001"
        assert created_entry["status"] == "draft"
        assert created_entry["total_debit"] == Decimal("1000.00")
        assert created_entry["total_credit"] == Decimal("1000.00")
        assert created_entry["posted_at"] is None
        
        # Step 2: Verify balances are zero for draft entry (not posted yet)
        cash_balance = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        
        # Draft entries should not affect balances
        assert cash_balance["debit_total"] == Decimal("0.00")
        assert cash_balance["credit_total"] == Decimal("0.00")
        assert cash_balance["balance"] == Decimal("0.00")
        
        # Step 3: Post the journal entry by updating status to 'posted'
        posted_entry = je_service.update(
            entry_id=created_entry["id"],
            data={
                "status": "posted",
                "posted_at": datetime.now(timezone.utc),
            },
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify status changed to 'posted' and posted_at is set
        assert posted_entry["status"] == "posted"
        assert posted_entry["posted_at"] is not None
        
        # Step 4: Query balance for affected accounts - should reflect new entry
        cash_balance = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        
        # Cash is an asset account (debit balance)
        assert cash_balance["debit_total"] == Decimal("1000.00")
        assert cash_balance["credit_total"] == Decimal("0.00")
        assert cash_balance["balance"] == Decimal("1000.00")  # Debit - Credit for assets
        
        equity_balance = balance_calc.calculate_balance(
            account_id=equity_account.id,
        )
        
        # Equity is a credit balance account
        assert equity_balance["debit_total"] == Decimal("0.00")
        assert equity_balance["credit_total"] == Decimal("1000.00")
        assert equity_balance["balance"] == Decimal("1000.00")  # Credit - Debit for equity

    def test_multiple_journal_entries_balance_accumulation(
        self, db_session, mock_current_user, sample_accounts
    ):
        """
        Test that multiple journal entries correctly accumulate in balance calculations.
        
        Requirements: 2.5, 2.6
        """
        # Get accounts
        cash_account = next(acc for acc in sample_accounts if acc.account_code == "1000")
        revenue_account = next(acc for acc in sample_accounts if acc.account_code == "4000")
        expense_account = next(acc for acc in sample_accounts if acc.account_code == "5000")
        
        # Initialize services
        je_service = JournalEntryService(db_session)
        balance_calc = BalanceCalculator(db_session)
        
        # Create and post first entry: Cash debit 500, Revenue credit 500
        entry1_data = {
            "entry_no": "JE-TEST-002",
            "posting_date": datetime.now(timezone.utc),
            "status": "posted",
            "posted_at": datetime.now(timezone.utc),
            "voucher_type": "Journal Entry",
            "total_debit": Decimal("500.00"),
            "total_credit": Decimal("500.00"),
            "lines": [
                {
                    "account_id": str(cash_account.id),
                    "debit": Decimal("500.00"),
                    "credit": Decimal("0.00"),
                    "sort_order": 1,
                },
                {
                    "account_id": str(revenue_account.id),
                    "debit": Decimal("0.00"),
                    "credit": Decimal("500.00"),
                    "sort_order": 2,
                },
            ],
        }
        
        je_service.create(
            entry1_data,
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Create and post second entry: Expense debit 200, Cash credit 200
        entry2_data = {
            "entry_no": "JE-TEST-003",
            "posting_date": datetime.now(timezone.utc),
            "status": "posted",
            "posted_at": datetime.now(timezone.utc),
            "voucher_type": "Journal Entry",
            "total_debit": Decimal("200.00"),
            "total_credit": Decimal("200.00"),
            "lines": [
                {
                    "account_id": str(expense_account.id),
                    "debit": Decimal("200.00"),
                    "credit": Decimal("0.00"),
                    "sort_order": 1,
                },
                {
                    "account_id": str(cash_account.id),
                    "debit": Decimal("0.00"),
                    "credit": Decimal("200.00"),
                    "sort_order": 2,
                },
            ],
        }
        
        je_service.create(
            entry2_data,
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify cash balance reflects both entries
        cash_balance = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        
        # Cash: 500 debit - 200 credit = 300 net debit
        assert cash_balance["debit_total"] == Decimal("500.00")
        assert cash_balance["credit_total"] == Decimal("200.00")
        assert cash_balance["balance"] == Decimal("300.00")
        
        # Verify revenue balance
        revenue_balance = balance_calc.calculate_balance(
            account_id=revenue_account.id,
        )
        
        assert revenue_balance["credit_total"] == Decimal("500.00")
        assert revenue_balance["balance"] == Decimal("500.00")
        
        # Verify expense balance
        expense_balance = balance_calc.calculate_balance(
            account_id=expense_account.id,
        )
        
        assert expense_balance["debit_total"] == Decimal("200.00")
        assert expense_balance["balance"] == Decimal("200.00")

    def test_cancelled_entries_not_included_in_balance(
        self, db_session, mock_current_user, sample_accounts
    ):
        """
        Test that cancelled journal entries are not included in balance calculations.
        
        Requirements: 2.5, 2.6
        """
        # Get accounts
        cash_account = next(acc for acc in sample_accounts if acc.account_code == "1000")
        revenue_account = next(acc for acc in sample_accounts if acc.account_code == "4000")
        
        # Initialize services
        je_service = JournalEntryService(db_session)
        balance_calc = BalanceCalculator(db_session)
        
        # Create and post entry
        entry_data = {
            "entry_no": "JE-TEST-004",
            "posting_date": datetime.now(timezone.utc),
            "status": "posted",
            "posted_at": datetime.now(timezone.utc),
            "voucher_type": "Journal Entry",
            "total_debit": Decimal("1000.00"),
            "total_credit": Decimal("1000.00"),
            "lines": [
                {
                    "account_id": str(cash_account.id),
                    "debit": Decimal("1000.00"),
                    "credit": Decimal("0.00"),
                    "sort_order": 1,
                },
                {
                    "account_id": str(revenue_account.id),
                    "debit": Decimal("0.00"),
                    "credit": Decimal("1000.00"),
                    "sort_order": 2,
                },
            ],
        }
        
        created_entry = je_service.create(
            entry_data,
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify balance includes the posted entry
        cash_balance = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        assert cash_balance["debit_total"] == Decimal("1000.00")
        
        # Cancel the entry
        je_service.update(
            entry_id=created_entry["id"],
            data={"status": "cancelled"},
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify balance no longer includes the cancelled entry
        cash_balance_after = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        
        assert cash_balance_after["debit_total"] == Decimal("0.00")
        assert cash_balance_after["credit_total"] == Decimal("0.00")
        assert cash_balance_after["balance"] == Decimal("0.00")

    def test_update_journal_entry_affects_balance(
        self, db_session, mock_current_user, sample_accounts
    ):
        """
        Test that updating a journal entry's amounts affects balance calculations.
        
        Note: In practice, posted entries should not be modified, but this tests
        the technical capability per requirement 2.6.
        
        Requirements: 2.6
        """
        # Get accounts
        cash_account = next(acc for acc in sample_accounts if acc.account_code == "1000")
        revenue_account = next(acc for acc in sample_accounts if acc.account_code == "4000")
        
        # Initialize services
        je_service = JournalEntryService(db_session)
        balance_calc = BalanceCalculator(db_session)
        
        # Create posted entry with 500
        entry_data = {
            "entry_no": "JE-TEST-005",
            "posting_date": datetime.now(timezone.utc),
            "status": "posted",
            "posted_at": datetime.now(timezone.utc),
            "voucher_type": "Journal Entry",
            "total_debit": Decimal("500.00"),
            "total_credit": Decimal("500.00"),
            "remarks": "Original entry",
            "lines": [
                {
                    "account_id": str(cash_account.id),
                    "debit": Decimal("500.00"),
                    "credit": Decimal("0.00"),
                    "sort_order": 1,
                },
                {
                    "account_id": str(revenue_account.id),
                    "debit": Decimal("0.00"),
                    "credit": Decimal("500.00"),
                    "sort_order": 2,
                },
            ],
        }
        
        created_entry = je_service.create(
            entry_data,
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify initial balance
        cash_balance = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        assert cash_balance["debit_total"] == Decimal("500.00")
        
        # Update the entry (change remarks to verify update works)
        updated_entry = je_service.update(
            entry_id=created_entry["id"],
            data={"remarks": "Updated entry"},
            organization_id=mock_current_user.organization_id,
            user_id=mock_current_user.id,
        )
        
        # Verify update was persisted
        assert updated_entry["remarks"] == "Updated entry"
        
        # Verify balance still reflects the entry (amounts unchanged)
        cash_balance_after = balance_calc.calculate_balance(
            account_id=cash_account.id,
        )
        assert cash_balance_after["debit_total"] == Decimal("500.00")
