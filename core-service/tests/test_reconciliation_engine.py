"""
Unit tests for ReconciliationEngine service

Tests the core reconciliation engine methods for retrieving unreconciled
transactions, journal entries, and calculating reconciliation differences.
"""

import pytest
from datetime import date, datetime, UTC
from decimal import Decimal
from uuid import uuid4, UUID

from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation
from app.models.journal_entry import JournalEntry
from app.models.base import JournalStatus
from app.services.reconciliation_engine import ReconciliationEngine


@pytest.fixture
def reconciliation_engine(db_session: Session):
    """Create a ReconciliationEngine instance for testing"""
    return ReconciliationEngine(db=db_session)


@pytest.fixture
def organization_id():
    """Generate a test organization ID"""
    return uuid4()


@pytest.fixture
def bank_account_id():
    """Generate a test bank account ID"""
    return uuid4()


@pytest.fixture
def gl_account_id():
    """Generate a test GL account ID"""
    return uuid4()


class TestGetUnreconciledTransactions:
    """Tests for get_unreconciled_transactions method"""

    def test_returns_cleared_unreconciled_transactions(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that only cleared, unreconciled transactions are returned"""
        # Create test transactions with different statuses
        cleared_unreconciled = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction 1",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        pending_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 16),
            transaction_amount=Decimal("200.00"),
            transaction_description="Test transaction 2",
            bank_reference="REF002",
            transaction_status="pending",
            transaction_type="credit",
            reconciled_at=None
        )
        
        reconciled_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 17),
            transaction_amount=Decimal("300.00"),
            transaction_description="Test transaction 3",
            bank_reference="REF003",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC)
        )
        
        db_session.add_all([cleared_unreconciled, pending_transaction, reconciled_transaction])
        db_session.commit()
        
        # Get unreconciled transactions
        result = reconciliation_engine.get_unreconciled_transactions(
            bank_account_id=bank_account_id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Should only return the cleared, unreconciled transaction
        assert len(result) == 1
        assert result[0].id == cleared_unreconciled.id
        assert result[0].transaction_status == "cleared"
        assert result[0].reconciled_at is None

    def test_filters_by_date_range(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that transactions are filtered by date range"""
        # Create transactions on different dates
        transaction_in_range = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="In range",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        transaction_before_range = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2023, 12, 31),
            transaction_amount=Decimal("200.00"),
            transaction_description="Before range",
            bank_reference="REF002",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        transaction_after_range = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 2, 1),
            transaction_amount=Decimal("300.00"),
            transaction_description="After range",
            bank_reference="REF003",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        db_session.add_all([transaction_in_range, transaction_before_range, transaction_after_range])
        db_session.commit()
        
        # Get unreconciled transactions for January 2024
        result = reconciliation_engine.get_unreconciled_transactions(
            bank_account_id=bank_account_id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Should only return the transaction in range
        assert len(result) == 1
        assert result[0].id == transaction_in_range.id

    def test_filters_by_bank_account(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id
    ):
        """Test that transactions are filtered by bank account"""
        bank_account_1 = uuid4()
        bank_account_2 = uuid4()
        
        transaction_account_1 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_1,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Account 1",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        transaction_account_2 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_2,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("200.00"),
            transaction_description="Account 2",
            bank_reference="REF002",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        db_session.add_all([transaction_account_1, transaction_account_2])
        db_session.commit()
        
        # Get unreconciled transactions for bank_account_1
        result = reconciliation_engine.get_unreconciled_transactions(
            bank_account_id=bank_account_1,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Should only return transaction from bank_account_1
        assert len(result) == 1
        assert result[0].id == transaction_account_1.id


class TestGetUnreconciledJournalEntries:
    """Tests for get_unreconciled_journal_entries method"""

    def test_returns_posted_unreconciled_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        gl_account_id
    ):
        """Test that only posted, unreconciled journal entries are returned"""
        # Create test journal entries with different statuses
        posted_unreconciled = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        draft_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 16, tzinfo=UTC),
            status=JournalStatus.DRAFT,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        db_session.add_all([posted_unreconciled, draft_entry])
        db_session.commit()
        
        # Get unreconciled journal entries
        result = reconciliation_engine.get_unreconciled_journal_entries(
            gl_account_id=gl_account_id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Should only return the posted entry
        assert len(result) == 1
        assert result[0].id == posted_unreconciled.id
        assert result[0].status == JournalStatus.POSTED

    def test_excludes_reconciled_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        gl_account_id,
        bank_account_id
    ):
        """Test that reconciled journal entries are excluded"""
        # Create a posted journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add(journal_entry)
        db_session.commit()
        
        # Create a bank transaction and reconciliation
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC)
        )
        
        db_session.add(bank_transaction)
        db_session.commit()
        
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="manual",
            reconciliation_status="confirmed",
            is_active=True
        )
        
        db_session.add(reconciliation)
        db_session.commit()
        
        # Get unreconciled journal entries
        result = reconciliation_engine.get_unreconciled_journal_entries(
            gl_account_id=gl_account_id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Should not return the reconciled entry
        assert len(result) == 0

    def test_filters_by_date_range(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        gl_account_id
    ):
        """Test that journal entries are filtered by date range"""
        # Create entries on different dates
        entry_in_range = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        entry_before_range = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2023, 12, 31, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        entry_after_range = JournalEntry(
            organization_id=organization_id,
            entry_no="JE003",
            posting_date=datetime(2024, 2, 1, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("300.00"),
            total_credit=Decimal("300.00")
        )
        
        db_session.add_all([entry_in_range, entry_before_range, entry_after_range])
        db_session.commit()
        
        # Get unreconciled journal entries for January 2024
        result = reconciliation_engine.get_unreconciled_journal_entries(
            gl_account_id=gl_account_id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Should only return the entry in range
        assert len(result) == 1
        assert result[0].id == entry_in_range.id


class TestCalculateReconciliationDifference:
    """Tests for calculate_reconciliation_difference method"""

    def test_calculates_positive_difference(
        self,
        reconciliation_engine: ReconciliationEngine
    ):
        """Test calculation when bank balance is higher than GL balance"""
        bank_balance = Decimal("1000.00")
        gl_balance = Decimal("800.00")
        
        difference = reconciliation_engine.calculate_reconciliation_difference(
            bank_balance=bank_balance,
            gl_balance=gl_balance
        )
        
        assert difference == Decimal("200.00")

    def test_calculates_negative_difference(
        self,
        reconciliation_engine: ReconciliationEngine
    ):
        """Test calculation when GL balance is higher than bank balance"""
        bank_balance = Decimal("800.00")
        gl_balance = Decimal("1000.00")
        
        difference = reconciliation_engine.calculate_reconciliation_difference(
            bank_balance=bank_balance,
            gl_balance=gl_balance
        )
        
        assert difference == Decimal("-200.00")

    def test_calculates_zero_difference(
        self,
        reconciliation_engine: ReconciliationEngine
    ):
        """Test calculation when balances are equal"""
        bank_balance = Decimal("1000.00")
        gl_balance = Decimal("1000.00")
        
        difference = reconciliation_engine.calculate_reconciliation_difference(
            bank_balance=bank_balance,
            gl_balance=gl_balance
        )
        
        assert difference == Decimal("0.00")

    def test_handles_decimal_precision(
        self,
        reconciliation_engine: ReconciliationEngine
    ):
        """Test that decimal precision is maintained"""
        bank_balance = Decimal("1000.55")
        gl_balance = Decimal("800.33")
        
        difference = reconciliation_engine.calculate_reconciliation_difference(
            bank_balance=bank_balance,
            gl_balance=gl_balance
        )
        
        assert difference == Decimal("200.22")



class TestCreateManualMatch:
    """Tests for create_manual_match method"""

    def test_creates_manual_reconciliation_successfully(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test successful creation of manual reconciliation"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create a posted journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create manual reconciliation
        reconciliations = reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry.id],
            reconciled_by="test_user",
            organization_id=organization_id,
            notes="Test reconciliation"
        )
        
        # Verify reconciliation was created
        assert len(reconciliations) == 1
        reconciliation = reconciliations[0]
        
        # Requirement 7.4: reconciliation_type is "manual"
        assert reconciliation.reconciliation_type == "manual"
        
        # Requirement 7.5: reconciliation_status is "confirmed"
        assert reconciliation.reconciliation_status == "confirmed"
        
        # Requirement 7.8: reconciled_by is stored
        assert reconciliation.reconciled_by == "test_user"
        
        # Requirement 7.7: reconciled_at is set
        assert reconciliation.reconciled_at is not None
        
        # Requirement 7.9: notes are stored
        assert reconciliation.notes == "Test reconciliation"
        
        # Verify match confidence is 1.0 for manual matches
        assert reconciliation.match_confidence == Decimal("1.0")
        
        # Verify reconciliation is active
        assert reconciliation.is_active is True
        
        # Refresh bank transaction to get updated status
        db_session.refresh(bank_transaction)
        
        # Requirement 7.6: bank transaction status is "reconciled"
        assert bank_transaction.transaction_status == "reconciled"
        assert bank_transaction.reconciled_at is not None

    def test_prevents_double_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that double reconciliation is prevented (Requirement 7.10)"""
        # Create a reconciled bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC)
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Attempt to reconcile already reconciled transaction
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_manual_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[journal_entry.id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "already reconciled" in str(exc_info.value).lower()

    def test_prevents_reconciliation_with_active_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that reconciliation is prevented if active reconciliation exists"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Create first reconciliation
        reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Attempt to create second reconciliation for same transaction
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_manual_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[journal_entry_2.id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        # The error message should indicate the transaction is already reconciled
        # (either "already reconciled" or "already has an active reconciliation")
        error_msg = str(exc_info.value).lower()
        assert "already reconciled" in error_msg or "already has an active reconciliation" in error_msg

    def test_raises_error_for_nonexistent_bank_transaction(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id
    ):
        """Test that error is raised for nonexistent bank transaction"""
        nonexistent_id = uuid4()
        journal_entry_id = uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_manual_match(
                bank_transaction_id=nonexistent_id,
                journal_entry_ids=[journal_entry_id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_raises_error_for_nonexistent_journal_entry(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that error is raised for nonexistent journal entry"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        db_session.add(bank_transaction)
        db_session.commit()
        
        nonexistent_je_id = uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_manual_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[nonexistent_je_id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_supports_many_to_one_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that multiple journal entries can be reconciled to one bank transaction"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Batch deposit",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create multiple journal entries
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Create manual reconciliation with multiple journal entries
        reconciliations = reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
            reconciled_by="test_user",
            organization_id=organization_id,
            notes="Many-to-one reconciliation"
        )
        
        # Verify multiple reconciliation records were created
        assert len(reconciliations) == 2
        
        # Verify both reconciliations are linked to the same bank transaction
        assert all(r.bank_transaction_id == bank_transaction.id for r in reconciliations)
        
        # Verify each reconciliation is linked to a different journal entry
        je_ids = {r.journal_entry_id for r in reconciliations}
        assert je_ids == {journal_entry_1.id, journal_entry_2.id}
        
        # Verify all reconciliations have correct type and status
        assert all(r.reconciliation_type == "manual" for r in reconciliations)
        assert all(r.reconciliation_status == "confirmed" for r in reconciliations)
        
        # Verify bank transaction is reconciled
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"

    def test_notes_parameter_is_optional(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that notes parameter is optional"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create manual reconciliation without notes
        reconciliations = reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation was created successfully
        assert len(reconciliations) == 1
        assert reconciliations[0].notes is None



class TestCreateManyToOneMatch:
    """Tests for create_many_to_one_match method"""

    def test_creates_many_to_one_reconciliation_successfully(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test successful creation of many-to-one reconciliation (Requirements 10.1-10.8)"""
        # Create a cleared bank transaction with amount 300.00
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Batch deposit",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create multiple journal entries that sum to 300.00
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Create many-to-one reconciliation
        reconciliations = reconciliation_engine.create_many_to_one_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
            reconciled_by="test_user",
            organization_id=organization_id,
            notes="Many-to-one reconciliation test"
        )
        
        # Verify multiple reconciliation records were created (Requirement 10.5)
        assert len(reconciliations) == 2
        
        # Verify all reconciliations are linked to the same bank transaction
        assert all(r.bank_transaction_id == bank_transaction.id for r in reconciliations)
        
        # Verify each reconciliation is linked to a different journal entry
        je_ids = {r.journal_entry_id for r in reconciliations}
        assert je_ids == {journal_entry_1.id, journal_entry_2.id}
        
        # Requirement 10.6: reconciliation_type is "many_to_one"
        assert all(r.reconciliation_type == "many_to_one" for r in reconciliations)
        
        # Requirement 10.7: reconciliation_status is "confirmed"
        assert all(r.reconciliation_status == "confirmed" for r in reconciliations)
        
        # Verify reconciled_by is stored
        assert all(r.reconciled_by == "test_user" for r in reconciliations)
        
        # Verify reconciled_at is set
        assert all(r.reconciled_at is not None for r in reconciliations)
        
        # Verify notes are stored
        assert all(r.notes == "Many-to-one reconciliation test" for r in reconciliations)
        
        # Verify match confidence is 1.0
        assert all(r.match_confidence == Decimal("1.0") for r in reconciliations)
        
        # Verify reconciliations are active
        assert all(r.is_active is True for r in reconciliations)
        
        # Refresh bank transaction to get updated status
        db_session.refresh(bank_transaction)
        
        # Requirement 10.8: bank transaction status is "reconciled"
        assert bank_transaction.transaction_status == "reconciled"
        assert bank_transaction.reconciled_at is not None

    def test_calculates_sum_correctly(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that sum of journal entries is calculated correctly (Requirement 10.2)"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("450.75"),
            transaction_description="Multiple sales",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create journal entries with different amounts
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("150.25"),
            total_credit=Decimal("150.25")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.50"),
            total_credit=Decimal("200.50")
        )
        
        journal_entry_3 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE003",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2, journal_entry_3])
        db_session.commit()
        
        # Create many-to-one reconciliation
        reconciliations = reconciliation_engine.create_many_to_one_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id, journal_entry_2.id, journal_entry_3.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation was successful (sum matches)
        assert len(reconciliations) == 3
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"

    def test_validates_sum_equals_transaction_amount(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that reconciliation is prevented when sum doesn't match (Requirements 10.3, 10.4)"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Batch deposit",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create journal entries that sum to 250.00 (doesn't match 300.00)
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("150.00"),
            total_credit=Decimal("150.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Attempt to create many-to-one reconciliation with mismatched sum
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_many_to_one_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        # Verify error message mentions the mismatch
        error_msg = str(exc_info.value).lower()
        assert "does not equal" in error_msg or "difference" in error_msg
        
        # Verify bank transaction status is still "cleared" (not reconciled)
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "cleared"

    def test_allows_reconciliation_within_tolerance(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that reconciliation is allowed when difference is within 0.01 tolerance (Requirement 10.3)"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Batch deposit",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create journal entries that sum to 300.01 (within 0.01 tolerance)
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.01"),
            total_credit=Decimal("200.01")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Create many-to-one reconciliation (should succeed)
        reconciliations = reconciliation_engine.create_many_to_one_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation was successful
        assert len(reconciliations) == 2
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"

    def test_requires_at_least_two_journal_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that many-to-one requires at least 2 journal entries (Requirement 10.1)"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Single entry",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create only one journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Attempt to create many-to-one reconciliation with only one entry
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_many_to_one_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[journal_entry.id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        # Verify error message mentions requirement for multiple entries
        error_msg = str(exc_info.value).lower()
        assert "at least 2" in error_msg or "multiple" in error_msg

    def test_prevents_double_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that double reconciliation is prevented"""
        # Create a reconciled bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Already reconciled",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC)
        )
        
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Attempt to reconcile already reconciled transaction
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_many_to_one_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "already reconciled" in str(exc_info.value).lower()

    def test_raises_error_for_nonexistent_bank_transaction(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id
    ):
        """Test that error is raised for nonexistent bank transaction"""
        nonexistent_id = uuid4()
        journal_entry_id_1 = uuid4()
        journal_entry_id_2 = uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_many_to_one_match(
                bank_transaction_id=nonexistent_id,
                journal_entry_ids=[journal_entry_id_1, journal_entry_id_2],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_raises_error_for_nonexistent_journal_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that error is raised for nonexistent journal entries"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Test",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        db_session.add(bank_transaction)
        db_session.commit()
        
        nonexistent_je_id_1 = uuid4()
        nonexistent_je_id_2 = uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.create_many_to_one_match(
                bank_transaction_id=bank_transaction.id,
                journal_entry_ids=[nonexistent_je_id_1, nonexistent_je_id_2],
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_notes_parameter_is_optional(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that notes parameter is optional"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Batch deposit",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create journal entries
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Create many-to-one reconciliation without notes
        reconciliations = reconciliation_engine.create_many_to_one_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation was created successfully
        assert len(reconciliations) == 2
        assert all(r.notes is None for r in reconciliations)


class TestUndoReconciliation:
    """Tests for undo_reconciliation method"""

    def test_undo_reconciliation_successfully(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test successful undo of a reconciliation (Requirements 17.1-17.8)"""
        # Create and reconcile a transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create reconciliation
        reconciliations = reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry.id],
            reconciled_by="test_user",
            organization_id=organization_id,
            notes="Initial reconciliation"
        )
        
        reconciliation = reconciliations[0]
        
        # Verify initial state
        assert reconciliation.reconciliation_status == "confirmed"
        assert reconciliation.is_active is True
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"
        assert bank_transaction.reconciled_at is not None
        
        # Undo the reconciliation
        undone_reconciliation = reconciliation_engine.undo_reconciliation(
            reconciliation_id=reconciliation.id,
            undone_by="admin_user",
            organization_id=organization_id,
            reason="Incorrect match"
        )
        
        # Requirement 17.2: Reconciliation status updated to "rejected"
        assert undone_reconciliation.reconciliation_status == "rejected"
        
        # Requirement 17.6: Reconciliation record preserved (not deleted)
        assert undone_reconciliation.is_active is False
        db_reconciliation = db_session.query(BankReconciliation).filter_by(id=reconciliation.id).first()
        assert db_reconciliation is not None
        
        # Requirement 17.7: Undo action logged with user and timestamp
        assert undone_reconciliation.undone_by == "admin_user"
        assert undone_reconciliation.undone_at is not None
        
        # Requirement 17.8: Reason stored
        assert undone_reconciliation.undo_reason == "Incorrect match"
        
        # Refresh bank transaction
        db_session.refresh(bank_transaction)
        
        # Requirement 17.3: Bank transaction status back to "cleared"
        assert bank_transaction.transaction_status == "cleared"
        
        # Requirement 17.4: reconciled_at set to null
        assert bank_transaction.reconciled_at is None

    def test_undo_prevents_undoing_non_confirmed_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that only confirmed reconciliations can be undone"""
        # Create a suggested reconciliation
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a suggested reconciliation (not confirmed)
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.8"),
            is_active=True
        )
        
        db_session.add(reconciliation)
        db_session.commit()
        
        # Attempt to undo suggested reconciliation
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.undo_reconciliation(
                reconciliation_id=reconciliation.id,
                undone_by="test_user",
                organization_id=organization_id,
                reason="Test"
            )
        
        assert "cannot be undone" in str(exc_info.value).lower()

    def test_undo_prevents_undoing_already_undone_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that already undone reconciliations cannot be undone again"""
        # Create and reconcile a transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create reconciliation
        reconciliations = reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        reconciliation = reconciliations[0]
        
        # Undo the reconciliation
        reconciliation_engine.undo_reconciliation(
            reconciliation_id=reconciliation.id,
            undone_by="admin_user",
            organization_id=organization_id,
            reason="First undo"
        )
        
        # Attempt to undo again
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.undo_reconciliation(
                reconciliation_id=reconciliation.id,
                undone_by="admin_user",
                organization_id=organization_id,
                reason="Second undo"
            )
        
        assert "cannot be undone" in str(exc_info.value).lower()

    def test_undo_enforces_90_day_restriction_for_non_elevated_users(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test 90-day restriction for non-elevated users (Requirement 17.9)"""
        from datetime import timedelta
        
        # Create a transaction reconciled 91 days ago
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Old transaction",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC) - timedelta(days=91)
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create old reconciliation
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="manual",
            reconciliation_status="confirmed",
            match_confidence=Decimal("1.0"),
            reconciled_by="test_user",
            reconciled_at=datetime.now(UTC) - timedelta(days=91),
            is_active=True
        )
        
        db_session.add(reconciliation)
        db_session.commit()
        
        # Attempt to undo without elevated permissions
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.undo_reconciliation(
                reconciliation_id=reconciliation.id,
                undone_by="regular_user",
                organization_id=organization_id,
                reason="Too old",
                has_elevated_permissions=False
            )
        
        assert "90 days" in str(exc_info.value).lower()
        assert "elevated permissions" in str(exc_info.value).lower()

    def test_undo_allows_old_reconciliation_with_elevated_permissions(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that elevated users can undo old reconciliations (Requirement 17.9)"""
        from datetime import timedelta
        
        # Create a transaction reconciled 91 days ago
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Old transaction",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC) - timedelta(days=91)
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create old reconciliation
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="manual",
            reconciliation_status="confirmed",
            match_confidence=Decimal("1.0"),
            reconciled_by="test_user",
            reconciled_at=datetime.now(UTC) - timedelta(days=91),
            is_active=True
        )
        
        db_session.add(reconciliation)
        db_session.commit()
        
        # Undo with elevated permissions - should succeed
        undone_reconciliation = reconciliation_engine.undo_reconciliation(
            reconciliation_id=reconciliation.id,
            undone_by="admin_user",
            organization_id=organization_id,
            reason="Admin override",
            has_elevated_permissions=True
        )
        
        assert undone_reconciliation.reconciliation_status == "rejected"
        assert undone_reconciliation.is_active is False

    def test_undo_handles_many_to_one_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test undoing one reconciliation in a many-to-one scenario"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("300.00"),
            transaction_description="Batch deposit",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        # Create multiple journal entries
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("200.00"),
            total_credit=Decimal("200.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry_1, journal_entry_2])
        db_session.commit()
        
        # Create many-to-one reconciliation
        reconciliations = reconciliation_engine.create_many_to_one_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry_1.id, journal_entry_2.id],
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Verify bank transaction is reconciled
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"
        
        # Undo one of the reconciliations
        undone_reconciliation = reconciliation_engine.undo_reconciliation(
            reconciliation_id=reconciliations[0].id,
            undone_by="admin_user",
            organization_id=organization_id,
            reason="Incorrect match"
        )
        
        # Verify the undone reconciliation
        assert undone_reconciliation.reconciliation_status == "rejected"
        assert undone_reconciliation.is_active is False
        
        # Bank transaction should still be reconciled because there's another active reconciliation
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"
        assert bank_transaction.reconciled_at is not None
        
        # Undo the second reconciliation
        undone_reconciliation_2 = reconciliation_engine.undo_reconciliation(
            reconciliation_id=reconciliations[1].id,
            undone_by="admin_user",
            organization_id=organization_id,
            reason="Incorrect match"
        )
        
        # Now bank transaction should be back to cleared
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "cleared"
        assert bank_transaction.reconciled_at is None

    def test_undo_raises_error_for_nonexistent_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id
    ):
        """Test that error is raised for nonexistent reconciliation"""
        nonexistent_id = uuid4()
        
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.undo_reconciliation(
                reconciliation_id=nonexistent_id,
                undone_by="test_user",
                organization_id=organization_id,
                reason="Test"
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_undo_preserves_original_reconciliation_data(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that original reconciliation data is preserved after undo (Requirement 17.6, 17.10)"""
        # Create and reconcile a transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create reconciliation
        reconciliations = reconciliation_engine.create_manual_match(
            bank_transaction_id=bank_transaction.id,
            journal_entry_ids=[journal_entry.id],
            reconciled_by="original_user",
            organization_id=organization_id,
            notes="Original notes"
        )
        
        reconciliation = reconciliations[0]
        original_reconciled_at = reconciliation.reconciled_at
        original_reconciled_by = reconciliation.reconciled_by
        original_notes = reconciliation.notes
        
        # Undo the reconciliation
        undone_reconciliation = reconciliation_engine.undo_reconciliation(
            reconciliation_id=reconciliation.id,
            undone_by="admin_user",
            organization_id=organization_id,
            reason="Undo reason"
        )
        
        # Verify original data is preserved
        assert undone_reconciliation.reconciled_by == original_reconciled_by
        assert undone_reconciliation.reconciled_at == original_reconciled_at
        assert undone_reconciliation.notes == original_notes
        
        # Verify undo data is added
        assert undone_reconciliation.undone_by == "admin_user"
        assert undone_reconciliation.undone_at is not None
        assert undone_reconciliation.undo_reason == "Undo reason"
        
        # Verify record still exists in database (Requirement 17.10: display history)
        db_reconciliation = db_session.query(BankReconciliation).filter_by(id=reconciliation.id).first()
        assert db_reconciliation is not None
        assert db_reconciliation.reconciliation_status == "rejected"



class TestReconcileWithCurrencyConversion:
    """Tests for reconcile_with_currency_conversion method"""

    def test_creates_multi_currency_reconciliation_successfully(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test successful multi-currency reconciliation with exchange rate"""
        # Create a bank transaction in USD
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),  # 100 USD
            transaction_description="Payment from customer",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create a journal entry in EUR (assuming 1 USD = 0.85 EUR)
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),  # 85 EUR
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Reconcile with exchange rate
        exchange_rate = Decimal("0.85")
        reconciliation = reconciliation_engine.reconcile_with_currency_conversion(
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            exchange_rate=exchange_rate,
            reconciled_by="test_user",
            organization_id=organization_id,
            notes="Multi-currency reconciliation"
        )
        
        # Verify reconciliation was created
        assert reconciliation is not None
        assert reconciliation.bank_transaction_id == bank_transaction.id
        assert reconciliation.journal_entry_id == journal_entry.id
        assert reconciliation.reconciliation_type == "manual"
        assert reconciliation.reconciliation_status == "confirmed"
        assert reconciliation.match_confidence == Decimal("1.0")
        
        # Requirement 19.6: Verify exchange_rate is stored
        assert reconciliation.exchange_rate == exchange_rate
        
        # Requirement 19.4: Verify converted_amount is calculated correctly
        expected_converted = Decimal("100.00") * Decimal("0.85")
        assert reconciliation.converted_amount == expected_converted
        
        # Verify bank transaction is updated
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"
        assert bank_transaction.reconciled_at is not None

    def test_validates_converted_amount_within_tolerance(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that reconciliation succeeds when converted amount is within 0.01 tolerance"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create a journal entry with amount that's within tolerance after conversion
        # 100 * 0.8501 = 85.01, which is within 0.01 of 85.00
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Reconcile with exchange rate that results in amount within tolerance
        exchange_rate = Decimal("0.8501")
        reconciliation = reconciliation_engine.reconcile_with_currency_conversion(
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            exchange_rate=exchange_rate,
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Requirement 19.5: Verify reconciliation succeeds within tolerance
        assert reconciliation is not None
        assert reconciliation.exchange_rate == exchange_rate

    def test_rejects_converted_amount_outside_tolerance(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that reconciliation fails when converted amount exceeds 0.01 tolerance"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create a journal entry with amount that's outside tolerance after conversion
        # 100 * 0.85 = 85.00, but journal entry is 86.00 (difference > 0.01)
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("86.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Requirement 19.5: Attempt reconciliation should fail
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=bank_transaction.id,
                journal_entry_id=journal_entry.id,
                exchange_rate=Decimal("0.85"),
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "does not match" in str(exc_info.value)
        assert "within tolerance" in str(exc_info.value)

    def test_requires_exchange_rate_parameter(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that exchange_rate parameter is required"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create a journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Requirement 19.3: Attempt reconciliation without exchange_rate should fail
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=bank_transaction.id,
                journal_entry_id=journal_entry.id,
                exchange_rate=None,
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "Exchange rate is required" in str(exc_info.value)

    def test_validates_positive_exchange_rate(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that exchange_rate must be positive"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create a journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Test with negative exchange rate
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=bank_transaction.id,
                journal_entry_id=journal_entry.id,
                exchange_rate=Decimal("-0.85"),
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "must be positive" in str(exc_info.value)
        
        # Test with zero exchange rate
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=bank_transaction.id,
                journal_entry_id=journal_entry.id,
                exchange_rate=Decimal("0"),
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "must be positive" in str(exc_info.value)

    def test_prevents_double_reconciliation(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that already reconciled transactions cannot be reconciled again"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create journal entries
        journal_entry1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        journal_entry2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry1, journal_entry2])
        db_session.commit()
        
        # First reconciliation
        reconciliation_engine.reconcile_with_currency_conversion(
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry1.id,
            exchange_rate=Decimal("0.85"),
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Attempt second reconciliation should fail
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=bank_transaction.id,
                journal_entry_id=journal_entry2.id,
                exchange_rate=Decimal("0.85"),
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "already reconciled" in str(exc_info.value).lower()

    def test_raises_error_for_nonexistent_bank_transaction(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that error is raised for non-existent bank transaction"""
        # Create a journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add(journal_entry)
        db_session.commit()
        
        # Attempt reconciliation with non-existent bank transaction
        fake_transaction_id = uuid4()
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=fake_transaction_id,
                journal_entry_id=journal_entry.id,
                exchange_rate=Decimal("0.85"),
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "not found" in str(exc_info.value)

    def test_raises_error_for_nonexistent_journal_entry(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that error is raised for non-existent journal entry"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        db_session.add(bank_transaction)
        db_session.commit()
        
        # Attempt reconciliation with non-existent journal entry
        fake_entry_id = uuid4()
        with pytest.raises(ValueError) as exc_info:
            reconciliation_engine.reconcile_with_currency_conversion(
                bank_transaction_id=bank_transaction.id,
                journal_entry_id=fake_entry_id,
                exchange_rate=Decimal("0.85"),
                reconciled_by="test_user",
                organization_id=organization_id
            )
        
        assert "not found" in str(exc_info.value)

    def test_notes_parameter_is_optional(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that notes parameter is optional"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit"
        )
        
        # Create a journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("85.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Reconcile without notes
        reconciliation = reconciliation_engine.reconcile_with_currency_conversion(
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            exchange_rate=Decimal("0.85"),
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        assert reconciliation is not None
        assert reconciliation.notes is None

    def test_handles_credit_journal_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that reconciliation works with journal entries that have credit amounts"""
        # Create a bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Payment",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="debit"
        )
        
        # Create a journal entry with credit amount
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("0.00"),
            total_credit=Decimal("85.00")  # Credit amount
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Reconcile with exchange rate
        exchange_rate = Decimal("0.85")
        reconciliation = reconciliation_engine.reconcile_with_currency_conversion(
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            exchange_rate=exchange_rate,
            reconciled_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation was created
        assert reconciliation is not None
        assert reconciliation.exchange_rate == exchange_rate
        assert reconciliation.converted_amount == Decimal("100.00") * Decimal("0.85")


class TestCalculateBankBalance:
    """Test calculate_bank_balance method"""

    def test_calculates_balance_from_cleared_and_reconciled_transactions(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID
    ):
        """Test that bank balance is calculated from cleared and reconciled transactions"""
        # Create test transactions
        # Credit transactions increase balance
        credit_transaction_1 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        credit_transaction_2 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 16),
            transaction_amount=Decimal("500.00"),
            transaction_type="credit",
            transaction_status="reconciled",
            bank_reference="TXN-002"
        )
        # Debit transactions decrease balance
        debit_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 17),
            transaction_amount=Decimal("300.00"),
            transaction_type="debit",
            transaction_status="cleared",
            bank_reference="TXN-003"
        )
        
        db_session.add_all([credit_transaction_1, credit_transaction_2, debit_transaction])
        db_session.commit()
        
        # Calculate balance
        balance = reconciliation_engine.calculate_bank_balance(
            bank_account_id=bank_account_id,
            organization_id=organization_id
        )
        
        # Expected: 1000 + 500 - 300 = 1200
        assert balance == Decimal("1200.00")

    def test_excludes_pending_transactions(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID
    ):
        """Test that pending transactions are excluded from balance calculation"""
        # Create cleared transaction
        cleared_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        # Create pending transaction (should be excluded)
        pending_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 16),
            transaction_amount=Decimal("500.00"),
            transaction_type="credit",
            transaction_status="pending",
            bank_reference="TXN-002"
        )
        
        db_session.add_all([cleared_transaction, pending_transaction])
        db_session.commit()
        
        # Calculate balance
        balance = reconciliation_engine.calculate_bank_balance(
            bank_account_id=bank_account_id,
            organization_id=organization_id
        )
        
        # Expected: only cleared transaction = 1000
        assert balance == Decimal("1000.00")

    def test_filters_by_as_of_date(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID
    ):
        """Test that balance calculation filters by as_of_date"""
        # Create transactions on different dates
        transaction_1 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        transaction_2 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 20),
            transaction_amount=Decimal("500.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-002"
        )
        
        db_session.add_all([transaction_1, transaction_2])
        db_session.commit()
        
        # Calculate balance as of Jan 17 (should only include first transaction)
        balance = reconciliation_engine.calculate_bank_balance(
            bank_account_id=bank_account_id,
            organization_id=organization_id,
            as_of_date=date(2024, 1, 17)
        )
        
        # Expected: only first transaction = 1000
        assert balance == Decimal("1000.00")

    def test_returns_zero_for_no_transactions(
        self,
        reconciliation_engine: ReconciliationEngine,
        organization_id: UUID,
        bank_account_id: UUID
    ):
        """Test that balance is zero when there are no transactions"""
        balance = reconciliation_engine.calculate_bank_balance(
            bank_account_id=bank_account_id,
            organization_id=organization_id
        )
        
        assert balance == Decimal("0.00")


class TestCalculateGLBalance:
    """Test calculate_gl_balance method"""

    def test_calculates_balance_from_journal_entry_lines(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        gl_account_id: UUID
    ):
        """Test that GL balance is calculated from journal entry lines"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create journal entry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("1500.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.flush()
        
        # Create journal entry lines for the GL account
        # Debit line (increases balance for asset accounts)
        debit_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry.id,
            account_id=gl_account_id,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00")
        )
        # Credit line (decreases balance for asset accounts)
        credit_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry.id,
            account_id=gl_account_id,
            debit=Decimal("0.00"),
            credit=Decimal("300.00")
        )
        
        db_session.add_all([debit_line, credit_line])
        db_session.commit()
        
        # Calculate balance
        balance = reconciliation_engine.calculate_gl_balance(
            gl_account_id=gl_account_id,
            organization_id=organization_id
        )
        
        # Expected: 1000 (debit) - 300 (credit) = 700
        assert balance == Decimal("700.00")

    def test_excludes_draft_journal_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        gl_account_id: UUID
    ):
        """Test that draft journal entries are excluded from balance calculation"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create posted journal entry
        posted_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00")
        )
        db_session.add(posted_entry)
        db_session.flush()
        
        posted_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=posted_entry.id,
            account_id=gl_account_id,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00")
        )
        db_session.add(posted_line)
        
        # Create draft journal entry (should be excluded)
        draft_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",
            posting_date=date(2024, 1, 16),
            status="draft",
            total_debit=Decimal("500.00"),
            total_credit=Decimal("500.00")
        )
        db_session.add(draft_entry)
        db_session.flush()
        
        draft_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=draft_entry.id,
            account_id=gl_account_id,
            debit=Decimal("500.00"),
            credit=Decimal("0.00")
        )
        db_session.add(draft_line)
        db_session.commit()
        
        # Calculate balance
        balance = reconciliation_engine.calculate_gl_balance(
            gl_account_id=gl_account_id,
            organization_id=organization_id
        )
        
        # Expected: only posted entry = 1000
        assert balance == Decimal("1000.00")

    def test_filters_by_as_of_date(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        gl_account_id: UUID
    ):
        """Test that GL balance calculation filters by as_of_date"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create journal entries on different dates
        entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00")
        )
        db_session.add(entry_1)
        db_session.flush()
        
        line_1 = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=entry_1.id,
            account_id=gl_account_id,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00")
        )
        db_session.add(line_1)
        
        entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",
            posting_date=date(2024, 1, 20),
            status="posted",
            total_debit=Decimal("500.00"),
            total_credit=Decimal("500.00")
        )
        db_session.add(entry_2)
        db_session.flush()
        
        line_2 = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=entry_2.id,
            account_id=gl_account_id,
            debit=Decimal("500.00"),
            credit=Decimal("0.00")
        )
        db_session.add(line_2)
        db_session.commit()
        
        # Calculate balance as of Jan 17 (should only include first entry)
        balance = reconciliation_engine.calculate_gl_balance(
            gl_account_id=gl_account_id,
            organization_id=organization_id,
            as_of_date=date(2024, 1, 17)
        )
        
        # Expected: only first entry = 1000
        assert balance == Decimal("1000.00")

    def test_returns_zero_for_no_journal_entries(
        self,
        reconciliation_engine: ReconciliationEngine,
        organization_id: UUID,
        gl_account_id: UUID
    ):
        """Test that balance is zero when there are no journal entries"""
        balance = reconciliation_engine.calculate_gl_balance(
            gl_account_id=gl_account_id,
            organization_id=organization_id
        )
        
        assert balance == Decimal("0.00")


class TestCalculateUnreconciledAmount:
    """Test calculate_unreconciled_amount method"""

    def test_calculates_difference_between_bank_and_gl_balances(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID,
        gl_account_id: UUID
    ):
        """Test that unreconciled amount is the difference between bank and GL balances"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create bank transactions (bank balance = 1500)
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        db_session.add(bank_transaction)
        
        # Create journal entry (GL balance = 1000)
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00")
        )
        db_session.add(journal_entry)
        db_session.flush()
        
        journal_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry.id,
            account_id=gl_account_id,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00")
        )
        db_session.add(journal_line)
        db_session.commit()
        
        # Calculate unreconciled amount
        unreconciled = reconciliation_engine.calculate_unreconciled_amount(
            bank_account_id=bank_account_id,
            gl_account_id=gl_account_id,
            organization_id=organization_id
        )
        
        # Expected: 1500 (bank) - 1000 (GL) = 500
        assert unreconciled == Decimal("500.00")

    def test_returns_negative_when_gl_balance_higher(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID,
        gl_account_id: UUID
    ):
        """Test that unreconciled amount is negative when GL balance is higher"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create bank transactions (bank balance = 800)
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("800.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        db_session.add(bank_transaction)
        
        # Create journal entry (GL balance = 1200)
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("1200.00"),
            total_credit=Decimal("1200.00")
        )
        db_session.add(journal_entry)
        db_session.flush()
        
        journal_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry.id,
            account_id=gl_account_id,
            debit=Decimal("1200.00"),
            credit=Decimal("0.00")
        )
        db_session.add(journal_line)
        db_session.commit()
        
        # Calculate unreconciled amount
        unreconciled = reconciliation_engine.calculate_unreconciled_amount(
            bank_account_id=bank_account_id,
            gl_account_id=gl_account_id,
            organization_id=organization_id
        )
        
        # Expected: 800 (bank) - 1200 (GL) = -400
        assert unreconciled == Decimal("-400.00")

    def test_returns_zero_when_balances_match(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID,
        gl_account_id: UUID
    ):
        """Test that unreconciled amount is zero when balances match"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create bank transactions (bank balance = 1000)
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        db_session.add(bank_transaction)
        
        # Create journal entry (GL balance = 1000)
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("1000.00"),
            total_credit=Decimal("1000.00")
        )
        db_session.add(journal_entry)
        db_session.flush()
        
        journal_line = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry.id,
            account_id=gl_account_id,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00")
        )
        db_session.add(journal_line)
        db_session.commit()
        
        # Calculate unreconciled amount
        unreconciled = reconciliation_engine.calculate_unreconciled_amount(
            bank_account_id=bank_account_id,
            gl_account_id=gl_account_id,
            organization_id=organization_id
        )
        
        # Expected: 1000 (bank) - 1000 (GL) = 0
        assert unreconciled == Decimal("0.00")

    def test_respects_as_of_date_parameter(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id: UUID,
        bank_account_id: UUID,
        gl_account_id: UUID
    ):
        """Test that unreconciled amount calculation respects as_of_date"""
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        
        # Create bank transactions on different dates
        bank_transaction_1 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-001"
        )
        bank_transaction_2 = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 20),
            transaction_amount=Decimal("500.00"),
            transaction_type="credit",
            transaction_status="cleared",
            bank_reference="TXN-002"
        )
        db_session.add_all([bank_transaction_1, bank_transaction_2])
        
        # Create journal entries on different dates
        journal_entry_1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=date(2024, 1, 15),
            status="posted",
            total_debit=Decimal("800.00"),
            total_credit=Decimal("800.00")
        )
        db_session.add(journal_entry_1)
        db_session.flush()
        
        journal_line_1 = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry_1.id,
            account_id=gl_account_id,
            debit=Decimal("800.00"),
            credit=Decimal("0.00")
        )
        db_session.add(journal_line_1)
        
        journal_entry_2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",
            posting_date=date(2024, 1, 20),
            status="posted",
            total_debit=Decimal("400.00"),
            total_credit=Decimal("400.00")
        )
        db_session.add(journal_entry_2)
        db_session.flush()
        
        journal_line_2 = JournalEntryLine(
            organization_id=organization_id,
            journal_entry_id=journal_entry_2.id,
            account_id=gl_account_id,
            debit=Decimal("400.00"),
            credit=Decimal("0.00")
        )
        db_session.add(journal_line_2)
        db_session.commit()
        
        # Calculate unreconciled amount as of Jan 17
        # Bank: 1000, GL: 800, Difference: 200
        unreconciled = reconciliation_engine.calculate_unreconciled_amount(
            bank_account_id=bank_account_id,
            gl_account_id=gl_account_id,
            organization_id=organization_id,
            as_of_date=date(2024, 1, 17)
        )
        
        # Expected: 1000 (bank) - 800 (GL) = 200
        assert unreconciled == Decimal("200.00")



