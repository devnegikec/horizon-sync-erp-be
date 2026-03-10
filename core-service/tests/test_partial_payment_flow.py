"""End-to-end integration test for partial payment flow

Tests the partial payment lifecycle with multiple payments:
1. Create invoice with grand_total $1,000
2. Confirm invoice
3. Create and allocate payment $300 → Verify outstanding_amount = $700, status = "partial"
4. Create and allocate payment $400 → Verify outstanding_amount = $300, status = "partial"
5. Create and allocate payment $300 → Verify outstanding_amount = $0, status = "paid"

**Validates: Requirements 2.11, 2.12**
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
    bank_gl_account,
):
    """Create default accounts for sales invoices and bank transfers"""
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
    # Add bank default account for backward compatibility
    # (even though we're using specific bank account, validation still checks for it)
    bank_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="bank",
        account_id=bank_gl_account.id,
    )
    db_session.add(ar_default)
    db_session.add(revenue_default)
    db_session.add(bank_default)
    db_session.commit()
    return {
        "accounts_receivable": ar_default,
        "sales_revenue": revenue_default,
        "bank": bank_default,
    }


class TestPartialPaymentFlow:
    """End-to-end integration test for partial payment flow
    
    **Validates: Requirements 2.11, 2.12**
    """

    def test_multiple_partial_payments_to_full_payment(
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
        """Test partial payment flow with multiple payments
        
        Flow:
        1. Create invoice with grand_total $1,000
        2. Confirm invoice
        3. Create and allocate payment $300 → Verify outstanding_amount = $700, status = "partial"
        4. Create and allocate payment $400 → Verify outstanding_amount = $300, status = "partial"
        5. Create and allocate payment $300 → Verify outstanding_amount = $0, status = "paid"
        
        **Validates: Requirements 2.11, 2.12**
        """
        
        # Step 1: Create draft sales invoice with grand_total $1,000
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-PARTIAL-001",
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
        assert invoice.grand_total == Decimal("1000.00")
        
        # Step 2: Confirm invoice via API
        response = client_with_auth.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200, f"Invoice confirmation failed: {response.text}"
        
        # Refresh invoice to get updated data
        db_session.refresh(invoice)
        
        # Verify invoice confirmed with outstanding_amount = grand_total
        assert invoice.status == "submitted", "Invoice status should be 'submitted'"
        assert invoice.submitted_at is not None, "submitted_at should be set"
        assert invoice.outstanding_amount == Decimal("1000.00"), f"outstanding_amount should equal grand_total ($1000.00), got {invoice.outstanding_amount}"
        
        # Verify invoice journal entry created
        invoice_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "Invoice",
                JournalEntry.reference_id == invoice.id,
            )
            .all()
        )
        
        assert len(invoice_journal_entries) == 1, "Expected 1 journal entry for invoice confirmation"
        
        # Step 3: Create and allocate first payment $300
        payment1 = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-PARTIAL-001",
            payment_type="Customer_Payment",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=hdfc_bank_account.id,
            amount=Decimal("300.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            status="Confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment1)
        db_session.commit()
        db_session.refresh(payment1)
        
        # Create journal entry for payment1 using JournalPostingService
        from app.services.journal_posting_service import JournalPostingService
        
        journal_service = JournalPostingService(db_session)
        journal_service.post_payment_journal_entry(
            payment_entry=payment1,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Allocate payment1 to invoice
        payment_reference1 = PaymentReference(
            organization_id=organization_id,
            payment_id=payment1.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("300.00"),
            created_by=user_id,
        )
        db_session.add(payment_reference1)
        db_session.commit()
        
        # Update invoice status using InvoiceStatusService
        from app.services.invoice_status_service import InvoiceStatusService
        
        status_service = InvoiceStatusService(db_session)
        status_service.update_invoice_status(
            invoice_id=invoice.id,
            organization_id=organization_id,
        )
        
        # Refresh invoice to get updated outstanding_amount and status
        db_session.refresh(invoice)
        
        # Verify outstanding_amount = $700, status = "partial"
        assert invoice.outstanding_amount == Decimal("700.00"), f"After $300 payment, outstanding_amount should be $700.00, got {invoice.outstanding_amount}"
        assert invoice.status == "partial", f"After partial payment, status should be 'partial', got {invoice.status}"
        
        print(f"✓ First payment: $300 allocated")
        print(f"  - Invoice status: {invoice.status}")
        print(f"  - Outstanding amount: ${invoice.outstanding_amount}")
        
        # Step 4: Create and allocate second payment $400
        payment2 = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-PARTIAL-002",
            payment_type="Customer_Payment",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=hdfc_bank_account.id,
            amount=Decimal("400.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            status="Confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment2)
        db_session.commit()
        db_session.refresh(payment2)
        
        # Create journal entry for payment2
        journal_service.post_payment_journal_entry(
            payment_entry=payment2,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Allocate payment2 to invoice
        payment_reference2 = PaymentReference(
            organization_id=organization_id,
            payment_id=payment2.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("400.00"),
            created_by=user_id,
        )
        db_session.add(payment_reference2)
        db_session.commit()
        
        # Update invoice status using InvoiceStatusService
        status_service.update_invoice_status(
            invoice_id=invoice.id,
            organization_id=organization_id,
        )
        
        # Refresh invoice to get updated outstanding_amount and status
        db_session.refresh(invoice)
        
        # Verify outstanding_amount = $300, status = "partial"
        assert invoice.outstanding_amount == Decimal("300.00"), f"After $700 total payments, outstanding_amount should be $300.00, got {invoice.outstanding_amount}"
        assert invoice.status == "partial", f"After partial payment, status should be 'partial', got {invoice.status}"
        
        print(f"✓ Second payment: $400 allocated")
        print(f"  - Invoice status: {invoice.status}")
        print(f"  - Outstanding amount: ${invoice.outstanding_amount}")
        
        # Step 5: Create and allocate third payment $300 (final payment)
        payment3 = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-PARTIAL-003",
            payment_type="Customer_Payment",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=hdfc_bank_account.id,
            amount=Decimal("300.00"),
            currency_code="USD",
            payment_date=datetime.now(UTC),
            status="Confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment3)
        db_session.commit()
        db_session.refresh(payment3)
        
        # Create journal entry for payment3
        journal_service.post_payment_journal_entry(
            payment_entry=payment3,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        # Allocate payment3 to invoice
        payment_reference3 = PaymentReference(
            organization_id=organization_id,
            payment_id=payment3.id,
            invoice_id=invoice.id,
            allocated_amount=Decimal("300.00"),
            created_by=user_id,
        )
        db_session.add(payment_reference3)
        db_session.commit()
        
        # Update invoice status using InvoiceStatusService
        status_service.update_invoice_status(
            invoice_id=invoice.id,
            organization_id=organization_id,
        )
        
        # Refresh invoice to get updated outstanding_amount and status
        db_session.refresh(invoice)
        
        # Verify outstanding_amount = $0, status = "paid"
        assert invoice.outstanding_amount == Decimal("0.00"), f"After full payment ($1000 total), outstanding_amount should be $0.00, got {invoice.outstanding_amount}"
        assert invoice.status == "paid", f"After full payment, status should be 'paid', got {invoice.status}"
        
        print(f"✓ Third payment: $300 allocated")
        print(f"  - Invoice status: {invoice.status}")
        print(f"  - Outstanding amount: ${invoice.outstanding_amount}")
        
        # Step 6: Verify all payment allocations exist
        all_payment_references = (
            db_session.query(PaymentReference)
            .filter(
                PaymentReference.organization_id == organization_id,
                PaymentReference.invoice_id == invoice.id,
            )
            .all()
        )
        
        assert len(all_payment_references) == 3, f"Expected 3 payment references, found {len(all_payment_references)}"
        
        # Verify total allocated amount
        total_allocated = sum(ref.allocated_amount for ref in all_payment_references)
        assert total_allocated == Decimal("1000.00"), f"Total allocated should be $1000.00, got {total_allocated}"
        
        # Step 7: Verify all journal entries created correctly
        all_journal_entries = (
            db_session.query(JournalEntry)
            .filter(JournalEntry.organization_id == organization_id)
            .all()
        )
        
        # Should have 4 journal entries: 1 for invoice + 3 for payments
        assert len(all_journal_entries) == 4, f"Expected 4 journal entries (1 invoice + 3 payments), found {len(all_journal_entries)}"
        
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
        
        print("\n✓ Partial payment flow test passed successfully")
        print(f"  - Invoice {invoice.invoice_no} created with grand_total $1000.00")
        print(f"  - Invoice confirmed → outstanding_amount: $1000.00, status: submitted")
        print(f"  - Payment 1: $300 → outstanding_amount: $700.00, status: partial")
        print(f"  - Payment 2: $400 → outstanding_amount: $300.00, status: partial")
        print(f"  - Payment 3: $300 → outstanding_amount: $0.00, status: paid")
        print(f"  - Total payments: ${total_allocated}")
        print(f"  - All journal entries balanced (debits = credits)")
