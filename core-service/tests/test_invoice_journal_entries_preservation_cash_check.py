"""
Phase 2 Preservation Tests: Cash and Check Payment Flows

These tests verify that existing payment flows (Cash, Check) remain unchanged
after the fix. These tests should PASS on UNFIXED code to confirm baseline
behavior that must be preserved.

**CRITICAL**: These tests encode the expected preservation behavior. They should
pass on both unfixed and fixed code to ensure no regression.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session

from app.models.payment_entry import PaymentEntry
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.base import (
    AccountType,
    AccountStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
)
from app.services.journal_posting_service import JournalPostingService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def setup_payment_default_accounts(db_session, mock_current_user):
    """Create default accounts required for payment journal entries"""
    org_id = mock_current_user.organization_id
    
    # Create GL accounts
    accounts = {
        "cash": Account(
            id=uuid.uuid4(),
            account_code="1100",
            account_name="Cash",
            account_type=AccountType.ASSET,
            organization_id=org_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        ),
        "checks_received": Account(
            id=uuid.uuid4(),
            account_code="1150",
            account_name="Checks Received",
            account_type=AccountType.ASSET,
            organization_id=org_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        ),
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
    }
    
    for account in accounts.values():
        db_session.add(account)
    db_session.commit()
    
    # Create default account mappings
    default_accounts = {
        "cash": DefaultAccount(
            id=uuid.uuid4(),
            organization_id=org_id,
            transaction_type="cash",
            account_id=accounts["cash"].id,
        ),
        "checks_received": DefaultAccount(
            id=uuid.uuid4(),
            organization_id=org_id,
            transaction_type="checks_received",
            account_id=accounts["checks_received"].id,
        ),
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
    }
    
    for default_account in default_accounts.values():
        db_session.add(default_account)
    db_session.commit()
    
    return accounts, default_accounts


@pytest.fixture
def sample_customer(db_session, mock_current_user):
    """Create a sample customer for testing"""
    customer = Customer(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        customer_name="Test Customer",
        customer_code="CUST-001",
        email="customer@example.com",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def sample_supplier(db_session, mock_current_user):
    """Create a sample supplier for testing"""
    supplier = Supplier(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        supplier_name="Test Supplier",
        supplier_code="SUPP-001",
        email="supplier@example.com",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(supplier)
    db_session.commit()
    return supplier


# ============================================================================
# Customer Payment Tests (Cash and Check)
# ============================================================================

def test_customer_payment_cash_creates_correct_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_payment_default_accounts,
    sample_customer,
):
    """
    Test that customer payment with payment_mode "Cash" creates journal entry:
    - Debit: Cash default account
    - Credit: Accounts Receivable
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.1**
    """
    accounts, default_accounts = setup_payment_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a customer payment with Cash mode
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_customer.id,
        amount=Decimal("500.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no="CASH-001",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Post journal entry using JournalPostingService
    service = JournalPostingService(db_session)
    journal_entry_result = service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query for journal entries related to this payment
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "PaymentEntry",
        JournalEntry.reference_id == payment.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: Journal entry should exist
    assert len(journal_entries) > 0, (
        f"Customer payment {payment.reference_no} with Cash mode should create journal entry"
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
    
    # Verify debit line is Cash account
    assert debit_line.account_id == accounts["cash"].id, (
        f"Customer Cash payment should debit Cash account, "
        f"found account_id {debit_line.account_id}"
    )
    assert debit_line.debit == payment.amount, (
        f"Debit amount should be {payment.amount}, found {debit_line.debit}"
    )
    
    # Verify credit line is Accounts Receivable
    assert credit_line.account_id == accounts["accounts_receivable"].id, (
        f"Customer Cash payment should credit Accounts Receivable, "
        f"found account_id {credit_line.account_id}"
    )
    assert credit_line.credit == payment.amount, (
        f"Credit amount should be {payment.amount}, found {credit_line.credit}"
    )


def test_customer_payment_check_creates_correct_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_payment_default_accounts,
    sample_customer,
):
    """
    Test that customer payment with payment_mode "Check" creates journal entry:
    - Debit: Checks Received default account
    - Credit: Accounts Receivable
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.2**
    """
    accounts, default_accounts = setup_payment_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a customer payment with Check mode
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        payment_mode=PaymentMode.CHECK,
        party_id=sample_customer.id,
        amount=Decimal("750.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no="CHK-001",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Post journal entry using JournalPostingService
    service = JournalPostingService(db_session)
    journal_entry_result = service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query for journal entries related to this payment
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "PaymentEntry",
        JournalEntry.reference_id == payment.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: Journal entry should exist
    assert len(journal_entries) > 0, (
        f"Customer payment {payment.reference_no} with Check mode should create journal entry"
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
    
    # Verify debit line is Checks Received account
    assert debit_line.account_id == accounts["checks_received"].id, (
        f"Customer Check payment should debit Checks Received account, "
        f"found account_id {debit_line.account_id}"
    )
    assert debit_line.debit == payment.amount, (
        f"Debit amount should be {payment.amount}, found {debit_line.debit}"
    )
    
    # Verify credit line is Accounts Receivable
    assert credit_line.account_id == accounts["accounts_receivable"].id, (
        f"Customer Check payment should credit Accounts Receivable, "
        f"found account_id {credit_line.account_id}"
    )
    assert credit_line.credit == payment.amount, (
        f"Credit amount should be {payment.amount}, found {credit_line.credit}"
    )


# ============================================================================
# Supplier Payment Tests (Cash and Check)
# ============================================================================

def test_supplier_payment_cash_creates_correct_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_payment_default_accounts,
    sample_supplier,
):
    """
    Test that supplier payment with payment_mode "Cash" creates journal entry:
    - Debit: Accounts Payable
    - Credit: Cash default account
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.3**
    """
    accounts, default_accounts = setup_payment_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a supplier payment with Cash mode
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
        payment_mode=PaymentMode.CASH,
        party_id=sample_supplier.id,
        amount=Decimal("300.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no="CASH-SUPP-001",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Post journal entry using JournalPostingService
    service = JournalPostingService(db_session)
    journal_entry_result = service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query for journal entries related to this payment
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "PaymentEntry",
        JournalEntry.reference_id == payment.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: Journal entry should exist
    assert len(journal_entries) > 0, (
        f"Supplier payment {payment.reference_no} with Cash mode should create journal entry"
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
    
    # Verify debit line is Accounts Payable
    assert debit_line.account_id == accounts["accounts_payable"].id, (
        f"Supplier Cash payment should debit Accounts Payable, "
        f"found account_id {debit_line.account_id}"
    )
    assert debit_line.debit == payment.amount, (
        f"Debit amount should be {payment.amount}, found {debit_line.debit}"
    )
    
    # Verify credit line is Cash account
    assert credit_line.account_id == accounts["cash"].id, (
        f"Supplier Cash payment should credit Cash account, "
        f"found account_id {credit_line.account_id}"
    )
    assert credit_line.credit == payment.amount, (
        f"Credit amount should be {payment.amount}, found {credit_line.credit}"
    )


def test_supplier_payment_check_creates_correct_journal_entry(
    db_session: Session,
    mock_current_user,
    setup_payment_default_accounts,
    sample_supplier,
):
    """
    Test that supplier payment with payment_mode "Check" creates journal entry:
    - Debit: Accounts Payable
    - Credit: Checks Received default account
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirement 3.4**
    """
    accounts, default_accounts = setup_payment_default_accounts
    org_id = mock_current_user.organization_id
    
    # Create a supplier payment with Check mode
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
        payment_mode=PaymentMode.CHECK,
        party_id=sample_supplier.id,
        amount=Decimal("450.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no="CHK-SUPP-001",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Post journal entry using JournalPostingService
    service = JournalPostingService(db_session)
    journal_entry_result = service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query for journal entries related to this payment
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "PaymentEntry",
        JournalEntry.reference_id == payment.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # ASSERTION: Journal entry should exist
    assert len(journal_entries) > 0, (
        f"Supplier payment {payment.reference_no} with Check mode should create journal entry"
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
    
    # Verify debit line is Accounts Payable
    assert debit_line.account_id == accounts["accounts_payable"].id, (
        f"Supplier Check payment should debit Accounts Payable, "
        f"found account_id {debit_line.account_id}"
    )
    assert debit_line.debit == payment.amount, (
        f"Debit amount should be {payment.amount}, found {debit_line.debit}"
    )
    
    # Verify credit line is Checks Received account
    assert credit_line.account_id == accounts["checks_received"].id, (
        f"Supplier Check payment should credit Checks Received account, "
        f"found account_id {credit_line.account_id}"
    )
    assert credit_line.credit == payment.amount, (
        f"Credit amount should be {payment.amount}, found {credit_line.credit}"
    )


# ============================================================================
# Property-Based Test: Cash and Check Payments Use Correct Accounts
# ============================================================================

@given(
    amount=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("99999.99"),
        places=2
    ),
    payment_mode=st.sampled_from([PaymentMode.CASH, PaymentMode.CHECK]),
    payment_type=st.sampled_from([
        PaymentEntryType.CUSTOMER_PAYMENT,
        PaymentEntryType.SUPPLIER_PAYMENT
    ])
)
@settings(
    max_examples=5,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None
)
def test_property_cash_check_payments_use_appropriate_accounts(
    db_session: Session,
    mock_current_user,
    setup_payment_default_accounts,
    sample_customer,
    sample_supplier,
    amount: Decimal,
    payment_mode: PaymentMode,
    payment_type: PaymentEntryType
):
    """
    Property-Based Test: For all payments with payment_mode in ["Cash", "Check"],
    journal entries use appropriate default accounts.
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (preservation test)
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """
    accounts, default_accounts = setup_payment_default_accounts
    org_id = mock_current_user.organization_id
    
    # Select party based on payment type
    party_id = sample_customer.id if payment_type == PaymentEntryType.CUSTOMER_PAYMENT else sample_supplier.id
    
    # Create payment
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=payment_type,
        payment_mode=payment_mode,
        party_id=party_id,
        amount=amount,
        currency_code="USD",
        payment_date=datetime.now(UTC),
        reference_no=f"PBT-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentEntryStatus.CONFIRMED,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Post journal entry
    service = JournalPostingService(db_session)
    journal_entry_result = service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query for journal entries
    journal_entries = db_session.query(JournalEntry).filter(
        JournalEntry.reference_type == "PaymentEntry",
        JournalEntry.reference_id == payment.id,
        JournalEntry.organization_id == org_id
    ).all()
    
    # Property 1: Journal entry exists
    assert len(journal_entries) > 0, (
        f"Payment {payment.reference_no} (mode={payment_mode.value}, "
        f"type={payment_type.value}, amount={amount}) should create journal entry"
    )
    
    journal_entry = journal_entries[0]
    
    # Property 2: Journal entry has exactly 2 lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry.id
    ).all()
    assert len(lines) == 2, (
        f"Expected 2 journal entry lines for payment {payment.reference_no}, "
        f"found {len(lines)}"
    )
    
    # Property 3: Debits equal credits
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    assert total_debit == total_credit == amount, (
        f"Debits ({total_debit}) and credits ({total_credit}) should equal "
        f"amount ({amount})"
    )
    
    # Property 4: Correct accounts used based on payment mode and type
    debit_line = next((l for l in lines if l.debit > 0), None)
    credit_line = next((l for l in lines if l.credit > 0), None)
    
    # Determine expected accounts
    if payment_type == PaymentEntryType.CUSTOMER_PAYMENT:
        # Customer payment: Debit payment account, Credit AR
        if payment_mode == PaymentMode.CASH:
            expected_debit_account = accounts["cash"].id
        else:  # CHECK
            expected_debit_account = accounts["checks_received"].id
        expected_credit_account = accounts["accounts_receivable"].id
        
        assert debit_line.account_id == expected_debit_account, (
            f"Customer {payment_mode.value} payment should debit "
            f"{'Cash' if payment_mode == PaymentMode.CASH else 'Checks Received'} account"
        )
        assert credit_line.account_id == expected_credit_account, (
            f"Customer payment should credit Accounts Receivable"
        )
    else:  # SUPPLIER_PAYMENT
        # Supplier payment: Debit AP, Credit payment account
        expected_debit_account = accounts["accounts_payable"].id
        if payment_mode == PaymentMode.CASH:
            expected_credit_account = accounts["cash"].id
        else:  # CHECK
            expected_credit_account = accounts["checks_received"].id
        
        assert debit_line.account_id == expected_debit_account, (
            f"Supplier payment should debit Accounts Payable"
        )
        assert credit_line.account_id == expected_credit_account, (
            f"Supplier {payment_mode.value} payment should credit "
            f"{'Cash' if payment_mode == PaymentMode.CASH else 'Checks Received'} account"
        )
    
    # Cleanup for next iteration
    db_session.delete(payment)
    for line in lines:
        db_session.delete(line)
    db_session.delete(journal_entry)
    db_session.commit()
