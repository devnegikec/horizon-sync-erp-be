"""
Bug 1 Exploration Tests: Missing Invoice Journal Entries

These tests are EXPECTED TO FAIL on unfixed code to confirm the bug exists.
They test that confirming invoices (status "draft" → "submitted") should create
journal entries, set submitted_at timestamp, and initialize outstanding_amount.

**CRITICAL**: These tests encode the expected behavior and will validate the fix
when they pass after implementation. For now, they should fail to demonstrate
the bug exists.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.11**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceItem
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.base import AccountType, AccountStatus, InvoiceType
from app.services.invoice_service import InvoiceService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def setup_default_accounts(db_session, mock_current_user):
    """Create default accounts required for invoice journal entries"""
    org_id = mock_current_user.organization_id
    
    # Create GL accounts
    accounts = {
        "accounts_receivable": Account(
            id=uuid.uuid4(),
            account_code="1200",
            account_name="Accounts Receivable",
            account_type=AccountType.ASSET,
            organization_id=org_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        ),
        "accounts_payable": Account(
            id=uuid.uuid4(),
            account_code="2100",
            account_name="Accounts Payable",
            account_type=AccountType.LIABILITY,
            organization_id=org_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        ),
        "sales_revenue": Account(
            id=uuid.uuid4(),
            account_code="4000",
            account_name="Sales Revenue",
            account_type=AccountType.REVENUE,
            organization_id=org_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        ),
        "purchase_expense": Account(
            id=uuid.uuid4(),
            account_code="5000",
            account_name="Purchase Expense",
            account_type=AccountType.EXPENSE,
            organization_id=org_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        ),
    }
    
    for account in accounts.values():
        db_session.add(account)
    db_session.commit()
    
    # Create default account mappings
    default_accounts = {
        "accounts_receivable": DefaultAccount(
            id=uuid.uuid4(),
            organization_id=org_id,
            transaction_type="accounts_receivable",
            account_id=accounts["accounts_receivable"].id,
        ),
        "accounts_payable": DefaultAccount(
            id=uuid.uuid4(),
            organization_id=org_id,
            transaction_type="accounts_payable",
            account_id=accounts["accounts_payable"].id,
        ),
        "sales_revenue": DefaultAccount(
            id=uuid.uuid4(),
            organization_id=org_id,
            transaction_type="sales_revenue",
            account_id=accounts["sales_revenue"].id,
        ),
        "purchase_expense": DefaultAccount(
            id=uuid.uuid4(),
            organization_id=org_id,
            transaction_type="purchase_expense",
            account_id=accounts["purchase_expense"].id,
        ),
    }
    
    for default_account in default_accounts.values():
        db_session.add(default_account)
    db_session.commit()
    
    return accounts, default_accounts


# ============================================================================
# Bug 1 Exploration Tests - Sales Invoice
# ============================================================================

def test_sales_invoice_confirmation_creates_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_default_accounts
):
    """
    Test that confirming a sales invoice creates a journal entry with:
    - Debit: Accounts Receivable
    - Credit: Sales Revenue
    - Amount: Invoice grand_total
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (no journal entry created)
    **Validates: Requirement 2.1**
    """
    accounts, default_accounts = setup_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a draft sales invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no="INV-SALES-001",
        invoice_type=InvoiceType.SALES,
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("0.00"),
        currency="USD",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Confirm invoice using the service (which should create journal entry)
    from app.services.invoice_service import InvoiceService
    invoice_service = InvoiceService(db_session)
    invoice_service.confirm_invoice(invoice.id, org_id, mock_current_user.id)
    db_session.refresh(invoice)
    
    # Query for journal entries related to this invoice
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: Journal entry should exist (will FAIL on unfixed code)
    assert len(journal_entries) > 0, (
        f"Sales invoice {invoice.invoice_no} confirmed but no journal entry exists. "
        f"Expected journal entry with Debit AR, Credit Revenue."
    )
    
    journal_entry = journal_entries[0]
    
    # Verify journal entry lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry.id
    ).all()
    
    assert len(lines) == 2, f"Expected 2 journal entry lines, found {len(lines)}"
    
    # Find debit and credit lines
    debit_line = next((l for l in lines if l.debit > 0), None)
    credit_line = next((l for l in lines if l.credit > 0), None)
    
    assert debit_line is not None, "No debit line found in journal entry"
    assert credit_line is not None, "No credit line found in journal entry"
    
    # Verify debit line is Accounts Receivable
    assert debit_line.account_id == accounts["accounts_receivable"].id, (
        f"Debit line should be Accounts Receivable, "
        f"found account_id {debit_line.account_id}"
    )
    assert debit_line.debit == invoice.grand_total, (
        f"Debit amount should be {invoice.grand_total}, found {debit_line.debit}"
    )
    
    # Verify credit line is Sales Revenue
    assert credit_line.account_id == accounts["sales_revenue"].id, (
        f"Credit line should be Sales Revenue, "
        f"found account_id {credit_line.account_id}"
    )
    assert credit_line.credit == invoice.grand_total, (
        f"Credit amount should be {invoice.grand_total}, found {credit_line.credit}"
    )


def test_purchase_invoice_confirmation_creates_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_default_accounts
):
    """
    Test that confirming a purchase invoice creates a journal entry with:
    - Debit: Purchase Expense
    - Credit: Accounts Payable
    - Amount: Invoice grand_total
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (no journal entry created)
    **Validates: Requirement 2.2**
    """
    accounts, default_accounts = setup_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a draft purchase invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no="INV-PURCHASE-001",
        invoice_type=InvoiceType.PURCHASE,
        party_id=uuid.uuid4(),
        party_type="Supplier",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("500.00"),
        outstanding_amount=Decimal("0.00"),
        currency="USD",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Confirm invoice using the service (which should create journal entry)
    from app.services.invoice_service import InvoiceService
    invoice_service = InvoiceService(db_session)
    invoice_service.confirm_invoice(invoice.id, org_id, mock_current_user.id)
    db_session.refresh(invoice)
    
    # Query for journal entries related to this invoice
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: Journal entry should exist (will FAIL on unfixed code)
    assert len(journal_entries) > 0, (
        f"Purchase invoice {invoice.invoice_no} confirmed but no journal entry exists. "
        f"Expected journal entry with Debit Expense, Credit AP."
    )
    
    journal_entry = journal_entries[0]
    
    # Verify journal entry lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry.id
    ).all()
    
    assert len(lines) == 2, f"Expected 2 journal entry lines, found {len(lines)}"
    
    # Find debit and credit lines
    debit_line = next((l for l in lines if l.debit > 0), None)
    credit_line = next((l for l in lines if l.credit > 0), None)
    
    assert debit_line is not None, "No debit line found in journal entry"
    assert credit_line is not None, "No credit line found in journal entry"
    
    # Verify debit line is Purchase Expense
    assert debit_line.account_id == accounts["purchase_expense"].id, (
        f"Debit line should be Purchase Expense, "
        f"found account_id {debit_line.account_id}"
    )
    assert debit_line.debit == invoice.grand_total, (
        f"Debit amount should be {invoice.grand_total}, found {debit_line.debit}"
    )
    
    # Verify credit line is Accounts Payable
    assert credit_line.account_id == accounts["accounts_payable"].id, (
        f"Credit line should be Accounts Payable, "
        f"found account_id {credit_line.account_id}"
    )
    assert credit_line.credit == invoice.grand_total, (
        f"Credit amount should be {invoice.grand_total}, found {credit_line.credit}"
    )


def test_invoice_submitted_at_timestamp_set(
    db_session: Session,
    mock_current_user,
    setup_default_accounts
):
    """
    Test that invoice.submitted_at is set when status changes to "submitted"
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (submitted_at not set)
    **Validates: Requirement 2.4**
    """
    org_id = mock_current_user.organization_id
    
    # Create a draft sales invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no="INV-TIMESTAMP-001",
        invoice_type=InvoiceType.SALES,
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("750.00"),
        outstanding_amount=Decimal("0.00"),
        currency="USD",
        submitted_at=None,  # Initially None
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Verify submitted_at is None initially
    assert invoice.submitted_at is None, "submitted_at should be None for draft invoice"
    
    # Confirm invoice using the service (which should set submitted_at)
    from app.services.invoice_service import InvoiceService
    invoice_service = InvoiceService(db_session)
    invoice_service.confirm_invoice(invoice.id, org_id, mock_current_user.id)
    db_session.refresh(invoice)
    
    # ASSERTION: submitted_at should be set (will FAIL on unfixed code)
    assert invoice.submitted_at is not None, (
        f"Invoice {invoice.invoice_no} confirmed but submitted_at is still None. "
        f"Expected submitted_at to be set to current timestamp."
    )


def test_invoice_outstanding_amount_initialized(
    db_session: Session,
    mock_current_user,
    setup_default_accounts
):
    """
    Test that invoice.outstanding_amount equals grand_total after confirmation
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (outstanding_amount not initialized)
    **Validates: Requirement 2.11**
    """
    org_id = mock_current_user.organization_id
    
    # Create a draft sales invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no="INV-OUTSTANDING-001",
        invoice_type=InvoiceType.SALES,
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("1250.00"),
        outstanding_amount=Decimal("0.00"),  # Initially 0
        currency="USD",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Verify outstanding_amount is 0 initially
    assert invoice.outstanding_amount == Decimal("0.00"), (
        "outstanding_amount should be 0 for draft invoice"
    )
    
    # Confirm invoice using the service (which should initialize outstanding_amount)
    from app.services.invoice_service import InvoiceService
    invoice_service = InvoiceService(db_session)
    invoice_service.confirm_invoice(invoice.id, org_id, mock_current_user.id)
    db_session.refresh(invoice)
    
    # ASSERTION: outstanding_amount should equal grand_total (will FAIL on unfixed code)
    assert invoice.outstanding_amount == invoice.grand_total, (
        f"Invoice {invoice.invoice_no} confirmed but outstanding_amount is "
        f"{invoice.outstanding_amount}, expected {invoice.grand_total}. "
        f"Outstanding amount should be initialized to grand_total on confirmation."
    )


# ============================================================================
# Property-Based Test: Invoice Confirmation Creates Journal Entry
# ============================================================================

@given(
    grand_total=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("999999.99"),
        places=2
    ),
    invoice_type=st.sampled_from([InvoiceType.SALES, InvoiceType.PURCHASE])
)
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_property_invoice_confirmation_creates_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_default_accounts,
    grand_total: Decimal,
    invoice_type: InvoiceType
):
    """
    Property-Based Test: For any invoice with valid grand_total and invoice_type,
    confirming the invoice should create a journal entry with correct debits and credits.
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code (no journal entries created)
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.11**
    """
    accounts, default_accounts = setup_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a draft invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        organization_id=org_id,
        invoice_no=f"INV-PBT-{uuid.uuid4().hex[:8].upper()}",
        invoice_type=invoice_type,
        party_id=uuid.uuid4(),
        party_type="Customer" if invoice_type == InvoiceType.SALES else "Supplier",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=grand_total,
        outstanding_amount=Decimal("0.00"),
        currency="USD",
        submitted_at=None,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    
    # Confirm invoice using the service
    from app.services.invoice_service import InvoiceService
    invoice_service = InvoiceService(db_session)
    invoice_service.confirm_invoice(invoice.id, org_id, mock_current_user.id)
    
    # Query for journal entries
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "Invoice",
        JournalEntry.reference_id == invoice.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # Property 1: Journal entry exists
    assert len(journal_entries) > 0, (
        f"Invoice {invoice.invoice_no} (type={invoice_type.value}, "
        f"grand_total={grand_total}) confirmed but no journal entry created"
    )
    
    journal_entry = journal_entries[0]
    
    # Property 2: Journal entry has exactly 2 lines (debit and credit)
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry.id
    ).all()
    assert len(lines) == 2, (
        f"Expected 2 journal entry lines for invoice {invoice.invoice_no}, "
        f"found {len(lines)}"
    )
    
    # Property 3: Debits equal credits
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    assert total_debit == total_credit == grand_total, (
        f"Debits ({total_debit}) and credits ({total_credit}) should equal "
        f"grand_total ({grand_total})"
    )
    
    # Property 4: Correct accounts used based on invoice type
    debit_line = next((l for l in lines if l.debit > 0), None)
    credit_line = next((l for l in lines if l.credit > 0), None)
    
    if invoice_type == InvoiceType.SALES:
        assert debit_line.account_id == accounts["accounts_receivable"].id, (
            f"Sales invoice should debit Accounts Receivable"
        )
        assert credit_line.account_id == accounts["sales_revenue"].id, (
            f"Sales invoice should credit Sales Revenue"
        )
    else:  # PURCHASE
        assert debit_line.account_id == accounts["purchase_expense"].id, (
            f"Purchase invoice should debit Purchase Expense"
        )
        assert credit_line.account_id == accounts["accounts_payable"].id, (
            f"Purchase invoice should credit Accounts Payable"
        )
    
    # Property 5: submitted_at is set
    assert invoice.submitted_at is not None, (
        f"Invoice {invoice.invoice_no} confirmed but submitted_at is None"
    )
    
    # Property 6: outstanding_amount equals grand_total
    assert invoice.outstanding_amount == grand_total, (
        f"Invoice {invoice.invoice_no} outstanding_amount ({invoice.outstanding_amount}) "
        f"should equal grand_total ({grand_total})"
    )
    
    # Cleanup for next iteration
    db_session.delete(invoice)
    for line in lines:
        db_session.delete(line)
    db_session.delete(journal_entry)
    db_session.commit()
