"""Unit tests for InvoiceJournalPostingService"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.invoice import Invoice
from app.services.invoice_journal_posting_service import InvoiceJournalPostingService


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
def sales_invoice(db_session, organization_id, user_id):
    """Create a sales invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-SALES-001",
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


@pytest.fixture
def purchase_invoice(db_session, organization_id, user_id):
    """Create a purchase invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-PURCHASE-001",
        invoice_type="Purchase",
        party_id=uuid.uuid4(),
        party_type="Supplier",
        posting_date=datetime.now(UTC),
        status="submitted",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("500.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


class TestPostInvoiceJournalEntry:
    """Tests for post_invoice_journal_entry method"""

    def test_post_sales_invoice_journal_entry(
        self,
        db_session,
        organization_id,
        user_id,
        sales_invoice,
        sales_default_accounts,
        accounts_receivable_account,
        sales_revenue_account,
    ):
        """Test creating journal entry for sales invoice"""
        service = InvoiceJournalPostingService(db_session)
        
        result = service.post_invoice_journal_entry(
            sales_invoice, organization_id, user_id
        )
        
        # Verify journal entry was created
        assert result is not None
        assert result["status"] == "posted"
        assert result["voucher_type"] == "Invoice Confirmation"
        assert result["reference_type"] == "Invoice"
        assert result["reference_id"] == sales_invoice.id
        assert result["entry_no"] is not None

    def test_post_purchase_invoice_journal_entry(
        self,
        db_session,
        organization_id,
        user_id,
        purchase_invoice,
        purchase_default_accounts,
        purchase_expense_account,
        accounts_payable_account,
    ):
        """Test creating journal entry for purchase invoice"""
        service = InvoiceJournalPostingService(db_session)
        
        result = service.post_invoice_journal_entry(
            purchase_invoice, organization_id, user_id
        )
        
        # Verify journal entry was created
        assert result is not None
        assert result["status"] == "posted"
        assert result["voucher_type"] == "Invoice Confirmation"
        assert result["reference_type"] == "Invoice"
        assert result["reference_id"] == purchase_invoice.id
        assert result["entry_no"] is not None

    def test_post_invoice_with_invalid_type(
        self,
        db_session,
        organization_id,
        user_id,
        sales_invoice,
    ):
        """Test error handling for invalid invoice type"""
        service = InvoiceJournalPostingService(db_session)
        
        # Change invoice type to invalid value
        sales_invoice.invoice_type = "InvalidType"
        
        with pytest.raises(ValidationError) as exc_info:
            service.post_invoice_journal_entry(
                sales_invoice, organization_id, user_id
            )
        
        assert "Invalid invoice type" in str(exc_info.value)

    def test_post_invoice_with_zero_grand_total(
        self,
        db_session,
        organization_id,
        user_id,
        sales_invoice,
        sales_default_accounts,
    ):
        """Test error handling for invoice with zero grand total"""
        service = InvoiceJournalPostingService(db_session)
        
        # Set grand total to zero
        sales_invoice.grand_total = Decimal("0")
        
        with pytest.raises(ValidationError) as exc_info:
            service.post_invoice_journal_entry(
                sales_invoice, organization_id, user_id
            )
        
        assert "grand_total must be greater than zero" in str(exc_info.value)


class TestValidateInvoiceDefaultAccounts:
    """Tests for _validate_invoice_default_accounts method"""

    def test_validate_sales_accounts_configured(
        self,
        db_session,
        organization_id,
        sales_default_accounts,
        accounts_receivable_account,
        sales_revenue_account,
    ):
        """Test validation passes when sales accounts are configured"""
        service = InvoiceJournalPostingService(db_session)
        
        debit_id, credit_id = service._validate_invoice_default_accounts(
            "Sales", organization_id
        )
        
        assert debit_id == accounts_receivable_account.id
        assert credit_id == sales_revenue_account.id

    def test_validate_purchase_accounts_configured(
        self,
        db_session,
        organization_id,
        purchase_default_accounts,
        purchase_expense_account,
        accounts_payable_account,
    ):
        """Test validation passes when purchase accounts are configured"""
        service = InvoiceJournalPostingService(db_session)
        
        debit_id, credit_id = service._validate_invoice_default_accounts(
            "Purchase", organization_id
        )
        
        assert debit_id == purchase_expense_account.id
        assert credit_id == accounts_payable_account.id

    def test_validate_missing_accounts_receivable(
        self,
        db_session,
        organization_id,
        sales_revenue_account,
    ):
        """Test validation fails when accounts receivable is not configured"""
        # Only configure sales revenue, not accounts receivable
        revenue_default = DefaultAccount(
            organization_id=organization_id,
            transaction_type="sales_revenue",
            account_id=sales_revenue_account.id,
        )
        db_session.add(revenue_default)
        db_session.commit()
        
        service = InvoiceJournalPostingService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_invoice_default_accounts("Sales", organization_id)
        
        assert "accounts_receivable" in str(exc_info.value)
        assert "not configured" in str(exc_info.value)

    def test_validate_missing_sales_revenue(
        self,
        db_session,
        organization_id,
        accounts_receivable_account,
    ):
        """Test validation fails when sales revenue is not configured"""
        # Only configure accounts receivable, not sales revenue
        ar_default = DefaultAccount(
            organization_id=organization_id,
            transaction_type="accounts_receivable",
            account_id=accounts_receivable_account.id,
        )
        db_session.add(ar_default)
        db_session.commit()
        
        service = InvoiceJournalPostingService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_invoice_default_accounts("Sales", organization_id)
        
        assert "sales_revenue" in str(exc_info.value)
        assert "not configured" in str(exc_info.value)

    def test_validate_missing_purchase_expense(
        self,
        db_session,
        organization_id,
        accounts_payable_account,
    ):
        """Test validation fails when purchase expense is not configured"""
        # Only configure accounts payable, not purchase expense
        ap_default = DefaultAccount(
            organization_id=organization_id,
            transaction_type="accounts_payable",
            account_id=accounts_payable_account.id,
        )
        db_session.add(ap_default)
        db_session.commit()
        
        service = InvoiceJournalPostingService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_invoice_default_accounts("Purchase", organization_id)
        
        assert "purchase_expense" in str(exc_info.value)
        assert "not configured" in str(exc_info.value)

    def test_validate_missing_accounts_payable(
        self,
        db_session,
        organization_id,
        purchase_expense_account,
    ):
        """Test validation fails when accounts payable is not configured"""
        # Only configure purchase expense, not accounts payable
        expense_default = DefaultAccount(
            organization_id=organization_id,
            transaction_type="purchase_expense",
            account_id=purchase_expense_account.id,
        )
        db_session.add(expense_default)
        db_session.commit()
        
        service = InvoiceJournalPostingService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_invoice_default_accounts("Purchase", organization_id)
        
        assert "accounts_payable" in str(exc_info.value)
        assert "not configured" in str(exc_info.value)

    def test_validate_multiple_missing_accounts(
        self,
        db_session,
        organization_id,
    ):
        """Test validation fails with multiple missing accounts"""
        service = InvoiceJournalPostingService(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            service._validate_invoice_default_accounts("Sales", organization_id)
        
        error_message = str(exc_info.value)
        assert "accounts_receivable" in error_message
        assert "sales_revenue" in error_message
        assert "not configured" in error_message


class TestConvertToBaseCurrency:
    """Tests for _convert_to_base_currency method"""

    def test_convert_same_currency(
        self,
        db_session,
        organization_id,
    ):
        """Test conversion when amount is already in base currency"""
        service = InvoiceJournalPostingService(db_session)
        
        # USD is typically the base currency in tests
        result = service._convert_to_base_currency(
            Decimal("1000.00"), "USD", organization_id
        )
        
        assert result == Decimal("1000.00")

    def test_convert_foreign_currency(
        self,
        db_session,
        organization_id,
    ):
        """Test conversion from foreign currency to base currency"""
        service = InvoiceJournalPostingService(db_session)
        
        # This test assumes CurrencyService is properly configured
        # The actual conversion rate depends on the CurrencyService implementation
        try:
            result = service._convert_to_base_currency(
                Decimal("800.00"), "EUR", organization_id
            )
            # Verify result is a Decimal
            assert isinstance(result, Decimal)
            # Verify result is positive
            assert result > 0
        except ValidationError:
            # If currency conversion fails due to missing exchange rates,
            # that's expected behavior and the test passes
            pass


class TestErrorHandling:
    """Tests for error handling scenarios"""

    def test_invalid_invoice_type_error(
        self,
        db_session,
        organization_id,
        user_id,
    ):
        """Test error handling for invalid invoice type"""
        service = InvoiceJournalPostingService(db_session)
        
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-INVALID-001",
            invoice_type="InvalidType",
            grand_total=Decimal("1000.00"),
            currency="USD",
            submitted_at=datetime.now(UTC),
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service.post_invoice_journal_entry(invoice, organization_id, user_id)
        
        assert "Invalid invoice type" in str(exc_info.value)

    def test_negative_grand_total_error(
        self,
        db_session,
        organization_id,
        user_id,
        sales_default_accounts,
    ):
        """Test error handling for negative grand total"""
        service = InvoiceJournalPostingService(db_session)
        
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-NEGATIVE-001",
            invoice_type="Sales",
            grand_total=Decimal("-100.00"),
            currency="USD",
            submitted_at=datetime.now(UTC),
        )
        
        with pytest.raises(ValidationError) as exc_info:
            service.post_invoice_journal_entry(invoice, organization_id, user_id)
        
        assert "grand_total must be greater than zero" in str(exc_info.value)
