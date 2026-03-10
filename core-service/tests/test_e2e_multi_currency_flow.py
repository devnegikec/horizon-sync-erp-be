"""End-to-end integration test for multi-currency invoice and payment flow

Tests the complete multi-currency invoice lifecycle:
1. Create sales invoice in EUR with grand_total €800
2. Confirm invoice → Verify journal entry uses base currency (USD) amount
3. Create payment in EUR with bank_account_id
4. Allocate payment → Verify outstanding_amount calculated correctly in base currency

**Validates: Requirements 2.1, 2.5, 2.12**
"""

import uuid
from datetime import datetime, UTC, date
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
from app.models.exchange_rate import ExchangeRate
from app.models.system_config import SystemConfig
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
def base_currency_config(db_session):
    """Configure USD as base currency"""
    config = SystemConfig(
        key="base_currency",
        value="USD",
        updated_by="test_user",
    )
    db_session.add(config)
    db_session.commit()
    return config


@pytest.fixture
def eur_to_usd_exchange_rate(db_session):
    """Create EUR to USD exchange rate (1 EUR = 1.10 USD)"""
    rate = ExchangeRate(
        from_currency="EUR",
        to_currency="USD",
        rate=Decimal("1.10"),
        effective_date=date.today(),
    )
    db_session.add(rate)
    db_session.commit()
    db_session.refresh(rate)
    return rate


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
    """Create bank GL account for EUR bank"""
    account = Account(
        organization_id=organization_id,
        account_code="1015",
        account_name="EUR Bank Account",
        account_type=AccountType.ASSET,
        currency="USD",  # GL accounts are in base currency
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
def eur_bank_account(db_session, organization_id, bank_gl_account):
    """Create EUR bank account linked to GL account"""
    bank_account = BankAccount(
        organization_id=organization_id,
        bank_name="Deutsche Bank",
        account_number="DE89370400440532013000",
        account_holder_name="Test Company",
        branch_name="Frankfurt Branch",
        ifsc_code="DEUTDEFF",
        country_code="DE",
        currency="EUR",  # Bank account holds EUR
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


class TestEndToEndMultiCurrencyFlow:
    """End-to-end integration test for multi-currency invoice and payment flow
    
    **Validates: Requirements 2.1, 2.5, 2.12**
    """

    def test_multi_currency_invoice_and_payment_flow(
        self,
        db_session,
        client_with_auth,
        organization_id,
        user_id,
        customer_id,
        base_currency_config,
        eur_to_usd_exchange_rate,
        default_accounts,
        eur_bank_account,
        accounts_receivable_account,
        sales_revenue_account,
        bank_gl_account,
    ):
        """Test multi-currency invoice and payment flow with currency conversion
        
        Flow:
        1. Create sales invoice in EUR with grand_total €800
        2. Confirm invoice → Verify journal entry uses base currency (USD) amount
        3. Create payment in EUR with bank_account_id
        4. Allocate payment → Verify outstanding_amount calculated correctly in base currency
        
        Exchange rate: 1 EUR = 1.10 USD
        Invoice: €800 = $880 USD
        Payment: €800 = $880 USD
        
        **Validates: Requirements 2.1, 2.5, 2.12**
        """
        
        # Step 1: Create sales invoice in EUR with grand_total €800
        invoice = Invoice(
            organization_id=organization_id,
            invoice_no="INV-EUR-001",
            invoice_type="sales",
            party_id=customer_id,
            party_type="Customer",
            posting_date=datetime.now(UTC),
            status="draft",
            grand_total=Decimal("800.00"),  # €800
            currency="EUR",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        
        assert invoice.status == "draft"
        assert invoice.currency == "EUR"
        assert invoice.grand_total == Decimal("800.00")
        
        # Step 2: Confirm invoice via API
        response = client_with_auth.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200, f"Invoice confirmation failed: {response.text}"
        
        # Refresh invoice to get updated data
        db_session.refresh(invoice)
        
        # Verify invoice status and fields updated
        assert invoice.status == "submitted", "Invoice status should be 'submitted'"
        assert invoice.submitted_at is not None, "submitted_at should be set"
        
        # Outstanding amount should be in base currency (USD)
        # €800 * 1.10 = $880
        expected_usd_amount = Decimal("880.00")
        assert invoice.outstanding_amount == expected_usd_amount, (
            f"outstanding_amount should be {expected_usd_amount} USD (converted from €800), "
            f"got {invoice.outstanding_amount}"
        )
        
        # Step 3: Verify journal entry created with base currency amounts
        invoice_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "Invoice",
                JournalEntry.reference_id == invoice.id,
            )
            .all()
        )
        
        assert len(invoice_journal_entries) == 1, (
            f"Expected 1 journal entry for invoice, found {len(invoice_journal_entries)}"
        )
        invoice_je = invoice_journal_entries[0]
        
        # Verify journal entry lines for invoice
        invoice_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == invoice_je.id)
            .all()
        )
        
        assert len(invoice_je_lines) == 2, (
            f"Expected 2 journal entry lines, found {len(invoice_je_lines)}"
        )
        
        # Find debit and credit lines
        debit_line = next((line for line in invoice_je_lines if line.debit > 0), None)
        credit_line = next((line for line in invoice_je_lines if line.credit > 0), None)
        
        assert debit_line is not None, "Debit line not found"
        assert credit_line is not None, "Credit line not found"
        
        # Verify journal entry uses base currency (USD) amounts
        # €800 * 1.10 = $880
        assert debit_line.account_id == accounts_receivable_account.id, (
            "Debit should be to Accounts Receivable"
        )
        assert debit_line.debit == expected_usd_amount, (
            f"Debit amount should be {expected_usd_amount} USD (converted from €800), "
            f"got {debit_line.debit}"
        )
        
        assert credit_line.account_id == sales_revenue_account.id, (
            "Credit should be to Sales Revenue"
        )
        assert credit_line.credit == expected_usd_amount, (
            f"Credit amount should be {expected_usd_amount} USD (converted from €800), "
            f"got {credit_line.credit}"
        )
        
        # Verify debits equal credits
        total_debits = sum(line.debit for line in invoice_je_lines)
        total_credits = sum(line.credit for line in invoice_je_lines)
        assert total_debits == total_credits, (
            f"Debits ({total_debits}) should equal credits ({total_credits})"
        )
        
        # Step 4: Create customer payment in EUR with bank_account_id
        payment = PaymentEntry(
            organization_id=organization_id,
            reference_no="PAY-EUR-001",
            payment_type="Customer_Payment",
            party_id=customer_id,
            payment_mode="Bank_Transfer",
            bank_account_id=eur_bank_account.id,
            amount=Decimal("800.00"),  # €800
            currency_code="EUR",
            payment_date=datetime.now(UTC),
            status="Confirmed",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        
        assert payment.bank_account_id == eur_bank_account.id, (
            "Payment should have bank_account_id set"
        )
        assert payment.currency_code == "EUR"
        assert payment.amount == Decimal("800.00")
        
        # Step 5: Verify journal entry created for payment with base currency amounts
        payment_journal_entries = (
            db_session.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.reference_type == "PaymentEntry",
                JournalEntry.reference_id == payment.id,
            )
            .all()
        )
        
        assert len(payment_journal_entries) == 1, (
            f"Expected 1 journal entry for payment, found {len(payment_journal_entries)}"
        )
        payment_je = payment_journal_entries[0]
        
        # Verify journal entry lines for payment
        payment_je_lines = (
            db_session.query(JournalEntryLine)
            .filter(JournalEntryLine.journal_entry_id == payment_je.id)
            .all()
        )
        
        assert len(payment_je_lines) == 2, (
            f"Expected 2 journal entry lines for payment, found {len(payment_je_lines)}"
        )
        
        # Find debit and credit lines for payment
        payment_debit_line = next((line for line in payment_je_lines if line.debit > 0), None)
        payment_credit_line = next((line for line in payment_je_lines if line.credit > 0), None)
        
        assert payment_debit_line is not None, "Payment debit line not found"
        assert payment_credit_line is not None, "Payment credit line not found"
        
        # Verify payment journal entry uses base currency (USD) amounts
        # €800 * 1.10 = $880
        assert payment_debit_line.account_id == bank_gl_account.id, (
            f"Debit should be to Bank GL Account (EUR Bank), "
            f"got account_id {payment_debit_line.account_id}"
        )
        assert payment_debit_line.debit == expected_usd_amount, (
            f"Debit amount should be {expected_usd_amount} USD (converted from €800), "
            f"got {payment_debit_line.debit}"
        )
        
        assert payment_credit_line.account_id == accounts_receivable_account.id, (
            "Credit should be to Accounts Receivable"
        )
        assert payment_credit_line.credit == expected_usd_amount, (
            f"Credit amount should be {expected_usd_amount} USD (converted from €800), "
            f"got {payment_credit_line.credit}"
        )
        
        # Verify debits equal credits for payment
        payment_total_debits = sum(line.debit for line in payment_je_lines)
        payment_total_credits = sum(line.credit for line in payment_je_lines)
        assert payment_total_debits == payment_total_credits, (
            f"Payment debits ({payment_total_debits}) should equal credits ({payment_total_credits})"
        )
        
        # Step 6: Allocate payment to invoice
        payment_reference = PaymentReference(
            organization_id=organization_id,
            payment_entry_id=payment.id,
            reference_type="Invoice",
            reference_id=invoice.id,
            allocated_amount=expected_usd_amount,  # Allocation in base currency (USD)
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(payment_reference)
        db_session.commit()
        
        # Refresh invoice to get updated outstanding_amount and status
        db_session.refresh(invoice)
        
        # Step 7: Verify outstanding_amount calculated correctly in base currency
        # After full payment: outstanding_amount should be $0
        assert invoice.outstanding_amount == Decimal("0.00"), (
            f"outstanding_amount should be 0.00 USD after full payment, "
            f"got {invoice.outstanding_amount}"
        )
        assert invoice.status == "paid", (
            f"Invoice status should be 'paid' after full payment, got {invoice.status}"
        )
        
        # Step 8: Verify all journal entries are correct
        all_journal_entries = (
            db_session.query(JournalEntry)
            .filter(JournalEntry.organization_id == organization_id)
            .all()
        )
        
        assert len(all_journal_entries) == 2, (
            f"Expected 2 journal entries total (invoice + payment), "
            f"found {len(all_journal_entries)}"
        )
        
        # Verify each journal entry has debits equal credits
        for je in all_journal_entries:
            je_lines = (
                db_session.query(JournalEntryLine)
                .filter(JournalEntryLine.journal_entry_id == je.id)
                .all()
            )
            je_debits = sum(line.debit for line in je_lines)
            je_credits = sum(line.credit for line in je_lines)
            assert je_debits == je_credits, (
                f"Journal entry {je.id} debits ({je_debits}) should equal credits ({je_credits})"
            )
        
        print("✓ Multi-currency invoice and payment flow test passed successfully")
        print(f"  - Invoice {invoice.invoice_no} created in EUR (€800)")
        print(f"  - Invoice confirmed with currency conversion (€800 → ${expected_usd_amount})")
        print(f"  - Journal entry created: Debit AR ${debit_line.debit}, Credit Revenue ${credit_line.credit}")
        print(f"  - Payment {payment.reference_no} created in EUR (€800) with bank_account_id")
        print(f"  - Payment journal entry created: Debit Bank ${payment_debit_line.debit}, Credit AR ${payment_credit_line.credit}")
        print(f"  - Payment allocated to invoice in base currency (${expected_usd_amount})")
        print(f"  - Invoice status: {invoice.status}, outstanding_amount: ${invoice.outstanding_amount}")
        print(f"  - All journal entries balanced (debits = credits)")
        print(f"  - Exchange rate used: 1 EUR = 1.10 USD")
