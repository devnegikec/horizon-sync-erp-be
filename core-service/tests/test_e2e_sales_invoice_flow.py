"""End-to-end integration test for sales invoice flow

Tests the complete sales invoice lifecycle from creation to payment:
1. Create draft sales invoice
2. Confirm invoice → Verify journal entry created (Debit AR, Credit Revenue)
3. Verify submitted_at timestamp set
4. Verify outstanding_amount equals grand_total
5. Create customer payment with bank_account_id → Verify journal entry created (Debit Bank GL Account, Credit AR)
6. Allocate payment to invoice → Verify outstanding_amount updated, status changed to "paid"
7. Verify journal entries are correct and debits equal credits

**Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.11, 2.12**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.invoice import Invoice
from app.models.payment_entry import PaymentEntry
from app.models.payment_reference import PaymentReference
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.bank_account import BankAccount
from app.dependencies import CurrentUser


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Provide a test user ID"""
    return uuid.uuid4()


@pytest.fixture
def customer_id():
    """Provide a test customer ID"""
    return uuid.uuid4()


@pytest.fixture
def mock_user(organization_id, user_id):
    """Create a mock user with all necessary permissions"""
    return CurrentUser(
        id=user_id,
        email="test@example.com",
        organization_id=organization_id,
        user_type="user",
        permissions=[
            "invoice.create",
            "invoice.read",
            "invoice.update",
            "invoice.delete",
            "payment.create",
            "payment.read",
            "payment.update",
            "payment.delete",
        ],
    )


