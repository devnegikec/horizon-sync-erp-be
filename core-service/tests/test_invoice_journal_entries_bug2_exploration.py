"""
Bug 2 Exploration Tests: Generic Bank Account Usage

These tests are EXPECTED TO FAIL on unfixed code to confirm the bug exists.
They test that payments with payment_mode "Bank_Transfer" and bank_account_id
should use the specific bank account's gl_account_id instead of the generic
"bank" default account.

**CRITICAL**: These tests encode the expected behavior and will validate the fix
when they pass after implementation. For now, they should fail to demonstrate
the bug exists.

**EXPECTED FAILURES**:
1. PaymentEntry model has no bank_account_id field (AttributeError)
2. Journal entries use generic "bank" account instead of specific bank account's gl_account_id

**Validates: Requirements 2.5, 2.6, 2.7**
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session

from app.models.payment_entry import PaymentEntry
from app.models.bank_account import BankAccount
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.base import (
    AccountType,
    AccountStatus,
    PaymentEntryType,
    PaymentMode,
    PaymentEntryStatus,
    PaymentSource,
)
from app.services.journal_posting_service import JournalPostingService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def setup_bank_accounts_and_defaults(db_session, mock_current_user):
    """Create bank accounts with GL accounts and default accounts"""
    org_id = mock_current_user.organization_id
    
    # Create GL accounts for bank accounts
    hdfc_gl_account = Account(
        id=uuid.uuid4(),
        account_code="1010",
        account_name="HDFC Bank Account",
        account_type=AccountType.ASSET,
        organization_id=org_id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    
    icici_gl_account = Account(
        id=uuid.uuid4(),
        account_code="1020",
        account_name="ICICI Bank Account",
        account_type=AccountType.ASSET,
        organization_id=org_id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    
    # Create generic bank GL account (for default account)
    generic_bank_gl_account = Account(
        id=uuid.uuid4(),
        account_code="1000",
        account_name="Bank (Generic)",
        account_type=AccountType.ASSET,
        organization_id=org_id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    
    # Create AR and AP accounts
    ar_account = Account(
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
    )
    
    ap_account = Account(
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
    )
    
    db_session.add_all([
        hdfc_gl_account,
        icici_gl_account,
        generic_bank_gl_account,
        ar_account,
        ap_account,
    ])
    db_session.commit()
    
    # Create bank accounts
    hdfc_bank = BankAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        gl_account_id=hdfc_gl_account.id,
        bank_name="HDFC Bank",
        account_holder_name="Test Company",
        account_number="1234567890",
        country_code="IN",
        currency="USD",
        is_active=True,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    
    icici_bank = BankAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        gl_account_id=icici_gl_account.id,
        bank_name="ICICI Bank",
        account_holder_name="Test Company",
        account_number="0987654321",
        country_code="IN",
        currency="USD",
        is_active=True,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    
    db_session.add_all([hdfc_bank, icici_bank])
    db_session.commit()
    
    # Create default accounts
    default_bank = DefaultAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        transaction_type="bank",
        account_id=generic_bank_gl_account.id,
    )
    
    default_ar = DefaultAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        transaction_type="accounts_receivable",
        account_id=ar_account.id,
    )
    
    default_ap = DefaultAccount(
        id=uuid.uuid4(),
        organization_id=org_id,
        transaction_type="accounts_payable",
        account_id=ap_account.id,
    )
    
    db_session.add_all([default_bank, default_ar, default_ap])
    db_session.commit()
    
    return {
        "hdfc_bank": hdfc_bank,
        "icici_bank": icici_bank,
        "hdfc_gl_account": hdfc_gl_account,
        "icici_gl_account": icici_gl_account,
        "generic_bank_gl_account": generic_bank_gl_account,
        "ar_account": ar_account,
        "ap_account": ap_account,
    }


# ============================================================================
# Bug 2 Exploration Tests - Customer Payment with Bank Account
# ============================================================================

def test_customer_payment_bank_transfer_uses_specific_bank_account(
    db_session: Session,
    mock_current_user,
    setup_bank_accounts_and_defaults
):
    """
    Test that customer payment with payment_mode "Bank_Transfer" and bank_account_id
    uses the specific bank account's gl_account_id instead of generic "bank" account.
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code because:
    1. PaymentEntry model has no bank_account_id field (AttributeError)
    2. Journal entry uses generic "bank" account instead of HDFC's gl_account_id
    
    **Validates: Requirements 2.5, 2.7**
    """
    accounts = setup_bank_accounts_and_defaults
    org_id = mock_current_user.organization_id
    hdfc_bank = accounts["hdfc_bank"]
    hdfc_gl_account = accounts["hdfc_gl_account"]
    generic_bank_gl_account = accounts["generic_bank_gl_account"]
    
    # Create a customer payment with Bank_Transfer mode
    # NOTE: In unfixed code, PaymentEntry has no bank_account_id field
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("1000.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="PAY-CUST-001",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    
    # Try to set bank_account_id (will fail on unfixed code)
    try:
        payment.bank_account_id = hdfc_bank.id
    except AttributeError as e:
        pytest.fail(
            f"PaymentEntry model has no bank_account_id field. "
            f"This is expected on unfixed code. Error: {e}"
        )
    
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Create journal entry for payment
    journal_posting_service = JournalPostingService(db_session)
    journal_entry = journal_posting_service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query journal entry lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry["id"]
    ).all()
    
    assert len(lines) == 2, f"Expected 2 journal entry lines, found {len(lines)}"
    
    # Find debit line (should be bank account)
    debit_line = next((l for l in lines if l.debit > 0), None)
    assert debit_line is not None, "No debit line found in journal entry"
    
    # ASSERTION: Debit line should use HDFC's gl_account_id, not generic bank account
    # This will FAIL on unfixed code because it uses generic_bank_gl_account.id
    assert debit_line.account_id == hdfc_gl_account.id, (
        f"Payment PAY-CUST-001 to HDFC account uses generic 'bank' account "
        f"(account_id={debit_line.account_id}) instead of HDFC's gl_account_id "
        f"({hdfc_gl_account.id}). Expected journal entry to debit HDFC Bank Account, "
        f"but found it debits {generic_bank_gl_account.account_name if debit_line.account_id == generic_bank_gl_account.id else 'unknown account'}."
    )


def test_supplier_payment_bank_transfer_uses_specific_bank_account(
    db_session: Session,
    mock_current_user,
    setup_bank_accounts_and_defaults
):
    """
    Test that supplier payment with payment_mode "Bank_Transfer" and bank_account_id
    uses the specific bank account's gl_account_id instead of generic "bank" account.
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code because:
    1. PaymentEntry model has no bank_account_id field (AttributeError)
    2. Journal entry uses generic "bank" account instead of ICICI's gl_account_id
    
    **Validates: Requirements 2.6, 2.7**
    """
    accounts = setup_bank_accounts_and_defaults
    org_id = mock_current_user.organization_id
    icici_bank = accounts["icici_bank"]
    icici_gl_account = accounts["icici_gl_account"]
    generic_bank_gl_account = accounts["generic_bank_gl_account"]
    
    # Create a supplier payment with Bank_Transfer mode
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.SUPPLIER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("500.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="PAY-SUPP-001",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    
    # Try to set bank_account_id (will fail on unfixed code)
    try:
        payment.bank_account_id = icici_bank.id
    except AttributeError as e:
        pytest.fail(
            f"PaymentEntry model has no bank_account_id field. "
            f"This is expected on unfixed code. Error: {e}"
        )
    
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Create journal entry for payment
    journal_posting_service = JournalPostingService(db_session)
    journal_entry = journal_posting_service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query journal entry lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry["id"]
    ).all()
    
    assert len(lines) == 2, f"Expected 2 journal entry lines, found {len(lines)}"
    
    # Find credit line (should be bank account)
    credit_line = next((l for l in lines if l.credit > 0), None)
    assert credit_line is not None, "No credit line found in journal entry"
    
    # ASSERTION: Credit line should use ICICI's gl_account_id, not generic bank account
    # This will FAIL on unfixed code because it uses generic_bank_gl_account.id
    assert credit_line.account_id == icici_gl_account.id, (
        f"Payment PAY-SUPP-001 from ICICI account uses generic 'bank' account "
        f"(account_id={credit_line.account_id}) instead of ICICI's gl_account_id "
        f"({icici_gl_account.id}). Expected journal entry to credit ICICI Bank Account, "
        f"but found it credits {generic_bank_gl_account.account_name if credit_line.account_id == generic_bank_gl_account.id else 'unknown account'}."
    )


def test_payment_without_bank_account_uses_generic_bank(
    db_session: Session,
    mock_current_user,
    setup_bank_accounts_and_defaults
):
    """
    Test that payment with payment_mode "Bank_Transfer" but NO bank_account_id
    falls back to generic "bank" default account (backward compatibility).
    
    **EXPECTED OUTCOME**: This test PASSES on unfixed code (expected behavior)
    
    **Validates: Requirement 2.8 (backward compatibility)**
    """
    accounts = setup_bank_accounts_and_defaults
    org_id = mock_current_user.organization_id
    generic_bank_gl_account = accounts["generic_bank_gl_account"]
    
    # Create a customer payment with Bank_Transfer mode but NO bank_account_id
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=PaymentEntryType.CUSTOMER_PAYMENT,
        party_id=uuid.uuid4(),
        amount=Decimal("750.00"),
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no="PAY-NO-BANK-001",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    # Note: bank_account_id is NOT set (or doesn't exist in unfixed code)
    
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Create journal entry for payment
    journal_posting_service = JournalPostingService(db_session)
    journal_entry = journal_posting_service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query journal entry lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry["id"]
    ).all()
    
    assert len(lines) == 2, f"Expected 2 journal entry lines, found {len(lines)}"
    
    # Find debit line (should be generic bank account)
    debit_line = next((l for l in lines if l.debit > 0), None)
    assert debit_line is not None, "No debit line found in journal entry"
    
    # ASSERTION: Should use generic bank account (this is expected behavior)
    assert debit_line.account_id == generic_bank_gl_account.id, (
        f"Payment without bank_account_id should use generic 'bank' account "
        f"({generic_bank_gl_account.id}), but found account_id={debit_line.account_id}"
    )


# ============================================================================
# Property-Based Test: Bank Transfer Payments Use Specific Bank Accounts
# ============================================================================

@given(
    amount=st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("99999.99"),
        places=2
    ),
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
def test_property_bank_transfer_uses_specific_bank_account(
    db_session: Session,
    mock_current_user,
    setup_bank_accounts_and_defaults,
    amount: Decimal,
    payment_type: PaymentEntryType
):
    """
    Property-Based Test: For any payment with payment_mode "Bank_Transfer" and
    bank_account_id, the journal entry should use the specific bank account's
    gl_account_id instead of the generic "bank" default account.
    
    **EXPECTED OUTCOME**: This test FAILS on unfixed code because:
    1. PaymentEntry model has no bank_account_id field
    2. Journal entries use generic "bank" account
    
    **Validates: Requirements 2.5, 2.6, 2.7**
    """
    accounts = setup_bank_accounts_and_defaults
    org_id = mock_current_user.organization_id
    hdfc_bank = accounts["hdfc_bank"]
    hdfc_gl_account = accounts["hdfc_gl_account"]
    generic_bank_gl_account = accounts["generic_bank_gl_account"]
    
    # Create payment with Bank_Transfer mode
    payment = PaymentEntry(
        id=uuid.uuid4(),
        organization_id=org_id,
        payment_type=payment_type,
        party_id=uuid.uuid4(),
        amount=amount,
        currency_code="USD",
        payment_date=datetime.now(UTC),
        payment_mode=PaymentMode.BANK_TRANSFER,
        reference_no=f"PAY-PBT-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentEntryStatus.CONFIRMED,
        source=PaymentSource.MANUAL,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    
    # Try to set bank_account_id (will fail on unfixed code)
    try:
        payment.bank_account_id = hdfc_bank.id
    except AttributeError:
        pytest.skip("PaymentEntry model has no bank_account_id field (expected on unfixed code)")
    
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    
    # Create journal entry
    journal_posting_service = JournalPostingService(db_session)
    journal_entry = journal_posting_service.post_payment_journal_entry(
        payment_entry=payment,
        organization_id=org_id,
        user_id=mock_current_user.id,
    )
    
    # Query journal entry lines
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry["id"]
    ).all()
    
    # Property 1: Journal entry has exactly 2 lines
    assert len(lines) == 2, f"Expected 2 journal entry lines, found {len(lines)}"
    
    # Property 2: Debits equal credits
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    assert total_debit == total_credit == amount, (
        f"Debits ({total_debit}) and credits ({total_credit}) should equal amount ({amount})"
    )
    
    # Property 3: Correct bank account used based on payment type
    if payment_type == PaymentEntryType.CUSTOMER_PAYMENT:
        # Customer payment: Debit should be specific bank account
        debit_line = next((l for l in lines if l.debit > 0), None)
        assert debit_line is not None, "No debit line found"
        
        assert debit_line.account_id == hdfc_gl_account.id, (
            f"Customer payment (amount={amount}) should debit HDFC Bank Account "
            f"({hdfc_gl_account.id}), but found account_id={debit_line.account_id}. "
            f"Using generic bank account instead of specific bank account."
        )
    else:  # SUPPLIER_PAYMENT
        # Supplier payment: Credit should be specific bank account
        credit_line = next((l for l in lines if l.credit > 0), None)
        assert credit_line is not None, "No credit line found"
        
        assert credit_line.account_id == hdfc_gl_account.id, (
            f"Supplier payment (amount={amount}) should credit HDFC Bank Account "
            f"({hdfc_gl_account.id}), but found account_id={credit_line.account_id}. "
            f"Using generic bank account instead of specific bank account."
        )
    
    # Cleanup for next iteration
    db_session.delete(payment)
    for line in lines:
        db_session.delete(line)
    db_session.query(JournalEntry).filter(
        JournalEntry.id == journal_entry["id"]
    ).delete()
    db_session.commit()
