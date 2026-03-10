"""Unit tests for InvoiceService.confirm_invoice method"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions import ValidationError, ResourceNotFoundException
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.invoice import Invoice
from app.services.invoice_service import InvoiceService


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Provide a test user ID"""
    return uuid.uuid4()


@pytest.fixture
def accounts_receivable_account(db_session, organization_id):
    """Create accounts receivable account"""
    account = Account(
        organization_id=organization_id,
        account_code="1100",
        account_name="Accounts Receivable",
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
def sales_revenue_account(db_session, organization_id):
    """Create sales revenue account"""
    account = Account(
        organization_id=organization_id,
        account_code="4000",
        account_name="Sales Revenue",
        account_type=AccountType.REVENUE,
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
def purchase_expense_account(db_session, organization_id):
    """Create purchase expense account"""
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
def accounts_payable_account(db_session, organization_id):
    """Create accounts payable account"""
    account = Account(
        organization_id=organization_id,
        account_code="2000",
        account_name="Accounts Payable",
        account_type=AccountType.LIABILITY,
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
def sales_default_accounts(
    db_session,
    organization_id,
    accounts_receivable_account,
    sales_revenue_account,
):
    """Create default accounts for sales invoices"""
    ar_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="accounts_receivable",
        account_id=accounts_receivable_account.id,
    )
    revenue_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="sales_revenue",
        account_id=sales_revenue_account.id,
    )
    db_session.add(ar_default)
    db_session.add(revenue_default)
    db_session.commit()
    return {
        "accounts_receivable": ar_default,
        "sales_revenue": revenue_default,
    }


@pytest.fixture
def purchase_default_accounts(
    db_session,
    organization_id,
    purchase_expense_account,
    accounts_payable_account,
):
    """Create default accounts for purchase invoices"""
    expense_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="purchase_expense",
        account_id=purchase_expense_account.id,
    )
    ap_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="accounts_payable",
        account_id=accounts_payable_account.id,
    )
    db_session.add(expense_default)
    db_session.add(ap_default)
    db_session.commit()
    return {
        "purchase_expense": expense_default,
        "accounts_payable": ap_default,
    }


@pytest.fixture
def draft_sales_invoice(db_session, organization_id, user_id):
    """Create a draft sales invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-SALES-DRAFT-001",
        invoice_type="Sales",
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("1000.00"),
        currency="USD",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def draft_purchase_invoice(db_session, organization_id, user_id):
    """Create a draft purchase invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-PURCHASE-DRAFT-001",
        invoice_type="Purchase",
        party_id=uuid.uuid4(),
        party_type="Supplier",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("500.00"),
        currency="USD",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def submitted_invoice(db_session, organization_id, user_id):
    """Create an already-submitted invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-SUBMITTED-001",
        invoice_type="Sales",
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="submitted",
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


class TestConfirmInvoiceSuccessPath:
    """Tests for successful invoice confirmation"""

    def test_confirm_sales_invoice_success(
        self,
        db_session,
        organization_id,
        user_id,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test successful confirmation of sales invoice
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.11**
        """
        service = InvoiceService(db_session)
        
        # Confirm the invoice
        result = service.confirm_invoice(
            draft_sales_invoice.id, organization_id, user_id
        )
        
        # Verify invoice status changed to submitted
        assert result["status"] == "submitted"
        
        # Verify submitted_at timestamp is set
        assert result["submitted_at"] is not None
        assert isinstance(result["submitted_at"], datetime)
        
        # Verify outstanding_amount equals grand_total
        assert result["outstanding_amount"] == draft_sales_invoice.grand_total
        assert result["outstanding_amount"] == Decimal("1000.00")
        
        # Verify updated_by is set
        assert result["updated_by"] == user_id

    def test_confirm_purchase_invoice_success(
        self,
        db_session,
        organization_id,
        user_id,
        draft_purchase_invoice,
        purchase_default_accounts,
    ):
        """Test successful confirmation of purchase invoice
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.11**
        """
        service = InvoiceService(db_session)
        
        # Confirm the invoice
        result = service.confirm_invoice(
            draft_purchase_invoice.id, organization_id, user_id
        )
        
        # Verify invoice status changed to submitted
        assert result["status"] == "submitted"
        
        # Verify submitted_at timestamp is set
        assert result["submitted_at"] is not None
        assert isinstance(result["submitted_at"], datetime)
        
        # Verify outstanding_amount equals grand_total
        assert result["outstanding_amount"] == draft_purchase_invoice.grand_total
        assert result["outstanding_amount"] == Decimal("500.00")
        
        # Verify updated_by is set
        assert result["updated_by"] == user_id


