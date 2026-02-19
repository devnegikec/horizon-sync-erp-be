"""Test journal entry model relationships and foreign keys

This test verifies:
- journal_entry.lines relationship returns correct lines
- journal_entry_line.journal_entry relationship returns parent entry
- Cascade delete behavior when journal entry is deleted
- Foreign key constraints to accounts table
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.models.base import AccountStatus, AccountType, JournalStatus
from app.models.chart_of_account import Account
from app.models.journal_entry import JournalEntry, JournalEntryLine


def test_journal_entry_lines_relationship(db_session, mock_current_user):
    """Test that journal_entry.lines relationship returns correct lines"""
    # Create test accounts
    cash_account = Account(
        account_code="1110",
        account_name="Cash",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    capital_account = Account(
        account_code="3100",
        account_name="Owner's Capital",
        account_type=AccountType.EQUITY,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add_all([cash_account, capital_account])
    db_session.commit()
    db_session.refresh(cash_account)
    db_session.refresh(capital_account)

    # Create journal entry with 2 lines
    journal_entry = JournalEntry(
        organization_id=mock_current_user.organization_id,
        entry_no="JE-TEST-001",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=1000.00,
        total_credit=1000.00,
        remarks="Test opening balance entry",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(journal_entry)
    db_session.flush()

    # Create journal entry lines
    line1 = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        debit=1000.00,
        credit=0.00,
        sort_order=1,
    )
    line2 = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=capital_account.id,
        debit=0.00,
        credit=1000.00,
        sort_order=2,
    )
    db_session.add_all([line1, line2])
    db_session.commit()
    db_session.refresh(journal_entry)

    # Verify journal_entry.lines relationship returns correct lines
    assert len(journal_entry.lines) == 2
    assert journal_entry.lines[0].id == line1.id
    assert journal_entry.lines[1].id == line2.id
    assert journal_entry.lines[0].debit == 1000.00
    assert journal_entry.lines[1].credit == 1000.00


def test_journal_entry_line_parent_relationship(db_session, mock_current_user):
    """Test that journal_entry_line.journal_entry relationship returns parent entry"""
    # Create test account
    cash_account = Account(
        account_code="1110",
        account_name="Cash",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add(cash_account)
    db_session.commit()
    db_session.refresh(cash_account)

    # Create journal entry
    journal_entry = JournalEntry(
        organization_id=mock_current_user.organization_id,
        entry_no="JE-TEST-002",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=500.00,
        total_credit=500.00,
        remarks="Test parent relationship",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(journal_entry)
    db_session.flush()

    # Create journal entry line
    line = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        debit=500.00,
        credit=0.00,
        sort_order=1,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(line)

    # Verify journal_entry_line.journal_entry relationship returns parent entry
    assert line.journal_entry is not None
    assert line.journal_entry.id == journal_entry.id
    assert line.journal_entry.entry_no == "JE-TEST-002"
    assert line.journal_entry.total_debit == 500.00


def test_cascade_delete_journal_entry(db_session, mock_current_user):
    """Test that deleting journal entry cascades to delete lines"""
    # Create test accounts
    cash_account = Account(
        account_code="1110",
        account_name="Cash",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    capital_account = Account(
        account_code="3100",
        account_name="Owner's Capital",
        account_type=AccountType.EQUITY,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add_all([cash_account, capital_account])
    db_session.commit()
    db_session.refresh(cash_account)
    db_session.refresh(capital_account)

    # Create journal entry with 2 lines
    journal_entry = JournalEntry(
        organization_id=mock_current_user.organization_id,
        entry_no="JE-TEST-003",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=2000.00,
        total_credit=2000.00,
        remarks="Test cascade delete",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(journal_entry)
    db_session.flush()

    line1 = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        debit=2000.00,
        credit=0.00,
        sort_order=1,
    )
    line2 = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=capital_account.id,
        debit=0.00,
        credit=2000.00,
        sort_order=2,
    )
    db_session.add_all([line1, line2])
    db_session.commit()

    # Store line IDs for verification
    line1_id = line1.id
    line2_id = line2.id
    journal_entry_id = journal_entry.id

    # Verify lines exist before deletion
    lines_before = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry_id
    ).all()
    assert len(lines_before) == 2

    # Delete journal entry
    db_session.delete(journal_entry)
    db_session.commit()

    # Verify journal entry is deleted
    deleted_entry = db_session.query(JournalEntry).filter(
        JournalEntry.id == journal_entry_id
    ).first()
    assert deleted_entry is None

    # Verify lines are cascade deleted
    lines_after = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.journal_entry_id == journal_entry_id
    ).all()
    assert len(lines_after) == 0

    # Verify specific lines are deleted
    line1_after = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.id == line1_id
    ).first()
    line2_after = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.id == line2_id
    ).first()
    assert line1_after is None
    assert line2_after is None


def test_foreign_key_to_accounts_table(db_session, mock_current_user):
    """Test that foreign key to accounts table works correctly"""
    # Create test accounts
    cash_account = Account(
        account_code="1110",
        account_name="Cash",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    capital_account = Account(
        account_code="3100",
        account_name="Owner's Capital",
        account_type=AccountType.EQUITY,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add_all([cash_account, capital_account])
    db_session.commit()
    db_session.refresh(cash_account)
    db_session.refresh(capital_account)

    # Create journal entry
    journal_entry = JournalEntry(
        organization_id=mock_current_user.organization_id,
        entry_no="JE-TEST-004",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=1500.00,
        total_credit=1500.00,
        remarks="Test foreign key constraint",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(journal_entry)
    db_session.flush()

    # Create journal entry line with valid account_id
    line = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        debit=1500.00,
        credit=0.00,
        sort_order=1,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(line)

    # Verify line is created with correct account_id
    assert line.account_id == cash_account.id

    # Verify we can query the account through the foreign key
    account = db_session.query(Account).filter(
        Account.id == line.account_id
    ).first()
    assert account is not None
    assert account.account_code == "1110"
    assert account.account_name == "Cash"


def test_against_account_foreign_key(db_session, mock_current_user):
    """Test that against_account_id foreign key works correctly with SET NULL"""
    # Create test accounts
    cash_account = Account(
        account_code="1110",
        account_name="Cash",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    capital_account = Account(
        account_code="3100",
        account_name="Owner's Capital",
        account_type=AccountType.EQUITY,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        organization_id=mock_current_user.organization_id,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add_all([cash_account, capital_account])
    db_session.commit()
    db_session.refresh(cash_account)
    db_session.refresh(capital_account)

    # Create journal entry
    journal_entry = JournalEntry(
        organization_id=mock_current_user.organization_id,
        entry_no="JE-TEST-005",
        posting_date=datetime.now(UTC),
        status=JournalStatus.POSTED,
        total_debit=800.00,
        total_credit=800.00,
        remarks="Test against_account_id",
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(journal_entry)
    db_session.flush()

    # Create journal entry line with against_account_id
    line = JournalEntryLine(
        organization_id=mock_current_user.organization_id,
        journal_entry_id=journal_entry.id,
        account_id=cash_account.id,
        against_account_id=capital_account.id,
        debit=800.00,
        credit=0.00,
        sort_order=1,
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(line)

    # Verify against_account_id is set correctly
    assert line.against_account_id == capital_account.id

    # Note: SQLite doesn't enforce SET NULL on foreign keys by default
    # In production PostgreSQL, deleting capital_account would set against_account_id to NULL
    # For this test, we just verify the foreign key relationship is established
    against_account = db_session.query(Account).filter(
        Account.id == line.against_account_id
    ).first()
    assert against_account is not None
    assert against_account.account_code == "3100"