class TestConfirmSuggestedMatch:
    """Tests for confirm_suggested_match method"""

    def test_confirms_suggested_match_successfully(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that a suggested match can be confirmed successfully"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a suggested reconciliation (simulating auto-fuzzy match)
        suggested_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.85"),
            is_active=True
        )
        
        db_session.add(suggested_reconciliation)
        db_session.commit()
        
        # Confirm the suggested match
        confirmed = reconciliation_engine.confirm_suggested_match(
            reconciliation_id=suggested_reconciliation.id,
            confirmed_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation status changed to confirmed
        assert confirmed.reconciliation_status == "confirmed"
        assert confirmed.reconciled_by == "test_user"
        assert confirmed.reconciled_at is not None
        
        # Verify bank transaction status changed to reconciled
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "reconciled"
        assert bank_transaction.reconciled_at is not None

    def test_raises_error_when_reconciliation_not_found(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id
    ):
        """Test that confirming a non-existent reconciliation raises an error"""
        non_existent_id = uuid4()
        
        with pytest.raises(ValueError, match=f"Reconciliation {non_existent_id} not found"):
            reconciliation_engine.confirm_suggested_match(
                reconciliation_id=non_existent_id,
                confirmed_by="test_user",
                organization_id=organization_id
            )

    def test_raises_error_when_reconciliation_not_suggested(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that confirming a non-suggested reconciliation raises an error"""
        # Create a bank transaction and journal entry
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC)
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a confirmed reconciliation
        confirmed_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="manual",
            reconciliation_status="confirmed",
            match_confidence=Decimal("1.0"),
            reconciled_by="original_user",
            reconciled_at=datetime.now(UTC),
            is_active=True
        )
        
        db_session.add(confirmed_reconciliation)
        db_session.commit()
        
        # Try to confirm an already confirmed reconciliation
        with pytest.raises(ValueError, match="Only suggested matches can be confirmed"):
            reconciliation_engine.confirm_suggested_match(
                reconciliation_id=confirmed_reconciliation.id,
                confirmed_by="test_user",
                organization_id=organization_id
            )

    def test_raises_error_when_reconciliation_not_active(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that confirming an inactive reconciliation raises an error"""
        # Create a bank transaction and journal entry
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create an inactive suggested reconciliation
        inactive_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.85"),
            is_active=False
        )
        
        db_session.add(inactive_reconciliation)
        db_session.commit()
        
        # Try to confirm an inactive reconciliation
        with pytest.raises(ValueError, match="Cannot confirm an inactive reconciliation"):
            reconciliation_engine.confirm_suggested_match(
                reconciliation_id=inactive_reconciliation.id,
                confirmed_by="test_user",
                organization_id=organization_id
            )


class TestRejectSuggestedMatch:
    """Tests for reject_suggested_match method"""

    def test_rejects_suggested_match_successfully(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that a suggested match can be rejected successfully"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a suggested reconciliation (simulating auto-fuzzy match)
        suggested_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.85"),
            is_active=True
        )
        
        db_session.add(suggested_reconciliation)
        db_session.commit()
        
        # Reject the suggested match
        rejected = reconciliation_engine.reject_suggested_match(
            reconciliation_id=suggested_reconciliation.id,
            rejected_by="test_user",
            organization_id=organization_id,
            reason="Incorrect match"
        )
        
        # Verify reconciliation status changed to rejected
        assert rejected.reconciliation_status == "rejected"
        assert rejected.reconciled_by == "test_user"
        assert rejected.reconciled_at is not None
        assert "Rejection reason: Incorrect match" in rejected.notes
        
        # Verify bank transaction status remains cleared (not reconciled)
        db_session.refresh(bank_transaction)
        assert bank_transaction.transaction_status == "cleared"
        assert bank_transaction.reconciled_at is None

    def test_rejects_without_reason(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that a suggested match can be rejected without providing a reason"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a suggested reconciliation
        suggested_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.85"),
            is_active=True
        )
        
        db_session.add(suggested_reconciliation)
        db_session.commit()
        
        # Reject without reason
        rejected = reconciliation_engine.reject_suggested_match(
            reconciliation_id=suggested_reconciliation.id,
            rejected_by="test_user",
            organization_id=organization_id
        )
        
        # Verify reconciliation status changed to rejected
        assert rejected.reconciliation_status == "rejected"
        assert rejected.reconciled_by == "test_user"

    def test_appends_rejection_reason_to_existing_notes(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that rejection reason is appended to existing notes"""
        # Create a cleared bank transaction
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a suggested reconciliation with existing notes
        suggested_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.85"),
            notes="Auto-matched based on amount and date",
            is_active=True
        )
        
        db_session.add(suggested_reconciliation)
        db_session.commit()
        
        # Reject with reason
        rejected = reconciliation_engine.reject_suggested_match(
            reconciliation_id=suggested_reconciliation.id,
            rejected_by="test_user",
            organization_id=organization_id,
            reason="Wrong vendor"
        )
        
        # Verify rejection reason was appended to existing notes
        assert "Auto-matched based on amount and date" in rejected.notes
        assert "Rejection reason: Wrong vendor" in rejected.notes

    def test_raises_error_when_reconciliation_not_found(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id
    ):
        """Test that rejecting a non-existent reconciliation raises an error"""
        non_existent_id = uuid4()
        
        with pytest.raises(ValueError, match=f"Reconciliation {non_existent_id} not found"):
            reconciliation_engine.reject_suggested_match(
                reconciliation_id=non_existent_id,
                rejected_by="test_user",
                organization_id=organization_id
            )

    def test_raises_error_when_reconciliation_not_suggested(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that rejecting a non-suggested reconciliation raises an error"""
        # Create a bank transaction and journal entry
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="reconciled",
            transaction_type="credit",
            reconciled_at=datetime.now(UTC)
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create a confirmed reconciliation
        confirmed_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="manual",
            reconciliation_status="confirmed",
            match_confidence=Decimal("1.0"),
            reconciled_by="original_user",
            reconciled_at=datetime.now(UTC),
            is_active=True
        )
        
        db_session.add(confirmed_reconciliation)
        db_session.commit()
        
        # Try to reject an already confirmed reconciliation
        with pytest.raises(ValueError, match="Only suggested matches can be rejected"):
            reconciliation_engine.reject_suggested_match(
                reconciliation_id=confirmed_reconciliation.id,
                rejected_by="test_user",
                organization_id=organization_id
            )

    def test_raises_error_when_reconciliation_not_active(
        self,
        reconciliation_engine: ReconciliationEngine,
        db_session: Session,
        organization_id,
        bank_account_id
    ):
        """Test that rejecting an inactive reconciliation raises an error"""
        # Create a bank transaction and journal entry
        bank_transaction = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account_id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("100.00"),
            transaction_description="Test transaction",
            bank_reference="REF001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE001",
            posting_date=datetime(2024, 1, 15, tzinfo=UTC),
            status=JournalStatus.POSTED,
            total_debit=Decimal("100.00"),
            total_credit=Decimal("100.00")
        )
        
        db_session.add_all([bank_transaction, journal_entry])
        db_session.commit()
        
        # Create an inactive suggested reconciliation
        inactive_reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=Decimal("0.85"),
            is_active=False
        )
        
        db_session.add(inactive_reconciliation)
        db_session.commit()
        
        # Try to reject an inactive reconciliation
        with pytest.raises(ValueError, match="Cannot reject an inactive reconciliation"):
            reconciliation_engine.reject_suggested_match(
                reconciliation_id=inactive_reconciliation.id,
                rejected_by="test_user",
                organization_id=organization_id
            )
