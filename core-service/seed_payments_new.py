"""Seed Journal Entries data for testing and demonstration

This script creates sample journal entries with:
- Common accounting scenarios (opening balance, purchases, sales, expenses, depreciation)
- Balanced debits and credits for each entry
- Posted status for inclusion in balance calculations
- References to accounts from the chart of accounts seed data

Usage:
    python seed_journal_entries.py
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text

# Database URL - can be overridden via environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)

# Organization ID - replace with your organization ID
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

# User ID for audit fields
ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# Calculate posting dates (30-90 days in the past)
def days_ago(days):
    return datetime.now(UTC) - timedelta(days=days)


# Sample Journal Entries data
# Each entry has: entry_no, posting_date, remarks, and lines (account_code, debit, credit, remarks)
journal_entries_data = [
    {
        "entry_no": "JE-2024-001",
        "posting_date": days_ago(90),
        "remarks": "Opening balance entry - Initial capital investment",
        "lines": [
            {
                "account_code": "1110",  # Cash and Cash Equivalents
                "debit": Decimal("50000.00"),
                "credit": Decimal("0.00"),
                "remarks": "Initial cash investment",
            },
            {
                "account_code": "3100",  # Owner's Capital
                "debit": Decimal("0.00"),
                "credit": Decimal("50000.00"),
                "remarks": "Owner's initial capital contribution",
            },
        ],
    },
    {
        "entry_no": "JE-2024-002",
        "posting_date": days_ago(75),
        "remarks": "Purchase of raw materials inventory",
        "lines": [
            {
                "account_code": "1130",  # Inventory
                "debit": Decimal("8500.00"),
                "credit": Decimal("0.00"),
                "remarks": "Raw materials purchased",
            },
            {
                "account_code": "2110",  # Accounts Payable
                "debit": Decimal("0.00"),
                "credit": Decimal("8500.00"),
                "remarks": "Amount owed to supplier",
            },
        ],
    },
    {
        "entry_no": "JE-2024-003",
        "posting_date": days_ago(60),
        "remarks": "Sales transaction - Product sold to customer",
        "lines": [
            {
                "account_code": "1120",  # Accounts Receivable
                "debit": Decimal("15000.00"),
                "credit": Decimal("0.00"),
                "remarks": "Amount due from customer",
            },
            {
                "account_code": "4110",  # Domestic Sales
                "debit": Decimal("0.00"),
                "credit": Decimal("15000.00"),
                "remarks": "Sales revenue recognized",
            },
            {
                "account_code": "5110",  # Material Costs (COGS)
                "debit": Decimal("6000.00"),
                "credit": Decimal("0.00"),
                "remarks": "Cost of goods sold",
            },
            {
                "account_code": "1130",  # Inventory
                "debit": Decimal("0.00"),
                "credit": Decimal("6000.00"),
                "remarks": "Inventory reduction",
            },
        ],
    },
    {
        "entry_no": "JE-2024-004",
        "posting_date": days_ago(45),
        "remarks": "Payment of employee salaries",
        "lines": [
            {
                "account_code": "5210",  # Salaries and Wages
                "debit": Decimal("12000.00"),
                "credit": Decimal("0.00"),
                "remarks": "Monthly salary expense",
            },
            {
                "account_code": "1110",  # Cash and Cash Equivalents
                "debit": Decimal("0.00"),
                "credit": Decimal("12000.00"),
                "remarks": "Cash paid for salaries",
            },
        ],
    },
    {
        "entry_no": "JE-2024-005",
        "posting_date": days_ago(40),
        "remarks": "Payment to supplier for inventory purchase",
        "lines": [
            {
                "account_code": "2110",  # Accounts Payable
                "debit": Decimal("8500.00"),
                "credit": Decimal("0.00"),
                "remarks": "Payment to supplier",
            },
            {
                "account_code": "1110",  # Cash and Cash Equivalents
                "debit": Decimal("0.00"),
                "credit": Decimal("8500.00"),
                "remarks": "Cash paid to supplier",
            },
        ],
    },
    {
        "entry_no": "JE-2024-006",
        "posting_date": days_ago(35),
        "remarks": "Collection from customer",
        "lines": [
            {
                "account_code": "1110",  # Cash and Cash Equivalents
                "debit": Decimal("15000.00"),
                "credit": Decimal("0.00"),
                "remarks": "Cash received from customer",
            },
            {
                "account_code": "1120",  # Accounts Receivable
                "debit": Decimal("0.00"),
                "credit": Decimal("15000.00"),
                "remarks": "Customer payment received",
            },
        ],
    },
    {
        "entry_no": "JE-2024-007",
        "posting_date": days_ago(30),
        "remarks": "Monthly depreciation expense",
        "lines": [
            {
                "account_code": "5420",  # Depreciation Expense
                "debit": Decimal("500.00"),
                "credit": Decimal("0.00"),
                "remarks": "Monthly depreciation charge",
            },
            {
                "account_code": "1220",  # Accumulated Depreciation
                "debit": Decimal("0.00"),
                "credit": Decimal("500.00"),
                "remarks": "Accumulated depreciation increase",
            },
        ],
    },
]


def get_account_id(conn, account_code):
    """Get account ID by account code"""
    result = conn.execute(
        text("""
            SELECT id FROM accounts
            WHERE organization_id = :org_id AND account_code = :code
        """),
        {"org_id": str(ORG_ID), "code": account_code},
    )
    row = result.fetchone()
    if not row:
        raise ValueError(
            f"Account with code {account_code} not found. Please run seed_chart_of_accounts.py first."
        )
    return row[0]


def seed_journal_entries():
    """Insert Journal Entries seed data using raw SQL to avoid model relationship issues"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        try:
            print("=" * 70)
            print("Journal Entries Seeding Script")
            print("=" * 70)
            print(f"\nOrganization ID: {ORG_ID}")
            print(f"Total journal entries to create: {len(journal_entries_data)}")
            print("\nStarting seed process...\n")

            # Track statistics
            created_entries = 0
            skipped_entries = 0
            total_debits = Decimal("0.00")
            total_credits = Decimal("0.00")
            affected_accounts = set()

            for entry_data in journal_entries_data:
                entry_no = entry_data["entry_no"]

                # Check if journal entry already exists
                result = conn.execute(
                    text("""
                        SELECT id FROM journal_entries
                        WHERE organization_id = :org_id AND entry_no = :entry_no
                    """),
                    {"org_id": str(ORG_ID), "entry_no": entry_no},
                )
                existing = result.fetchone()

                if existing:
                    print(f"  ⊘ {entry_no} (already exists)")
                    skipped_entries += 1
                    continue

                # Calculate totals for this entry
                entry_debit_total = sum(line["debit"] for line in entry_data["lines"])
                entry_credit_total = sum(line["credit"] for line in entry_data["lines"])

                # Verify entry is balanced
                if entry_debit_total != entry_credit_total:
                    raise ValueError(
                        f"Entry {entry_no} is not balanced: "
                        f"Debit={entry_debit_total}, Credit={entry_credit_total}"
                    )

                # Create journal entry
                journal_entry_id = str(uuid.uuid4())
                posting_date = entry_data["posting_date"]

                conn.execute(
                    text("""
                        INSERT INTO journal_entries (
                            id, organization_id, entry_no, posting_date, status,
                            total_debit, total_credit, remarks, posted_at,
                            created_by, updated_by, created_at, updated_at
                        ) VALUES (
                            :id, :org_id, :entry_no, :posting_date, :status,
                            :total_debit, :total_credit, :remarks, :posted_at,
                            :created_by, :updated_by, :created_at, :updated_at
                        )
                    """),
                    {
                        "id": journal_entry_id,
                        "org_id": str(ORG_ID),
                        "entry_no": entry_no,
                        "posting_date": posting_date,
                        "status": "posted",
                        "total_debit": float(entry_debit_total),
                        "total_credit": float(entry_credit_total),
                        "remarks": entry_data["remarks"],
                        "posted_at": posting_date,
                        "created_by": str(ADMIN_USER_ID),
                        "updated_by": str(ADMIN_USER_ID),
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    },
                )

                # Create journal entry lines
                line_count = 0
                for line_data in entry_data["lines"]:
                    account_id = get_account_id(conn, line_data["account_code"])
                    affected_accounts.add(line_data["account_code"])

                    line_id = str(uuid.uuid4())
                    conn.execute(
                        text("""
                            INSERT INTO journal_entry_lines (
                                id, organization_id, journal_entry_id, account_id,
                                debit, credit, remarks, sort_order,
                                created_at, updated_at
                            ) VALUES (
                                :id, :org_id, :journal_entry_id, :account_id,
                                :debit, :credit, :remarks, :sort_order,
                                :created_at, :updated_at
                            )
                        """),
                        {
                            "id": line_id,
                            "org_id": str(ORG_ID),
                            "journal_entry_id": journal_entry_id,
                            "account_id": account_id,
                            "debit": float(line_data["debit"]),
                            "credit": float(line_data["credit"]),
                            "remarks": line_data.get("remarks", ""),
                            "sort_order": line_count,
                            "created_at": datetime.now(UTC),
                            "updated_at": datetime.now(UTC),
                        },
                    )
                    line_count += 1

                # Update totals
                total_debits += entry_debit_total
                total_credits += entry_credit_total
                created_entries += 1

                # Print entry summary
                print(f"  ✓ {entry_no} - {entry_data['remarks']}")
                print(f"    Date: {posting_date.strftime('%Y-%m-%d')}")
                print(
                    f"    Debit: ${entry_debit_total:,.2f} | Credit: ${entry_credit_total:,.2f}"
                )
                print(f"    Lines: {line_count}")
                print()

            # Commit all changes
            conn.commit()

            # Display summary
            print("=" * 70)
            print("Seeding Complete!")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"  • Journal entries created: {created_entries}")
            print(f"  • Journal entries skipped (already exist): {skipped_entries}")
            print(f"  • Total debits: ${total_debits:,.2f}")
            print(f"  • Total credits: ${total_credits:,.2f}")
            print(f"  • Affected accounts: {len(affected_accounts)}")

            # Display affected accounts
            print("\n💡 Affected Account Codes:")
            print(f"  {', '.join(sorted(affected_accounts))}")

            # Display sample entries
            print("\n📝 Sample Journal Entries:")
            print("  • JE-2024-001: Opening balance (Cash/Owner's Capital)")
            print("  • JE-2024-002: Purchase transaction (Inventory/Accounts Payable)")
            print(
                "  • JE-2024-003: Sales transaction (AR/Sales Revenue, COGS/Inventory)"
            )
            print("  • JE-2024-004: Salary payment (Salaries/Cash)")
            print(
                "  • JE-2024-007: Depreciation (Depreciation Expense/Accumulated Depreciation)"
            )

            print("\n✓ Journal entries seed data inserted successfully!")
            print(
                "✓ All entries are posted and will be included in balance calculations"
            )
            print("=" * 70)

        except Exception as e:
            conn.rollback()
            print(f"\n✗ Error during seeding: {e}")
            raise


if __name__ == "__main__":
    seed_journal_entries()
