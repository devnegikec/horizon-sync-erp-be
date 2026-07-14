"""End-to-end integration test for payment cancellation flow

Tests the complete payment cancellation lifecycle:
1. Create invoice and confirm it
2. Create payment with bank_account_id and allocate to invoice
3. Cancel payment → Verify reversing entry created using specific bank account's gl_account_id
4. Verify outstanding_amount restored to original value
5. Verify invoice status changed back to "submitted"

**Validates: Requirements 2.9, 2.10, 2.13**
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


class TestPaymentCancellationFlow:
    """End-to-end integration test for payment cancellation flow
    
    **Validates: Requirements 2.9, 2.10, 2.13**
    """

    def test_payment_cancellation_with_bank_account(
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
        """Test payment cancellation flow with bank account
        
        Flow:
        1. Create invoice and confirm it
        2. Create payment with bank_account_id and allocate to invoice
        3. Cancel payment → Verify reversing entry created using specific bank account's gl_account_id
        4. Verify outstanding_amount restored to original value
        5. Verify invoice status changed back to "submitted"
        
        **Validates: Requirements 2.9, 2.10, 2.13**
        """
        
        # Step 1: Create and confirm sales invoice
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-CANCEL-001",
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
        
        # Confirm invoice via API
        response = client_with_auth.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200, f"Invoice confirmation failed: {response.text}"
        
        # Refresh invoice to get updated data
        db_session.refresh(invoice)
        
        assert invoice.status == "submitted"
        assert invoice.outstanding_amount == Decimal("1000.00")
        
        # Step 2: Create customer payment with bank_account_id
        payment = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-CANCEL-001",
            payment_type="Customer_Payment",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=hdfc_bank_account.id,
            amount=Decimal("1000.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            status="Confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        
        # Create journal entry for payment using JournalPostingService
        from app.services.journal_posting_service import JournalPostingService
        
        journal_service = JournalPostingService(db_session)
        journal_service.post_payment_journal_entry(
            payment_entry=payment,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify payment journal entry created with specific bank account
        payment_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "PaymentEntry",
                JournalEntry.reference_id == payment.id,
            )
            .all()
        )
        
        assert len(payment_journal_entries) == 1, "Expected 1 journal entry for payment"
        original_payment_je = payment_journal_entries[0]
        
        # Verify original payment journal entry uses specific bank account
        original_payment_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == original_payment_je.id)
            .all()
        )
        
        original_debit_line = next((line for line in original_payment_je_lines if line.debit > 0), None)
        assert original_debit_line is not None
        assert original_debit_line.account_id == bank_gl_account.id, "Original payment should debit specific bank account"
        
        # Step 3: Allocate payment to invoice
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
        
        # Refresh invoice to verify status changed to "paid"
        db_session.refresh(invoice)
        assert invoice.status == "paid"
        assert invoice.outstanding_amount == Decimal("0.00")
        
        # Step 4: Cancel payment using service layer
        from app.services.payment_entry_service import PaymentEntryService
        
        payment_service = PaymentEntryService(db_session)
        cancelled_payment = payment_service.cancel_payment(
            payment_id=payment.id,
            cancellation_reason="Test cancellation",
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Refresh payment to verify status
        db_session.refresh(payment)
        assert payment.status.value == "Cancelled", f"Payment status should be 'Cancelled', got {payment.status.value}"
        assert payment.cancellation_reason == "Test cancellation"
        
        # Step 5: Verify reversing journal entry created
        all_payment_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "PaymentEntry",
                JournalEntry.reference_id == payment.id,
            )
            .order_by(JournalEntry.created_at)
            .all()
        )
        
        assert len(all_payment_journal_entries) == 2, f"Expected 2 journal entries (original + reversal), found {len(all_payment_journal_entries)}"
        
        reversing_je = all_payment_journal_entries[1]
        
        # Verify reversing journal entry lines
        reversing_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == reversing_je.id)
            .all()
        )
        
        assert len(reversing_je_lines) == 2, f"Expected 2 reversing journal entry lines, found {len(reversing_je_lines)}"
        
        # Find debit and credit lines in reversing entry
        reversing_debit_line = next((line for line in reversing_je_lines if line.debit > 0), None)
        reversing_credit_line = next((line for line in reversing_je_lines if line.credit > 0), None)
        
        assert reversing_debit_line is not None, "Reversing debit line not found"
        assert reversing_credit_line is not None, "Reversing credit line not found"
        
        # Verify reversing entry uses specific bank account's gl_account_id
        # Original: Debit Bank, Credit AR
        # Reversal: Debit AR, Credit Bank
        assert reversing_debit_line.account_id == accounts_receivable_account.id, "Reversing entry should debit AR"
        assert reversing_debit_line.debit == Decimal("1000.00")
        
        assert reversing_credit_line.account_id == bank_gl_account.id, "Reversing entry should credit specific bank account (HDFC)"
        assert reversing_credit_line.credit == Decimal("1000.00")
        
        # Verify debits equal credits in reversing entry
        reversing_total_debits = sum(line.debit for line in reversing_je_lines)
        reversing_total_credits = sum(line.credit for line in reversing_je_lines)
        assert reversing_total_debits == reversing_total_credits, "Reversing entry debits should equal credits"
        
        # Step 6: Verify payment allocation removed
        remaining_references = (
            db_session.query(PaymentReference)
            .filter(
                PaymentReference.payment_entry_id == payment.id,
                PaymentReference.organization_id == organization_id,
            )
            .all()
        )
        
        assert len(remaining_references) == 0, "Payment references should be removed after cancellation"
        
        # Step 7: Verify invoice outstanding_amount restored and status changed back to "submitted"
        db_session.refresh(invoice)
        
        assert invoice.outstanding_amount == Decimal("1000.00"), f"outstanding_amount should be restored to 1000.00, got {invoice.outstanding_amount}"
        assert invoice.status == "submitted", f"Invoice status should be 'submitted' after payment cancellation, got {invoice.status}"
        
        print("✓ Payment cancellation flow test passed successfully")
        print(f"  - Invoice {invoice.invoice_no} created and confirmed")
        print(f"  - Payment {payment.reference_no} created with bank_account_id (HDFC)")
        print(f"  - Payment allocated to invoice → Invoice status: paid, outstanding: $0.00")
        print(f"  - Payment cancelled → Reversing entry created")
        print(f"  - Reversing entry uses specific bank account: Debit AR ${reversing_debit_line.debit}, Credit Bank ${reversing_credit_line.credit}")
        print(f"  - Invoice status restored: {invoice.status}, outstanding_amount: ${invoice.outstanding_amount}")
        print(f"  - All journal entries balanced (debits = credits)")

    def test_payment_cancellation_without_bank_account(
        self,
        db_session,
        client_with_auth,
        organization_id,
        user_id,
        customer_id,
        default_accounts,
        accounts_receivable_account,
        sales_revenue_account,
    ):
        """Test payment cancellation flow without bank account (backward compatibility)
        
        Flow:
        1. Create invoice and confirm it
        2. Create payment without bank_account_id (uses generic "bank" account)
        3. Allocate payment to invoice
        4. Cancel payment → Verify reversing entry created using generic "bank" account
        5. Verify outstanding_amount restored and status changed back to "submitted"
        
        **Validates: Requirements 2.10, 2.13**
        """
        
        # Create generic bank default account
        generic_bank_account = Account(
            organization_id=organization_id,
            account_code="1000",
            account_name="Bank Account (Generic)",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test_user",
            updated_by="test_user",
        )
        db_session.add(generic_bank_account)
        db_session.commit()
        db_session.refresh(generic_bank_account)
        
        # Create default account for "bank" transaction type
        bank_default = DefaultAccount(
            organization_id=organization_id,
            transaction_type="bank",
            account_id=generic_bank_account.id,
        )
        db_session.add(bank_default)
        db_session.commit()
        
        # Step 1: Create and confirm sales invoice
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-CANCEL-002",
            invoice_type="sales",
            party_id=customer_id,
            party_type="Customer",
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
        
        # Confirm invoice via API
        response = client_with_auth.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200
        
        db_session.refresh(invoice)
        assert invoice.status == "submitted"
        assert invoice.outstanding_amount == Decimal("500.00")
        
        # Step 2: Create customer payment WITHOUT bank_account_id
        payment = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-CANCEL-002",
            payment_type="Customer_Payment",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=None,  # No specific bank account
            amount=Decimal("500.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            status="Confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        
        # Create journal entry for payment using JournalPostingService
        from app.services.journal_posting_service import JournalPostingService
        
        journal_service = JournalPostingService(db_session)
        journal_service.post_payment_journal_entry(
            payment_entry=payment,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Verify payment journal entry uses generic bank account
        payment_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "PaymentEntry",
                JournalEntry.reference_id == payment.id,
            )
            .all()
        )
        
        assert len(payment_journal_entries) == 1
        original_payment_je = payment_journal_entries[0]
        
        original_payment_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == original_payment_je.id)
            .all()
        )
        
        original_debit_line = next((line for line in original_payment_je_lines if line.debit > 0), None)
        assert original_debit_line.account_id == generic_bank_account.id, "Original payment should debit generic bank account"
        
        # Step 3: Allocate payment to invoice
        payment_reference = PaymentReference(
            organization_id=organization_id,
            payment_entry_id=payment.id,
            reference_type="Invoice",
            reference_id=invoice.id,
            allocated_amount=Decimal("500.00"),
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_reference)
        db_session.commit()
        
        db_session.refresh(invoice)
        assert invoice.status == "paid"
        assert invoice.outstanding_amount == Decimal("0.00")
        
        # Step 4: Cancel payment
        from app.services.payment_entry_service import PaymentEntryService
        
        payment_service = PaymentEntryService(db_session)
        payment_service.cancel_payment(
            payment_id=payment.id,
            cancellation_reason="Test cancellation without bank account",
            organization_id=organization_id,
            user_id=user_id,
        )
        
        db_session.refresh(payment)
        assert payment.status.value == "Cancelled"
        
        # Step 5: Verify reversing entry uses generic bank account
        all_payment_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "PaymentEntry",
                JournalEntry.reference_id == payment.id,
            )
            .order_by(JournalEntry.created_at)
            .all()
        )
        
        assert len(all_payment_journal_entries) == 2
        reversing_je = all_payment_journal_entries[1]
        
        reversing_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == reversing_je.id)
            .all()
        )
        
        reversing_credit_line = next((line for line in reversing_je_lines if line.credit > 0), None)
        assert reversing_credit_line.account_id == generic_bank_account.id, "Reversing entry should credit generic bank account"
        assert reversing_credit_line.credit == Decimal("500.00")
        
        # Step 6: Verify invoice restored
        db_session.refresh(invoice)
        assert invoice.outstanding_amount == Decimal("500.00")
        assert invoice.status == "submitted"
        
        print("✓ Payment cancellation without bank account test passed successfully")
        print(f"  - Payment cancelled without bank_account_id")
        print(f"  - Reversing entry uses generic bank account")
        print(f"  - Invoice status restored: {invoice.status}, outstanding_amount: ${invoice.outstanding_amount}")
