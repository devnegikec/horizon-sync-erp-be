"""Unit tests for JournalPostingService"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock

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
        service.create = Mock(
            return_value={
                "id": uuid.uuid4(),
                "entry_no": "JE-2024-001",
                "status": "Posted",
                "total_debit": Decimal("1000.00"),
                "total_credit": Decimal("1000.00"),
            }
        )
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
        service.convert = Mock(
            side_effect=lambda amount, from_currency, to_currency: amount
        )
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
        payment.bank_account_id = None  # Default to None for non-bank payments
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
        assert journal_data["status"] == "posted"
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
        journal_posting_service.currency_service.get_base_currency = Mock(
            return_value="USD"
        )
        journal_posting_service.currency_service.convert = Mock(
            return_value=Decimal("1100.00")
        )

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
        assert journal_data["status"] == "posted"
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


    # ========================================================================
    # Tests for Bank Account Integration (Bug 2 Fix)
    # ========================================================================

    def test_get_payment_account_by_mode_with_bank_account_id(
        self,
        journal_posting_service,
    ):
        """Test _get_payment_account_by_mode returns specific gl_account_id when bank_account_id provided"""
        organization_id = uuid.uuid4()
        bank_account_id = uuid.uuid4()
        gl_account_id = uuid.uuid4()
        
        # Mock BankAccount
        mock_bank_account = Mock()
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = organization_id
        mock_bank_account.gl_account_id = gl_account_id
        mock_bank_account.is_active = True
        mock_bank_account.bank_name = "HDFC Bank"
        
        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_bank_account)
        mock_query.filter = Mock(return_value=mock_filter)
        journal_posting_service.db.query = Mock(return_value=mock_query)
        
        # Execute
        result = journal_posting_service._get_payment_account_by_mode(
            payment_mode="Bank_Transfer",
            organization_id=organization_id,
            bank_account_id=bank_account_id,
        )
        
        # Verify
        assert result == gl_account_id
        journal_posting_service.db.query.assert_called_once()

    def test_get_payment_account_by_mode_without_bank_account_id(
        self,
        journal_posting_service,
    ):
        """Test _get_payment_account_by_mode returns generic 'bank' account when bank_account_id not provided"""
        organization_id = uuid.uuid4()
        generic_bank_account_id = uuid.uuid4()
        
        # Mock default account service to return generic bank account
        mock_default_account = Mock()
        mock_default_account.account_id = generic_bank_account_id
        journal_posting_service.default_account_service.get_default_account = Mock(
            return_value=mock_default_account
        )
        
        # Execute
        result = journal_posting_service._get_payment_account_by_mode(
            payment_mode="Bank_Transfer",
            organization_id=organization_id,
            bank_account_id=None,
        )
        
        # Verify
        assert result == generic_bank_account_id
        journal_posting_service.default_account_service.get_default_account.assert_called_once_with(
            transaction_type="bank",
            organization_id=organization_id,
        )

    def test_get_payment_account_by_mode_with_inactive_bank_account(
        self,
        journal_posting_service,
    ):
        """Test _get_payment_account_by_mode raises ValidationError when bank account is inactive"""
        organization_id = uuid.uuid4()
        bank_account_id = uuid.uuid4()
        
        # Mock inactive BankAccount
        mock_bank_account = Mock()
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = organization_id
        mock_bank_account.gl_account_id = uuid.uuid4()
        mock_bank_account.is_active = False
        mock_bank_account.bank_name = "HDFC Bank"
        
        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_bank_account)
        mock_query.filter = Mock(return_value=mock_filter)
        journal_posting_service.db.query = Mock(return_value=mock_query)
        
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            journal_posting_service._get_payment_account_by_mode(
                payment_mode="Bank_Transfer",
                organization_id=organization_id,
                bank_account_id=bank_account_id,
            )
        
        assert "not active" in str(exc_info.value).lower()
        assert "HDFC Bank" in str(exc_info.value)

    def test_get_payment_account_by_mode_with_bank_account_from_different_org(
        self,
        journal_posting_service,
    ):
        """Test _get_payment_account_by_mode raises ValidationError when bank account belongs to different organization"""
        organization_id = uuid.uuid4()
        different_org_id = uuid.uuid4()
        bank_account_id = uuid.uuid4()
        
        # Mock BankAccount from different organization
        mock_bank_account = Mock()
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = different_org_id  # Different org
        mock_bank_account.gl_account_id = uuid.uuid4()
        mock_bank_account.is_active = True
        mock_bank_account.bank_name = "HDFC Bank"
        
        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_bank_account)
        mock_query.filter = Mock(return_value=mock_filter)
        journal_posting_service.db.query = Mock(return_value=mock_query)
        
        # Execute and verify exception
        with pytest.raises(ValidationError) as exc_info:
            journal_posting_service._get_payment_account_by_mode(
                payment_mode="Bank_Transfer",
                organization_id=organization_id,
                bank_account_id=bank_account_id,
            )
        
        assert "does not belong to organization" in str(exc_info.value).lower()

    def test_get_payment_account_by_mode_with_nonexistent_bank_account_id(
        self,
        journal_posting_service,
    ):
        """Test _get_payment_account_by_mode raises ResourceNotFoundException when bank_account_id not found"""
        from app.core.exceptions import ResourceNotFoundException
        
        organization_id = uuid.uuid4()
        bank_account_id = uuid.uuid4()
        
        # Mock database query returning None (not found)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        journal_posting_service.db.query = Mock(return_value=mock_query)
        
        # Execute and verify exception
        with pytest.raises(ResourceNotFoundException) as exc_info:
            journal_posting_service._get_payment_account_by_mode(
                payment_mode="Bank_Transfer",
                organization_id=organization_id,
                bank_account_id=bank_account_id,
            )
        
        assert "not found" in str(exc_info.value).lower()
        assert str(bank_account_id) in str(exc_info.value)

    def test_post_payment_journal_entry_with_bank_account_id(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test posting journal entry for Bank_Transfer payment with specific bank_account_id"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        bank_account_id = uuid.uuid4()
        gl_account_id = uuid.uuid4()
        
        # Set payment to Bank_Transfer with bank_account_id
        sample_payment_entry.payment_mode = PaymentMode.BANK_TRANSFER
        sample_payment_entry.bank_account_id = bank_account_id
        
        # Mock BankAccount
        mock_bank_account = Mock()
        mock_bank_account.id = bank_account_id
        mock_bank_account.organization_id = organization_id
        mock_bank_account.gl_account_id = gl_account_id
        mock_bank_account.is_active = True
        mock_bank_account.bank_name = "HDFC Bank"
        
        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_bank_account)
        mock_query.filter = Mock(return_value=mock_filter)
        journal_posting_service.db.query = Mock(return_value=mock_query)
        
        # Execute
        result = journal_posting_service.post_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify
        assert result is not None
        assert result["status"] == "Posted"
        
        # Verify journal entry was created with specific bank account's gl_account_id
        journal_posting_service.journal_entry_service.create.assert_called_once()
        call_args = journal_posting_service.journal_entry_service.create.call_args
        journal_data = call_args[1]["data"]
        
        # Verify debit line uses specific bank account's gl_account_id
        debit_line = journal_data["lines"][0]
        assert debit_line["account_id"] == gl_account_id
        assert debit_line["debit"] == Decimal("1000.00")
        assert debit_line["credit"] == Decimal("0.00")

    def test_reverse_payment_journal_entry_with_bank_account_id(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test reversing journal entry for payment with bank_account_id uses same specific account"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        bank_account_id = uuid.uuid4()
        gl_account_id = uuid.uuid4()
        
        # Set payment to Bank_Transfer with bank_account_id
        sample_payment_entry.payment_mode = PaymentMode.BANK_TRANSFER
        sample_payment_entry.bank_account_id = bank_account_id
        sample_payment_entry.cancellation_reason = "Duplicate payment"
        
        # Mock original journal entry that used specific bank account
        original_je = Mock()
        original_je.id = uuid.uuid4()
        original_je.lines = [
            Mock(
                account_id=gl_account_id,  # Specific bank account's GL account
                debit=Decimal("1000.00"),
                credit=Decimal("0.00"),
                against_account_id=uuid.uuid4(),
                remarks="Payment via HDFC Bank",
            ),
            Mock(
                account_id=uuid.uuid4(),  # AR account
                debit=Decimal("0.00"),
                credit=Decimal("1000.00"),
                against_account_id=gl_account_id,
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
        
        # Execute
        result = journal_posting_service.reverse_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify
        assert result is not None
        assert result["status"] == "Posted"
        
        # Verify reversing entry was created
        journal_posting_service.journal_entry_service.create.assert_called()
        call_args = journal_posting_service.journal_entry_service.create.call_args
        journal_data = call_args[1]["data"]
        
        # Verify reversing entry uses same specific bank account's gl_account_id
        reversing_line_1 = journal_data["lines"][0]
        assert reversing_line_1["account_id"] == gl_account_id
        assert reversing_line_1["debit"] == Decimal("0.00")  # Reversed
        assert reversing_line_1["credit"] == Decimal("1000.00")  # Reversed
        
        # Verify voucher type is reversal
        assert journal_data["voucher_type"] == "Payment Entry Reversal"
        assert "Reversal" in journal_data["remarks"]
        assert "Duplicate payment" in journal_data["remarks"]

    def test_post_payment_journal_entry_bank_transfer_backward_compatibility(
        self,
        journal_posting_service,
        sample_payment_entry,
    ):
        """Test Bank_Transfer without bank_account_id falls back to generic 'bank' account"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        generic_bank_account_id = uuid.uuid4()
        
        # Set payment to Bank_Transfer WITHOUT bank_account_id
        sample_payment_entry.payment_mode = PaymentMode.BANK_TRANSFER
        sample_payment_entry.bank_account_id = None
        
        # Mock default account service to return generic bank account
        mock_default_account = Mock()
        mock_default_account.account_id = generic_bank_account_id
        
        def get_default_account(transaction_type, organization_id):
            if transaction_type == "bank":
                return mock_default_account
            elif transaction_type == "accounts_receivable":
                ar_account = Mock()
                ar_account.account_id = uuid.uuid4()
                return ar_account
            else:
                raise ValidationError(f"Account not configured for {transaction_type}")
        
        journal_posting_service.default_account_service.get_default_account = Mock(
            side_effect=get_default_account
        )
        
        # Execute
        result = journal_posting_service.post_payment_journal_entry(
            payment_entry=sample_payment_entry,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify
        assert result is not None
        assert result["status"] == "Posted"
        
        # Verify default account service was called for generic "bank" account
        calls = journal_posting_service.default_account_service.get_default_account.call_args_list
        transaction_types = [call[1]["transaction_type"] for call in calls]
        assert "bank" in transaction_types
        
        # Verify journal entry uses generic bank account
        call_args = journal_posting_service.journal_entry_service.create.call_args
        journal_data = call_args[1]["data"]
        debit_line = journal_data["lines"][0]
        assert debit_line["account_id"] == generic_bank_account_id
