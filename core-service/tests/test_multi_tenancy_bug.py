"""Test to demonstrate multi-tenancy isolation bug

This test demonstrates that the balance calculator does NOT filter by organization_id
when querying journal entries, which could lead to cross-organization data leakage.

The test creates accounts with the SAME account_id for two different organizations
and verifies whether the balance calculation includes entries from both organizations.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.base import AccountStatus, AccountType, JournalStatus
from app.models.chart_of_account import Account
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.services.balance_calculator import BalanceCalculator


def test_multi_tenancy_bug_same_account_id(db_session):
    """
    Test that demonstrates the multi-tenancy bug when accounts have the same ID
    
    This test creates two accounts with the SAME UUID for different organizations
    (which shouldn't happen in practice due to UUID uniqueness, but demonstrates
    the lack of organization_id filtering in the balance calculator query).
    """
    # Create two separate organizations
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Use a shared account ID to demonstrate the bug
    shared_account_id = uuid.uuid4()
    
    # Create account for Organization A with shared ID
    cash_a = Account(
        id=shared_account_id,  # Explicitly set the ID
        account_code="1110-A",
        account_name="Cash - Org A",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=org_a_id,
        created_by=str(user_id),
        updated_by=str(user_id),
    )
    
    db_session.add(cash_a)
    db_session.commit()
    db_session.refresh(cash_a)
    
    # Create journal entry for Organization A (Debit Cash 1000)
    journal_a = JournalEntry(
        organization_id=org_a_id,
        entry_no="JE-ORG-A-001",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=Decimal("1000.00"),
        total_credit=Decimal("1000.00"),
        remarks="Entry for Organization A",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(journal_a)
    db_session.flush()
    
    line_a = JournalEntryLine(
        organization_id=org_a_id,
        journal_entry_id=journal_a.id,
        account_id=shared_account_id,
        debit=Decimal("1000.00"),
        credit=Decimal("0.00"),
        sort_order=1,
    )
    db_session.add(line_a)
    
    # Create journal entry for Organization B using the SAME account_id
    # (This simulates the bug where organization_id is not filtered)
    journal_b = JournalEntry(
        organization_id=org_b_id,
        entry_no="JE-ORG-B-001",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=Decimal("2000.00"),
        total_credit=Decimal("2000.00"),
        remarks="Entry for Organization B",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(journal_b)
    db_session.flush()
    
    line_b = JournalEntryLine(
        organization_id=org_b_id,
        journal_entry_id=journal_b.id,
        account_id=shared_account_id,  # Same account_id as Org A
        debit=Decimal("2000.00"),
        credit=Decimal("0.00"),
        sort_order=1,
    )
    db_session.add(line_b)
    db_session.commit()
    
    # Calculate balance for the shared account
    calculator = BalanceCalculator(db_session)
    balance = calculator.calculate_balance(shared_account_id, use_cache=False)
    
    # FIXED: The balance calculator NOW filters by organization_id
    # So it will only sum entries from the account's organization
    # Expected (correct): 1000.00 (only Org A's entry)
    # Actual (after fix): 1000.00 (only Org A's entry)
    
    print(f"Balance debit_total: {balance['debit_total']}")
    print(f"Balance balance: {balance['balance']}")
    
    # After the fix, the balance should only include Org A's entry
    assert balance["debit_total"] == 1000.00, "Balance should only include entries from the account's organization"
    assert balance["balance"] == 1000.00, "Balance calculation should filter by organization_id"
