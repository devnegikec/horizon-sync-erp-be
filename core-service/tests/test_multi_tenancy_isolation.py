"""Test multi-tenancy isolation for journal entries

This test verifies that journal entries are properly isolated by organization_id,
ensuring that balance calculations for one organization do not include journal
entries from another organization.

Validates Requirements 2.1, 2.2
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.base import AccountStatus, AccountType, JournalStatus
from app.models.chart_of_account import Account
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.services.balance_calculator import BalanceCalculator


def test_multi_tenancy_isolation(db_session):
    """Test that journal entries are isolated by organization_id"""
    # Create two separate organizations
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Create accounts for Organization A
    cash_a = Account(
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
    capital_a = Account(
        account_code="3100-A",
        account_name="Owner's Capital - Org A",
        account_type=AccountType.EQUITY,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=org_a_id,
        created_by=str(user_id),
        updated_by=str(user_id),
    )

    # Create accounts for Organization B
    cash_b = Account(
        account_code="1110-B",
        account_name="Cash - Org B",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=org_b_id,
        created_by=str(user_id),
        updated_by=str(user_id),
    )
    capital_b = Account(
        account_code="3100-B",
        account_name="Owner's Capital - Org B",
        account_type=AccountType.EQUITY,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=org_b_id,
        created_by=str(user_id),
        updated_by=str(user_id),
    )

    db_session.add_all([cash_a, capital_a, cash_b, capital_b])
    db_session.commit()
    db_session.refresh(cash_a)
    db_session.refresh(capital_a)
    db_session.refresh(cash_b)
    db_session.refresh(capital_b)

    # Create journal entry for Organization A (Debit Cash 1000, Credit Capital 1000)
    journal_a = JournalEntry(
        organization_id=org_a_id,
        entry_no="JE-ORG-A-001",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=Decimal("1000.00"),
        total_credit=Decimal("1000.00"),
        remarks="Opening balance for Organization A",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(journal_a)
    db_session.flush()

    line_a1 = JournalEntryLine(
        organization_id=org_a_id,
        journal_entry_id=journal_a.id,
        account_id=cash_a.id,
        debit=Decimal("1000.00"),
        credit=Decimal("0.00"),
        sort_order=1,
    )
    line_a2 = JournalEntryLine(
        organization_id=org_a_id,
        journal_entry_id=journal_a.id,
        account_id=capital_a.id,
        debit=Decimal("0.00"),
        credit=Decimal("1000.00"),
        sort_order=2,
    )
    db_session.add_all([line_a1, line_a2])

    # Create journal entry for Organization B (Debit Cash 2000, Credit Capital 2000)
    journal_b = JournalEntry(
        organization_id=org_b_id,
        entry_no="JE-ORG-B-001",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=Decimal("2000.00"),
        total_credit=Decimal("2000.00"),
        remarks="Opening balance for Organization B",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(journal_b)
    db_session.flush()

    line_b1 = JournalEntryLine(
        organization_id=org_b_id,
        journal_entry_id=journal_b.id,
        account_id=cash_b.id,
        debit=Decimal("2000.00"),
        credit=Decimal("0.00"),
        sort_order=1,
    )
    line_b2 = JournalEntryLine(
        organization_id=org_b_id,
        journal_entry_id=journal_b.id,
        account_id=capital_b.id,
        debit=Decimal("0.00"),
        credit=Decimal("2000.00"),
        sort_order=2,
    )
    db_session.add_all([line_b1, line_b2])
    db_session.commit()

    # Calculate balances for Organization A
    calculator = BalanceCalculator(db_session)
    balance_cash_a = calculator.calculate_balance(cash_a.id, use_cache=False)
    balance_capital_a = calculator.calculate_balance(capital_a.id, use_cache=False)

    # Calculate balances for Organization B
    balance_cash_b = calculator.calculate_balance(cash_b.id, use_cache=False)
    balance_capital_b = calculator.calculate_balance(capital_b.id, use_cache=False)

    # Verify Organization A balances (should only include org A entries)
    assert balance_cash_a is not None
    assert balance_cash_a["debit_total"] == 1000.00
    assert balance_cash_a["credit_total"] == 0.00
    assert balance_cash_a["balance"] == 1000.00  # Asset: Debit - Credit

    assert balance_capital_a is not None
    assert balance_capital_a["debit_total"] == 0.00
    assert balance_capital_a["credit_total"] == 1000.00
    assert balance_capital_a["balance"] == 1000.00  # Equity: Credit - Debit

    # Verify Organization B balances (should only include org B entries)
    assert balance_cash_b is not None
    assert balance_cash_b["debit_total"] == 2000.00
    assert balance_cash_b["credit_total"] == 0.00
    assert balance_cash_b["balance"] == 2000.00  # Asset: Debit - Credit

    assert balance_capital_b is not None
    assert balance_capital_b["debit_total"] == 0.00
    assert balance_capital_b["credit_total"] == 2000.00
    assert balance_capital_b["balance"] == 2000.00  # Equity: Credit - Debit

    # Verify isolation: Org A balances should NOT include Org B entries
    # If isolation is broken, Cash A would show 3000 (1000 + 2000)
    assert balance_cash_a["debit_total"] != 3000.00
    assert balance_cash_a["balance"] != 3000.00

    # Verify isolation: Org B balances should NOT include Org A entries
    # If isolation is broken, Cash B would show 3000 (1000 + 2000)
    assert balance_cash_b["debit_total"] != 3000.00
    assert balance_cash_b["balance"] != 3000.00