@pytest.fixture
def client_with_auth(db_session, mock_user):
    """Create a test client with authentication"""
    from app.database import get_db
    from app.dependencies import get_current_active_user

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


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
def bank_gl_account(db_session, organization_id):
    """Create bank GL account for HDFC bank"""
    account = Account(
        organization_id=organization_id,
        account_code="1010",
        account_name="HDFC Bank Account",
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
def hdfc_bank_account(db_session, organization_id, bank_gl_account):
    """Create HDFC bank account linked to GL account"""
    bank_account = BankAccount(
        organization_id=organization_id,
        bank_name="HDFC Bank",
        account_number="1234567890",
        account_holder_name="Test Company",
        branch_name="Main Branch",
        ifsc_code="HDFC0001234",
        country_code="IN",
        currency="USD",
        gl_account_id=bank_gl_account.id,
        is_active=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(bank_account)
    db_session.commit()
    db_session.refresh(bank_account)
    return bank_account


@pytest.fixture
def default_accounts(
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


class TestEndToEndSalesInvoiceFlow:
    """End-to-end integration test for complete sales invoice flow
    
    **Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.11, 2.12**
    """

    def test_complete_sales_invoice_to_payment_flow(
        self,
        db_session,
        client_with_auth,
        organization_id,
        user_id,
        customer_id,
        default_accounts,
        hdfc_bank_account,
        accounts_receivable_account,
        sales_revenue_account,
        bank_gl_account,
    ):
        """Test complete sales invoice flow from creation to payment
        
        Flow:
        1. Create draft sales invoice
        2. Confirm invoice → Verify journal entry created (Debit AR, Credit Revenue)
        3. Verify submitted_at timestamp set
        4. Verify outstanding_amount equals grand_total
        5. Create customer payment with bank_account_id → Verify journal entry created (Debit Bank GL Account, Credit AR)
        6. Allocate payment to invoice → Verify outstanding_amount updated, status changed to "paid"
        7. Verify journal entries are correct and debits equal credits
        
        **Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.11, 2.12**
        """
        
        # Step 1: Create draft sales invoice
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-E2E-001",
            invoice_type="sales",
            party_id=customer_id,
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
        
        assert invoice.status == "draft"
        assert invoice.submitted_at is None
        assert invoice.outstanding_amount is None or invoice.outstanding_amount == Decimal("0.00")
        
        # Step 2: Confirm invoice via API
        response = client_with_auth.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200, f"Invoice confirmation failed: {response.text}"
        
        # Refresh invoice to get updated data
        db_session.refresh(invoice)
        
        # Step 3: Verify invoice status and fields updated
        assert invoice.status == "submitted", "Invoice status should be 'submitted'"
        assert invoice.submitted_at is not None, "submitted_at should be set"
        assert invoice.outstanding_amount == Decimal("1000.00"), f"outstanding_amount should equal grand_total, got {invoice.outstanding_amount}"
        
        # Step 4: Verify journal entry created for invoice confirmation
        invoice_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "Invoice",
                JournalEntry.reference_id == invoice.id,
            )
            .all()
        )
        
        assert len(invoice_journal_entries) == 1, f"Expected 1 journal entry for invoice, found {len(invoice_journal_entries)}"
        invoice_je = invoice_journal_entries[0]
        
        # Verify journal entry lines for invoice
        invoice_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == invoice_je.id)
            .all()
        )
        
        assert len(invoice_je_lines) == 2, f"Expected 2 journal entry lines, found {len(invoice_je_lines)}"
        
        # Find debit and credit lines
        debit_line = next((line for line in invoice_je_lines if line.debit > 0), None)
        credit_line = next((line for line in invoice_je_lines if line.credit > 0), None)
        
        assert debit_line is not None, "Debit line not found"
        assert credit_line is not None, "Credit line not found"
        
        # Verify Debit AR, Credit Revenue
        assert debit_line.account_id == accounts_receivable_account.id, "Debit should be to Accounts Receivable"
        assert debit_line.debit == Decimal("1000.00"), f"Debit amount should be 1000.00, got {debit_line.debit}"
        
        assert credit_line.account_id == sales_revenue_account.id, "Credit should be to Sales Revenue"
        assert credit_line.credit == Decimal("1000.00"), f"Credit amount should be 1000.00, got {credit_line.credit}"
        
        # Verify debits equal credits
        total_debits = sum(line.debit for line in invoice_je_lines)
        total_credits = sum(line.credit for line in invoice_je_lines)
        assert total_debits == total_credits, f"Debits ({total_debits}) should equal credits ({total_credits})"
        
        # Step 5: Create customer payment with bank_account_id
        payment = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-E2E-001",
            payment_type="Receive",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=hdfc_bank_account.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            status="confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        
        assert payment.bank_account_id == hdfc_bank_account.id, "Payment should have bank_account_id set"
        
        # Step 6: Verify journal entry created for payment
        payment_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "PaymentEntry",
                JournalEntry.reference_id == payment.id,
            )
            .all()
        )
        
        assert len(payment_journal_entries) == 1, f"Expected 1 journal entry for payment, found {len(payment_journal_entries)}"
        payment_je = payment_journal_entries[0]
        
        # Verify journal entry lines for payment
        payment_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == payment_je.id)
            .all()
        )
        
        assert len(payment_je_lines) == 2, f"Expected 2 journal entry lines for payment, found {len(payment_je_lines)}"
        
        # Find debit and credit lines for payment
        payment_debit_line = next((line for line in payment_je_lines if line.debit > 0), None)
        payment_credit_line = next((line for line in payment_je_lines if line.credit > 0), None)
        
        assert payment_debit_line is not None, "Payment debit line not found"
        assert payment_credit_line is not None, "Payment credit line not found"
        
        # Verify Debit Bank GL Account, Credit AR
        assert payment_debit_line.account_id == bank_gl_account.id, f"Debit should be to Bank GL Account (HDFC), got account_id {payment_debit_line.account_id}"
        assert payment_debit_line.debit == Decimal("1000.00"), f"Debit amount should be 1000.00, got {payment_debit_line.debit}"
        
        assert payment_credit_line.account_id == accounts_receivable_account.id, "Credit should be to Accounts Receivable"
        assert payment_credit_line.credit == Decimal("1000.00"), f"Credit amount should be 1000.00, got {payment_credit_line.credit}"
        
        # Verify debits equal credits for payment
        payment_total_debits = sum(line.debit for line in payment_je_lines)
        payment_total_credits = sum(line.credit for line in payment_je_lines)
        assert payment_total_debits == payment_total_credits, f"Payment debits ({payment_total_debits}) should equal credits ({payment_total_credits})"
        
        # Step 7: Allocate payment to invoice
        payment_reference = PaymentReference(
            organization_id=organization_id,
            payment_entry_id=payment.id,
            reference_type="Invoice",
            reference_id=invoice.id,
            allocated_amount=Decimal("1000.00"),
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_reference)
        db_session.commit()
        
        # Refresh invoice to get updated outstanding_amount and status
        db_session.refresh(invoice)
        
        # Step 8: Verify outstanding_amount updated and status changed to "paid"
        assert invoice.outstanding_amount == Decimal("0.00"), f"outstanding_amount should be 0.00 after full payment, got {invoice.outstanding_amount}"
        assert invoice.status == "paid", f"Invoice status should be 'paid' after full payment, got {invoice.status}"
        
        # Step 9: Verify all journal entries are correct
        all_journal_entries = (
            db_session.query(JournalEntry)
            .filter(JournalEntry.organization_id == organization_id)
            .all()
        )
        
        assert len(all_journal_entries) == 2, f"Expected 2 journal entries total (invoice + payment), found {len(all_journal_entries)}"
        
        # Verify each journal entry has debits equal credits
        for je in all_journal_entries:
            je_lines = (
                db_session.query(JournalEntryLine)
                .filter(JournalEntryLine.journal_entry_id == je.id)
                .all()
            )
            je_debits = sum(line.debit for line in je_lines)
            je_credits = sum(line.credit for line in je_lines)
            assert je_debits == je_credits, f"Journal entry {je.id} debits ({je_debits}) should equal credits ({je_credits})"
        
        print("✓ End-to-end sales invoice flow test passed successfully")
        print(f"  - Invoice {invoice.invoice_no} created and confirmed")
        print(f"  - Journal entry created: Debit AR ${debit_line.debit}, Credit Revenue ${credit_line.credit}")
        print(f"  - Payment {payment.reference_no} created with bank_account_id")
        print(f"  - Journal entry created: Debit Bank ${payment_debit_line.debit}, Credit AR ${payment_credit_line.credit}")
        print(f"  - Payment allocated to invoice")
        print(f"  - Invoice status: {invoice.status}, outstanding_amount: ${invoice.outstanding_amount}")
        print(f"  - All journal entries balanced (debits = credits)")