class TestConfirmInvoiceValidation:
    """Tests for invoice confirmation validation"""

    def test_confirm_already_submitted_invoice_fails(
        self,
        db_session,
        organization_id,
        user_id,
        submitted_invoice,
        sales_default_accounts,
    ):
        """Test that confirming an already-submitted invoice fails
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        service = InvoiceService(db_session)
        
        # Attempt to confirm already-submitted invoice
        with pytest.raises(ValidationError) as exc_info:
            service.confirm_invoice(
                submitted_invoice.id, organization_id, user_id
            )
        
        # Verify error message
        assert "must be in draft status" in str(exc_info.value)
        assert "submitted" in str(exc_info.value).lower()

    def test_confirm_invoice_with_missing_default_accounts_fails(
        self,
        db_session,
        organization_id,
        user_id,
        draft_sales_invoice,
    ):
        """Test that confirming invoice without default accounts fails
        
        **Validates: Requirements 2.1, 2.2**
        """
        service = InvoiceService(db_session)
        
        # Attempt to confirm invoice without default accounts configured
        with pytest.raises(ValidationError) as exc_info:
            service.confirm_invoice(
                draft_sales_invoice.id, organization_id, user_id
            )
        
        # Verify error message mentions missing accounts
        error_message = str(exc_info.value)
        assert "not configured" in error_message.lower() or "required" in error_message.lower()

    def test_confirm_nonexistent_invoice_fails(
        self,
        db_session,
        organization_id,
        user_id,
    ):
        """Test that confirming non-existent invoice fails"""
        service = InvoiceService(db_session)
        
        # Attempt to confirm non-existent invoice
        nonexistent_id = uuid.uuid4()
        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.confirm_invoice(
                nonexistent_id, organization_id, user_id
            )
        
        # Verify error message
        assert str(nonexistent_id) in str(exc_info.value) or "not found" in str(exc_info.value).lower()


class TestConfirmInvoiceTransactionRollback:
    """Tests for transaction rollback on failure"""

    def test_confirm_invoice_rollback_on_journal_entry_failure(
        self,
        db_session,
        organization_id,
        user_id,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test that invoice status is not changed if journal entry creation fails
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        service = InvoiceService(db_session)
        
        # Mock the journal posting service to raise an error
        with patch(
            "app.services.invoice_journal_posting_service.InvoiceJournalPostingService.post_invoice_journal_entry"
        ) as mock_post:
            mock_post.side_effect = Exception(
                "Journal entry creation failed"
            )
            
            # Attempt to confirm invoice
            with pytest.raises(ValidationError) as exc_info:
                service.confirm_invoice(
                    draft_sales_invoice.id, organization_id, user_id
                )
            
            # Verify error message
            assert "Failed to confirm invoice" in str(exc_info.value)
        
        # Refresh invoice from database
        db_session.refresh(draft_sales_invoice)
        
        # Verify invoice status is still draft (rollback occurred)
        assert draft_sales_invoice.status == "draft"
        
        # Verify submitted_at is still None
        assert draft_sales_invoice.submitted_at is None
        
        # Verify outstanding_amount was not set
        assert draft_sales_invoice.outstanding_amount != draft_sales_invoice.grand_total


class TestConfirmInvoiceTimestampAndAmount:
    """Tests for submitted_at timestamp and outstanding_amount"""

    def test_submitted_at_is_set_correctly(
        self,
        db_session,
        organization_id,
        user_id,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test that submitted_at timestamp is set to current time
        
        **Validates: Requirements 2.4**
        """
        service = InvoiceService(db_session)
        
        # Record time before confirmation (with timezone)
        time_before = datetime.now(UTC)
        
        # Confirm the invoice
        result = service.confirm_invoice(
            draft_sales_invoice.id, organization_id, user_id
        )
        
        # Record time after confirmation (with timezone)
        time_after = datetime.now(UTC)
        
        # Verify submitted_at is set
        assert result["submitted_at"] is not None
        
        # Verify submitted_at is between time_before and time_after
        submitted_at = result["submitted_at"]
        # Make submitted_at timezone-aware if it's not
        if submitted_at.tzinfo is None:
            from zoneinfo import ZoneInfo
            submitted_at = submitted_at.replace(tzinfo=ZoneInfo("UTC"))
        assert time_before <= submitted_at <= time_after

    def test_outstanding_amount_equals_grand_total(
        self,
        db_session,
        organization_id,
        user_id,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test that outstanding_amount is set equal to grand_total
        
        **Validates: Requirements 2.11**
        """
        service = InvoiceService(db_session)
        
        # Confirm the invoice
        result = service.confirm_invoice(
            draft_sales_invoice.id, organization_id, user_id
        )
        
        # Verify outstanding_amount equals grand_total
        assert result["outstanding_amount"] == result["grand_total"]
        assert result["outstanding_amount"] == Decimal("1000.00")

    def test_outstanding_amount_for_purchase_invoice(
        self,
        db_session,
        organization_id,
        user_id,
        draft_purchase_invoice,
        purchase_default_accounts,
    ):
        """Test that outstanding_amount is set correctly for purchase invoice
        
        **Validates: Requirements 2.11**
        """
        service = InvoiceService(db_session)
        
        # Confirm the invoice
        result = service.confirm_invoice(
            draft_purchase_invoice.id, organization_id, user_id
        )
        
        # Verify outstanding_amount equals grand_total
        assert result["outstanding_amount"] == result["grand_total"]
        assert result["outstanding_amount"] == Decimal("500.00")
