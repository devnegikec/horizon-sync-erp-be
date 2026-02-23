"""Unit tests for JournalPostingService"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import Mock, MagicMock

import pytest

from app.core.exceptions import ValidationError
from app.models.base import PaymentEntryType, PaymentMode
from app.services.journal_posting_service import JournalPostingService


class TestJournalPostingService:
    """Test suite for JournalPostingService"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def mock_journal_entry_service(self):
        """Create a mock journal entry service"""
        service = Mock()
        service.create = Mock(return_value={
            "id": uuid.uuid4(),
            "entry_no": "JE-2024-001",
            "status": "Posted",
            "total_debit": Decimal("1000.00"),
            "total_credit": Decimal("1000.00"),
        })
        return service

    @pytest.fixture
    def mock_default_account_service(self):
        """Create a mock default account service"""
        service = Mock()
        
        def get_default_account(transaction_type, organization_id):
            account = Mock()
            if transaction_type == "cash":
                account.account_id = uuid.uuid4()
            elif transaction_type == "bank":
                account.account_id = uuid.uuid4()
            elif transaction_type == "checks_received":
                account.account_id = uuid.uuid4()
            elif transaction_type == "accounts_receivable":
                account.account_id = uuid.uuid4()
            else:
                raise ValidationError(f"Account not configured for {transaction_type}")
            return account
        
        service.get_default_account = Mock(side_effect=get_default_account)
        return service

    @pytest.fixture
    def mock_currency_service(self):
        """Create a mock currency service"""
        service = Mock()
        service.get_base_currency = Mock(return_value="USD")
        service.convert = Mock(side_effect=lambda amount, from_currency, to_currency: amount)
        return service

    @pytest.fixture
    def journal_posting_service(
        self,
        mock_db_session,
        mock_journal_entry_service,
        mock_default_account_service,
        mock_currency_service,
    ):
        """Create a JournalPostingService instance with mocked dependencies"""
        service = JournalPostingService(mock_db_session)
        service.journal_entry_service = mock_journal_entry_service
        service.default_account_service = mock_default_account_service
        service.currency_service = mock_currency_service
        return service

    @pytest.fixture
    def sample_payment_entry(self):
        """Create a sample payment entry for testing"""
        payment = Mock()
        payment.id = uuid.uuid4()
        payment.payment_type = PaymentEntryType.CUSTOMER_PAYMENT
        payment.payment_mode = PaymentMode.CASH
        payment.amount = Decimal("1000.00")
        payment.currency_code = "USD"
        payment.payment_date = datetime.now(UTC)
        return payment

    def test_post_payment_journal_entry_cash(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test posting journal entry for cash payment"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Execute
        result = journal_posting_service.post_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Verify
        assert result is not None
        assert result["status"] == "Posted"
        assert result["total_debit"] == Decimal("1000.00")
        assert result["total_credit"] == Decimal("1000.00")

        # Verify journal entry service was called
        journal_posting_service.journal_entry_service.create.assert_called_once()
        call_args = journal_posting_service.journal_entry_service.create.call_args
        
        # Verify journal entry data structure
        journal_data = call_args[1]["data"]
        assert journal_data["reference_type"] == "PaymentEntry"
        assert journal_data["reference_id"] == sample_payment_entry.id
        assert journal_data["voucher_type"] == "Payment Entry"
        assert journal_data["status"] == "Posted"
        assert len(journal_data["lines"]) == 2

        # Verify debit line (Cash account)
        debit_line = journal_data["lines"][0]
        assert debit_line["debit"] == Decimal("1000.00")
        assert debit_line["credit"] == Decimal("0.00")
        assert debit_line["reference_type"] == "PaymentEntry"

        # Verify credit line (Accounts Receivable)
        credit_line = journal_data["lines"][1]
        assert credit_line["debit"] == Decimal("0.00")
        assert credit_line["credit"] == Decimal("1000.00")
        assert credit_line["reference_type"] == "PaymentEntry"

    def test_post_payment_journal_entry_bank_transfer(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test posting journal entry for bank transfer payment"""
        sample_payment_entry.payment_mode = PaymentMode.BANK_TRANSFER
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Execute
        result = journal_posting_service.post_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Verify
        assert result is not None
        assert result["status"] == "Posted"

        # Verify default account service was called for bank account
        calls = journal_posting_service.default_account_service.get_default_account.call_args_list
        transaction_types = [call[1]["transaction_type"] for call in calls]
        assert "bank" in transaction_types
        assert "accounts_receivable" in transaction_types

    def test_post_payment_journal_entry_check(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test posting journal entry for check payment"""
        sample_payment_entry.payment_mode = PaymentMode.CHECK
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Execute
        result = journal_posting_service.post_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Verify
        assert result is not None
        assert result["status"] == "Posted"

        # Verify default account service was called for checks_received account
        calls = journal_posting_service.default_account_service.get_default_account.call_args_list
        transaction_types = [call[1]["transaction_type"] for call in calls]
        assert "checks_received" in transaction_types
        assert "accounts_receivable" in transaction_types

    def test_post_payment_journal_entry_validates_accounts(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test that posting validates required accounts are configured"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock missing account
        journal_posting_service.default_account_service.get_default_account = Mock(
            side_effect=ValidationError("Account not configured")
        )

        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            journal_posting_service.post_payment_journal_entry(
                payment_entry=sample_payment_entry,
                organization_id=organization_id,
                user_id=user_id,
            )

        assert "not configured" in str(exc_info.value).lower()

    def test_post_payment_journal_entry_currency_conversion(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test that posting converts currency to base currency"""
        sample_payment_entry.currency_code = "EUR"
        sample_payment_entry.amount = Decimal("1000.00")
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock currency conversion
        journal_posting_service.currency_service.get_base_currency = Mock(return_value="USD")
        journal_posting_service.currency_service.convert = Mock(return_value=Decimal("1100.00"))

        # Execute
        result = journal_posting_service.post_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Verify currency conversion was called
        journal_posting_service.currency_service.convert.assert_called_once()
        call_args = journal_posting_service.currency_service.convert.call_args
        assert call_args[1]["from_currency"] == "EUR"
        assert call_args[1]["to_currency"] == "USD"

    def test_reverse_payment_journal_entry(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test reversing journal entry for cancelled payment"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock original journal entry
        original_je = Mock()
        original_je.id = uuid.uuid4()
        original_je.lines = [
            Mock(
                account_id=uuid.uuid4(),
                debit=Decimal("1000.00"),
                credit=Decimal("0.00"),
                against_account_id=uuid.uuid4(),
                remarks="Payment received - Cash",
            ),
            Mock(
                account_id=uuid.uuid4(),
                debit=Decimal("0.00"),
                credit=Decimal("1000.00"),
                against_account_id=uuid.uuid4(),
                remarks="Accounts Receivable",
            ),
        ]
        
        # Mock get_by_reference to return original entry
        journal_posting_service.journal_entry_service.get_by_reference = Mock(
            return_value={
                "id": original_je.id,
                "total_debit": Decimal("1000.00"),
                "total_credit": Decimal("1000.00"),
            }
        )
        journal_posting_service.journal_entry_service.repo.get_by_reference = Mock(
            return_value=original_je
        )
        
        # Set cancellation reason
        sample_payment_entry.cancellation_reason = "Duplicate payment"
        
        # Execute
        result = journal_posting_service.reverse_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify
        assert result is not None
        assert result["status"] == "Posted"
        
        # Verify journal entry service was called
        journal_posting_service.journal_entry_service.create.assert_called()
        call_args = journal_posting_service.journal_entry_service.create.call_args
        
        # Verify reversing journal entry data structure
        journal_data = call_args[1]["data"]
        assert journal_data["reference_type"] == "PaymentEntry"
        assert journal_data["reference_id"] == sample_payment_entry.id
        assert journal_data["voucher_type"] == "Payment Entry Reversal"
        assert journal_data["status"] == "Posted"
        assert "Reversal" in journal_data["remarks"]
        assert "Duplicate payment" in journal_data["remarks"]
        assert len(journal_data["lines"]) == 2
        
        # Verify debits and credits are swapped
        reversing_line_1 = journal_data["lines"][0]
        assert reversing_line_1["debit"] == Decimal("0.00")  # Original credit
        assert reversing_line_1["credit"] == Decimal("1000.00")  # Original debit
        assert "Reversal:" in reversing_line_1["remarks"]
        
        reversing_line_2 = journal_data["lines"][1]
        assert reversing_line_2["debit"] == Decimal("1000.00")  # Original credit
        assert reversing_line_2["credit"] == Decimal("0.00")  # Original debit
        assert "Reversal:" in reversing_line_2["remarks"]

    def test_reverse_payment_journal_entry_not_found(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test reversing journal entry when original not found"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock get_by_reference to return None
        journal_posting_service.journal_entry_service.get_by_reference = Mock(
            return_value=None
        )
        
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            journal_posting_service.reverse_payment_journal_entry(
                payment_entry=sample_payment_entry,
                organization_id=organization_id,
                user_id=user_id,
            )
        
        assert "not found" in str(exc_info.value).lower()

    def test_reverse_payment_journal_entry_reference_tracking(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test that reversing entry maintains reference tracking"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock original journal entry with proper debit and credit lines
        original_je = Mock()
        original_je.id = uuid.uuid4()
        original_je.lines = [
            Mock(
                account_id=uuid.uuid4(),
                debit=Decimal("500.00"),
                credit=Decimal("0.00"),
                against_account_id=uuid.uuid4(),
                remarks="Test debit",
            ),
            Mock(
                account_id=uuid.uuid4(),
                debit=Decimal("0.00"),
                credit=Decimal("500.00"),
                against_account_id=uuid.uuid4(),
                remarks="Test credit",
            ),
        ]
        
        journal_posting_service.journal_entry_service.get_by_reference = Mock(
            return_value={
                "id": original_je.id,
                "total_debit": Decimal("500.00"),
                "total_credit": Decimal("500.00"),
            }
        )
        journal_posting_service.journal_entry_service.repo.get_by_reference = Mock(
            return_value=original_je
        )
        
        sample_payment_entry.cancellation_reason = "Test cancellation"
        
        # Execute
        result = journal_posting_service.reverse_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify reference tracking
        call_args = journal_posting_service.journal_entry_service.create.call_args
        journal_data = call_args[1]["data"]
        
        assert journal_data["reference_type"] == "PaymentEntry"
        assert journal_data["reference_id"] == sample_payment_entry.id
        
        # Verify all lines have reference tracking
        for line in journal_data["lines"]:
            assert line["reference_type"] == "PaymentEntry"
            assert line["reference_id"] == sample_payment_entry.id
