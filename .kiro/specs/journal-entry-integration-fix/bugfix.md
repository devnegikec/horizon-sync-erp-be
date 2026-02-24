# Bugfix Requirements Document

## Introduction

The journal entry implementation exists in the codebase but is not integrated into the database schema, causing all account balance calculations to return zero. The `JournalEntry` and `JournalEntryLine` models are defined in `app/models/journal_entry.py` but are not imported in `app/models/__init__.py`, and no Alembic migration exists to create the corresponding database tables (`journal_entries` and `journal_entry_lines`).

When the balance calculator service attempts to query journal entry lines to calculate account balances, it encounters a `ProgrammingError` or `OperationalError` (UndefinedTable) because the tables don't exist. The service catches this exception and falls back to returning zero balances for all accounts, effectively breaking the balance calculation feature.

This bug affects the core accounting functionality of the ERP system, making it impossible to track actual account balances from journal entries.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the balance calculator queries journal entry lines for an account THEN the system raises a ProgrammingError/OperationalError due to missing `journal_entry_lines` table

1.2 WHEN the balance calculator catches the database error THEN the system logs "Balance query fallback to zero totals due to missing journal schema" and returns zero for debit_total and credit_total

1.3 WHEN any account balance is requested THEN the system returns balance=0, debit_total=0, credit_total=0 regardless of actual journal entries

1.4 WHEN Alembic attempts to autogenerate migrations THEN the system does not detect JournalEntry and JournalEntryLine models because they are not imported in `app/models/__init__.py`

1.5 WHEN attempting to create journal entries programmatically THEN the system fails with table not found errors

1.6 WHEN attempting to update existing journal entries THEN the system fails with table not found errors


### Expected Behavior (Correct)

2.1 WHEN the balance calculator queries journal entry lines for an account THEN the system SHALL successfully execute the query against the existing `journal_entry_lines` table

2.2 WHEN journal entry lines exist for an account THEN the system SHALL calculate and return accurate debit_total, credit_total, and balance values based on posted journal entries

2.3 WHEN JournalEntry and JournalEntryLine models are imported in `app/models/__init__.py` THEN Alembic SHALL detect these models during migration autogeneration

2.4 WHEN an Alembic migration creates the journal_entries and journal_entry_lines tables THEN the system SHALL have the complete schema including all columns, foreign keys, indexes, and constraints defined in the models

2.5 WHEN journal entries are created and posted THEN the system SHALL persist them to the database and use them for balance calculations

2.6 WHEN journal entries are updated (not deleted) THEN the system SHALL modify the existing records and recalculate affected account balances

2.7 WHEN a seed data script creates sample journal entries THEN the system SHALL successfully persist them to the database for testing balance calculations

### Unchanged Behavior (Regression Prevention)

3.1 WHEN querying balances for accounts without journal entries THEN the system SHALL CONTINUE TO return zero balances (debit_total=0, credit_total=0, balance=0)

3.2 WHEN the balance calculator calculates natural balance direction based on account type THEN the system SHALL CONTINUE TO use the existing logic (Assets/Expenses: Debit - Credit, Liabilities/Equity/Revenue: Credit - Debit)

3.3 WHEN the balance calculator performs currency conversion THEN the system SHALL CONTINUE TO use the existing CurrencyService integration

3.4 WHEN the balance calculator calculates consolidated balances for parent accounts THEN the system SHALL CONTINUE TO use the existing HierarchyManager integration

3.5 WHEN existing Alembic migrations run THEN the system SHALL CONTINUE TO execute successfully without conflicts

3.6 WHEN existing models (Account, AccountBalance, etc.) are queried THEN the system SHALL CONTINUE TO function normally

3.7 WHEN the balance calculator caches results THEN the system SHALL CONTINUE TO use the existing Redis cache implementation
