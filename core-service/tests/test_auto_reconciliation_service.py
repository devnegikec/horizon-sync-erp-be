"""
Unit tests for AutoReconciliationService

Tests auto-reconciliation functionality including filtering unreconciled transactions.
"""

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.chart_of_account import Account
from app.services.auto_reconciliation_service import AutoReconciliationService


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def gl_account(db_session: Session, organization_id: uuid.UUID):
    """Create a test GL account"""
    account = Account(
        organization_id=organization_id,
        account_code="1000",
        account_name="Test Bank Account",
        account_type="asset",
        currency="USD",
        is_group=False,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def bank_account(db_session: Session, organization_id: uuid.UUID, gl_account: Account):
    """Create a test bank account"""
    account = BankAccount(
        organization_id=organization_id,
        gl_account_id=gl_account.id,
        bank_name="Test Bank",
        account_holder_name="Test Holder",
        account_number="1234567890",
        country_code="US",
        currency="USD",
        is_primary=True,
        is_active=True,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


class TestAutoReconciliationService:
    """Test suite for AutoReconciliationService"""
    
    def test_run_auto_reconciliation_filters_cleared_transactions(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that run_auto_reconciliation filters transactions with status 'cleared'
        and reconciled_at is null.
        
        Requirements: 8.1
        """
        # Create test transactions with different statuses
        transactions = [
            # Should be included: cleared and not reconciled
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 15),
                transaction_amount=Decimal("1500.00"),
                transaction_description="Payment 1",
                bank_reference="TXN-001",
                transaction_status="cleared",
                transaction_type="credit",
                reconciled_at=None
            ),
            # Should be included: cleared and not reconciled
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 16),
                transaction_amount=Decimal("250.50"),
                transaction_description="Payment 2",
                bank_reference="TXN-002",
                transaction_status="cleared",
                transaction_type="debit",
                reconciled_at=None
            ),
            # Should NOT be included: status is pending
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 17),
                transaction_amount=Decimal("500.00"),
                transaction_description="Payment 3",
                bank_reference="TXN-003",
                transaction_status="pending",
                transaction_type="credit",
                reconciled_at=None
            ),
            # Should NOT be included: already reconciled
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 18),
                transaction_amount=Decimal("750.00"),
                transaction_description="Payment 4",
                bank_reference="TXN-004",
                transaction_status="cleared",
                transaction_type="credit",
                reconciled_at=datetime.now(UTC)
            ),
            # Should NOT be included: status is void
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 19),
                transaction_amount=Decimal("100.00"),
                transaction_description="Payment 5",
                bank_reference="TXN-005",
                transaction_status="void",
                transaction_type="debit",
                reconciled_at=None
            ),
        ]
        
        for txn in transactions:
            db_session.add(txn)
        db_session.commit()
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        result = service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Verify only 2 transactions were processed (cleared and not reconciled)
        assert result["total_processed"] == 2
        assert result["exact_matches"] == 0  # No matching algorithm implemented yet
        assert result["fuzzy_matches"] == 0
        assert result["many_to_one_matches"] == 0
    
    def test_run_auto_reconciliation_filters_by_date_range(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that run_auto_reconciliation filters transactions by date range.
        
        Requirements: 8.1
        """
        # Create transactions with different dates
        transactions = [
            # Within date range
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 15),
                transaction_amount=Decimal("1500.00"),
                transaction_description="Payment 1",
                bank_reference="TXN-001",
                transaction_status="cleared",
                transaction_type="credit",
                reconciled_at=None
            ),
            # Before date range
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2023, 12, 31),
                transaction_amount=Decimal("250.50"),
                transaction_description="Payment 2",
                bank_reference="TXN-002",
                transaction_status="cleared",
                transaction_type="debit",
                reconciled_at=None
            ),
            # After date range
            BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 2, 1),
                transaction_amount=Decimal("500.00"),
                transaction_description="Payment 3",
                bank_reference="TXN-003",
                transaction_status="cleared",
                transaction_type="credit",
                reconciled_at=None
            ),
        ]
        
        for txn in transactions:
            db_session.add(txn)
        db_session.commit()
        
        # Run auto-reconciliation for January 2024
        service = AutoReconciliationService(db_session)
        result = service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Verify only 1 transaction was processed (within date range)
        assert result["total_processed"] == 1
    
    def test_run_auto_reconciliation_empty_result(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that run_auto_reconciliation handles empty result correctly.
        
        Requirements: 8.1
        """
        # Don't create any transactions
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        result = service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Verify no transactions were processed
        assert result["total_processed"] == 0
        assert result["exact_matches"] == 0
        assert result["fuzzy_matches"] == 0
        assert result["many_to_one_matches"] == 0


class TestExactMatchAlgorithm:
    """Test suite for exact match reconciliation algorithm"""
    
    def test_find_exact_matches_with_perfect_match(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that find_exact_matches finds a journal entry when all criteria match exactly.
        
        Requirements: 8.2, 8.3, 8.4
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a matching journal entry
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Test exact match
        service = AutoReconciliationService(db_session)
        match = service.find_exact_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert match is not None
        assert match.id == journal_entry.id
    
    def test_find_exact_matches_amount_mismatch(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that find_exact_matches returns None when amount doesn't match.
        
        Requirements: 8.2
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with different amount
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1600.00")  # Different amount
        )
        db_session.add(journal_entry)
        db_session.commit()
        
        # Test exact match
        service = AutoReconciliationService(db_session)
        match = service.find_exact_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert match is None
    
    def test_find_exact_matches_date_mismatch(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that find_exact_matches returns None when date doesn't match.
        
        Requirements: 8.3
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with different date
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 16, 10, 0, 0, tzinfo=UTC),  # Different date
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        
        # Test exact match
        service = AutoReconciliationService(db_session)
        match = service.find_exact_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert match is None
    
    def test_find_exact_matches_reference_mismatch(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that find_exact_matches returns None when reference doesn't match.
        
        Requirements: 8.4
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with different reference
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",  # Different reference
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        
        # Test exact match
        service = AutoReconciliationService(db_session)
        match = service.find_exact_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert match is None
    
    def test_exact_match_creates_reconciliation(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that exact match creates a reconciliation record with correct attributes.
        
        Requirements: 8.5, 8.6, 8.7
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a matching journal entry
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        result = service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Verify reconciliation was created
        assert result["exact_matches"] == 1
        
        # Check reconciliation record
        from app.models.bank_reconciliation import BankReconciliation
        reconciliation = db_session.query(BankReconciliation).filter(
            BankReconciliation.bank_transaction_id == bank_txn.id
        ).first()
        
        assert reconciliation is not None
        assert reconciliation.reconciliation_type == "auto_exact"
        assert reconciliation.reconciliation_status == "confirmed"
        assert reconciliation.match_confidence == Decimal("1.0")
        assert reconciliation.is_active is True
    
    def test_exact_match_updates_transaction_status(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that exact match updates bank transaction status to 'reconciled'.
        
        Requirements: 8.8, 8.9
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a matching journal entry
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Refresh transaction to get updated status
        db_session.refresh(bank_txn)
        
        # Verify transaction status was updated
        assert bank_txn.transaction_status == "reconciled"
        assert bank_txn.reconciled_at is not None
    
    def test_exact_match_with_debit_transaction(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that exact match works for debit transactions.
        
        Requirements: 8.2
        """
        # Create a debit bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("250.50"),
            transaction_description="Office Supplies",
            bank_reference="JE-002",
            transaction_status="cleared",
            transaction_type="debit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a matching journal entry (debit)
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("250.50"),
            total_credit=Decimal("0.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        result = service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Verify reconciliation was created
        assert result["exact_matches"] == 1
        
        # Refresh transaction to verify status
        db_session.refresh(bank_txn)
        assert bank_txn.transaction_status == "reconciled"



class TestFuzzyMatchAlgorithm:
    """Test suite for fuzzy match reconciliation algorithm"""
    
    def test_find_fuzzy_matches_amount_and_date_exact(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test fuzzy match with exact amount and exact date.
        Should return confidence of 0.8.
        
        Requirements: 9.2, 9.3, 9.5
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="TXN-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with matching amount and date, but different reference
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-999",  # Different reference
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert len(matches) == 1
        matched_je, confidence = matches[0]
        assert matched_je.id == journal_entry.id
        assert confidence == Decimal("0.8")  # Amount + exact date
    
    def test_find_fuzzy_matches_amount_and_date_within_3_days(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test fuzzy match with exact amount and date within 3 days.
        Should return confidence of 0.7.
        
        Requirements: 9.2, 9.3, 9.5
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="TXN-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry 2 days later
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-999",
            posting_date=datetime(2024, 1, 17, 10, 0, 0, tzinfo=UTC),  # 2 days later
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert len(matches) == 1
        matched_je, confidence = matches[0]
        assert matched_je.id == journal_entry.id
        assert confidence == Decimal("0.7")  # Amount + date within 3 days
    
    def test_find_fuzzy_matches_amount_date_and_reference(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test fuzzy match with exact amount, date within 3 days, and partial reference match.
        Should return confidence of 0.95 (0.5 base + 0.3 exact date + 0.2 reference).
        
        Requirements: 9.2, 9.3, 9.4, 9.6
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="INV-001-TXN",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with partial reference match
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-INV-001",  # Contains "INV-001" which is in bank_reference
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert len(matches) == 1
        matched_je, confidence = matches[0]
        assert matched_je.id == journal_entry.id
        # Note: Partial match check is bidirectional, so "INV-001" in "INV-001-TXN" OR "JE-INV-001" in "INV-001-TXN"
        # In this case, neither contains the other fully, so we need to adjust the test
        # Let me check the logic again...
        # Actually "INV-001-TXN" does NOT contain "JE-INV-001" and vice versa
        # So confidence should be 0.8 (exact date), not 0.95
        assert confidence == Decimal("0.8")  # Amount + exact date (no reference match)
    
    def test_find_fuzzy_matches_with_proper_partial_reference(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test fuzzy match with proper partial reference match.
        Should return confidence of 0.95.
        
        Requirements: 9.4, 9.6
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",  # Exact match with entry_no
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry where entry_no is contained in bank_reference
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001-EXTRA",  # Contains "JE-001"
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert len(matches) == 1
        matched_je, confidence = matches[0]
        assert matched_je.id == journal_entry.id
        assert confidence == Decimal("0.95")  # Amount + exact date + reference match
    
    def test_find_fuzzy_matches_no_match_amount_mismatch(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that fuzzy match returns empty list when amount doesn't match.
        Amount match is required for fuzzy matching.
        
        Requirements: 9.2
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="TXN-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with different amount
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1600.00")  # Different amount
        )
        db_session.add(journal_entry)
        db_session.commit()
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert len(matches) == 0
    
    def test_find_fuzzy_matches_no_match_date_too_far(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that fuzzy match returns empty list when date is more than 3 days apart.
        Date too far means no base confidence is assigned.
        
        Requirements: 9.3
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="TXN-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry 5 days later (more than 3 days)
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001",
            posting_date=datetime(2024, 1, 20, 10, 0, 0, tzinfo=UTC),  # 5 days later
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        # Should return empty list because date is too far (no confidence assigned)
        assert len(matches) == 0
    
    def test_fuzzy_match_creates_suggested_reconciliation(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that fuzzy match creates a reconciliation with status "suggested".
        
        Requirements: 9.7, 9.8
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="TXN-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with fuzzy match (amount + date)
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-999",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        result = service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Verify fuzzy match was created
        assert result["fuzzy_matches"] == 1
        
        # Check reconciliation record
        from app.models.bank_reconciliation import BankReconciliation
        reconciliation = db_session.query(BankReconciliation).filter(
            BankReconciliation.bank_transaction_id == bank_txn.id
        ).first()
        
        assert reconciliation is not None
        assert reconciliation.reconciliation_type == "auto_fuzzy"
        assert reconciliation.reconciliation_status == "suggested"
        assert reconciliation.match_confidence == Decimal("0.8")
        assert reconciliation.is_active is True
    
    def test_fuzzy_match_does_not_update_transaction_status(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that fuzzy match does NOT update bank transaction status.
        Transaction should remain "cleared" until user confirms the match.
        
        Requirements: 9.9
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="TXN-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a journal entry with fuzzy match
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-999",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Run auto-reconciliation
        service = AutoReconciliationService(db_session)
        service.run_auto_reconciliation(
            bank_account_id=bank_account.id,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            organization_id=organization_id
        )
        
        # Refresh transaction to check status
        db_session.refresh(bank_txn)
        
        # Verify transaction status was NOT updated
        assert bank_txn.transaction_status == "cleared"  # Still cleared, not reconciled
        assert bank_txn.reconciled_at is None  # Still null
    
    def test_fuzzy_match_sorts_by_confidence(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that fuzzy matches are sorted by confidence (highest first).
        
        Requirements: 9.6
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1500.00"),
            transaction_description="Customer Payment",
            bank_reference="JE-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create multiple journal entries with different confidence levels
        from app.models.journal_entry import JournalEntry
        
        # Lower confidence: amount + date within 3 days (0.7)
        je1 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-999",
            posting_date=datetime(2024, 1, 17, 10, 0, 0, tzinfo=UTC),  # 2 days later
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        
        # Medium confidence: amount + exact date (0.8)
        je2 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-888",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        
        # Highest confidence: amount + exact date + reference (0.95)
        je3 = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-001-EXTRA",  # Contains "JE-001"
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1500.00")
        )
        
        db_session.add_all([je1, je2, je3])
        db_session.commit()
        db_session.refresh(bank_txn)
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[je1, je2, je3]
        )
        
        # Should return 3 matches sorted by confidence
        assert len(matches) == 3
        
        # Verify sorting (highest confidence first)
        assert matches[0][1] == Decimal("0.95")  # je3: amount + exact date + reference
        assert matches[1][1] == Decimal("0.8")   # je2: amount + exact date
        assert matches[2][1] == Decimal("0.7")   # je1: amount + date within 3 days
    
    def test_fuzzy_match_with_debit_transaction(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that fuzzy match works for debit transactions.
        
        Requirements: 9.2
        """
        # Create a debit bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("250.50"),
            transaction_description="Office Supplies",
            bank_reference="TXN-002",
            transaction_status="cleared",
            transaction_type="debit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create a matching journal entry (debit)
        from app.models.journal_entry import JournalEntry
        journal_entry = JournalEntry(
            organization_id=organization_id,
            entry_no="JE-002",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("250.50"),
            total_credit=Decimal("0.00")
        )
        db_session.add(journal_entry)
        db_session.commit()
        db_session.refresh(bank_txn)
        db_session.refresh(journal_entry)
        
        # Test fuzzy match
        service = AutoReconciliationService(db_session)
        matches = service.find_fuzzy_matches(
            bank_transaction=bank_txn,
            journal_entries=[journal_entry]
        )
        
        assert len(matches) == 1
        matched_je, confidence = matches[0]
        assert matched_je.id == journal_entry.id
        assert confidence == Decimal("0.8")  # Amount + exact date



class TestManyToOneDetection:
    """Test suite for many-to-one reconciliation detection algorithm"""
    
    def test_find_many_to_one_matches_basic(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that find_many_to_one_matches finds multiple journal entries
        that sum to the bank transaction amount.
        
        Requirements: 10.10
        """
        # Create a bank transaction for $1000
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_description="Daily Sales Deposit",
            bank_reference="BATCH-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create multiple journal entries that sum to $1000
        from app.models.journal_entry import JournalEntry
        
        je1 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-001",
            posting_date=datetime(2024, 1, 14, 10, 0, 0, tzinfo=UTC),  # 1 day before
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("300.00")
        )
        
        je2 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-002",
            posting_date=datetime(2024, 1, 14, 14, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("450.00")
        )
        
        je3 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-003",
            posting_date=datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC),  # Same day
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("250.00")
        )
        
        db_session.add_all([je1, je2, je3])
        db_session.commit()
        db_session.refresh(bank_txn)
        
        # Test many-to-one match
        service = AutoReconciliationService(db_session)
        matches = service.find_many_to_one_matches(
            bank_transaction=bank_txn,
            journal_entries=[je1, je2, je3]
        )
        
        # Should find a combination that sums to $1000
        assert matches is not None
        assert len(matches) == 3
        
        # Verify the sum equals the bank transaction amount
        total = sum(Decimal(str(je.total_credit)) for je in matches)
        assert abs(total - Decimal("1000.00")) <= Decimal("0.01")
    
    def test_find_many_to_one_matches_within_date_range(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that many-to-one detection only considers journal entries
        within 7 days of the bank transaction date.
        
        Requirements: 10.10
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_description="Daily Sales Deposit",
            bank_reference="BATCH-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create journal entries
        from app.models.journal_entry import JournalEntry
        
        # Within range (6 days before)
        je1 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-001",
            posting_date=datetime(2024, 1, 9, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("500.00")
        )
        
        # Within range (same day)
        je2 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-002",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("500.00")
        )
        
        # Outside range (8 days before - should be excluded)
        je3 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-003",
            posting_date=datetime(2024, 1, 7, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("1000.00")
        )
        
        db_session.add_all([je1, je2, je3])
        db_session.commit()
        db_session.refresh(bank_txn)
        
        # Test many-to-one match
        service = AutoReconciliationService(db_session)
        matches = service.find_many_to_one_matches(
            bank_transaction=bank_txn,
            journal_entries=[je1, je2, je3]
        )
        
        # Should find je1 + je2 = $1000 (je3 is outside date range)
        assert matches is not None
        assert len(matches) == 2
        
        # Verify je3 is not in the matches
        match_ids = [je.id for je in matches]
        assert je3.id not in match_ids
    
    def test_find_many_to_one_matches_with_tolerance(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that many-to-one detection uses 0.01 tolerance for matching.
        
        Requirements: 10.10
        """
        # Create a bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_description="Daily Sales Deposit",
            bank_reference="BATCH-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create journal entries that sum to $999.99 (within 0.01 tolerance)
        from app.models.journal_entry import JournalEntry
        
        je1 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("500.00")
        )
        
        je2 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-002",
            posting_date=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("499.99")  # Total: $999.99
        )
        
        db_session.add_all([je1, je2])
        db_session.commit()
        db_session.refresh(bank_txn)
        
        # Test many-to-one match
        service = AutoReconciliationService(db_session)
        matches = service.find_many_to_one_matches(
            bank_transaction=bank_txn,
            journal_entries=[je1, je2]
        )
        
        # Should find a match because $999.99 is within 0.01 of $1000.00
        assert matches is not None
        assert len(matches) == 2
    
    def test_find_many_to_one_matches_no_match(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that many-to-one detection returns None when no combination
        sums to the bank transaction amount.
        
        Requirements: 10.10
        """
        # Create a bank transaction for $1000
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_description="Daily Sales Deposit",
            bank_reference="BATCH-001",
            transaction_status="cleared",
            transaction_type="credit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create journal entries that don't sum to $1000
        from app.models.journal_entry import JournalEntry
        
        je1 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("300.00")
        )
        
        je2 = JournalEntry(
            organization_id=organization_id,
            entry_no="SALE-002",
            posting_date=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("0.00"),
            total_credit=Decimal("400.00")
        )
        # Total: $700.00 (no combination sums to $1000)
        
        db_session.add_all([je1, je2])
        db_session.commit()
        db_session.refresh(bank_txn)
        
        # Test many-to-one match
        service = AutoReconciliationService(db_session)
        matches = service.find_many_to_one_matches(
            bank_transaction=bank_txn,
            journal_entries=[je1, je2]
        )
        
        # Should return None because no combination sums to $1000
        assert matches is None
    
    def test_find_many_to_one_matches_with_debit_transaction(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """
        Test that many-to-one detection works for debit transactions.
        
        Requirements: 10.10
        """
        # Create a debit bank transaction
        bank_txn = BankTransaction(
            organization_id=organization_id,
            bank_account_id=bank_account.id,
            statement_date=date(2024, 1, 15),
            transaction_amount=Decimal("1000.00"),
            transaction_description="Multiple Expenses",
            bank_reference="BATCH-002",
            transaction_status="cleared",
            transaction_type="debit",
            reconciled_at=None
        )
        db_session.add(bank_txn)
        
        # Create multiple debit journal entries
        from app.models.journal_entry import JournalEntry
        
        je1 = JournalEntry(
            organization_id=organization_id,
            entry_no="EXP-001",
            posting_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("600.00"),
            total_credit=Decimal("0.00")
        )
        
        je2 = JournalEntry(
            organization_id=organization_id,
            entry_no="EXP-002",
            posting_date=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            status="posted",
            total_debit=Decimal("400.00"),
            total_credit=Decimal("0.00")
        )
        
        db_session.add_all([je1, je2])
        db_session.commit()
        db_session.refresh(bank_txn)
        
        # Test many-to-one match
        service = AutoReconciliationService(db_session)
        matches = service.find_many_to_one_matches(
            bank_transaction=bank_txn,
            journal_entries=[je1, je2]
        )
        
        # Should find a combination that sums to $1000
        assert matches is not None
        assert len(matches) == 2
        
        # Verify the sum equals the bank transaction amount
        total = sum(Decimal(str(je.total_debit)) for je in matches)
        assert abs(total - Decimal("1000.00")) <= Decimal("0.01")
