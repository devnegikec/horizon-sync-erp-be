"""Seed Chart of Accounts data for testing and demonstration

This script creates a sample Chart of Accounts with:
- Example accounts for each account type (Asset, Liability, Equity, Income, Expense)
- A hierarchical structure with parent and child accounts
- Multi-currency support examples
- Realistic account codes and names

Usage:
    python seed_chart_of_accounts.py
"""

import uuid
from datetime import datetime, UTC

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL - can be overridden via environment variable
DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"

# Organization ID - replace with your organization ID
ORG_ID = uuid.UUID("b1f71de1-0a19-424e-9580-1d3f871c5b1f")

# User ID for audit fields
ADMIN_USER = "admin@example.com"

# Sample Chart of Accounts data
# Structure: Each account has code, name, type, currency, description, and optional parent_code
# Account types: 'asset', 'liability', 'equity', 'income', 'expense'
accounts_data = [
    # ============================================
    # ASSETS (1000-1999)
    # ============================================
    {
        "account_code": "1000",
        "account_name": "Assets",
        "account_type": "asset",
        "currency": "USD",
        "description": "All company assets",
        "is_posting_account": False,  # Parent account
    },
    # Current Assets (1100-1199)
    {
        "account_code": "1100",
        "account_name": "Current Assets",
        "account_type": "asset",
        "currency": "USD",
        "description": "Assets expected to be converted to cash within one year",
        "parent_code": "1000",
        "is_posting_account": False,
    },
    {
        "account_code": "1110",
        "account_name": "Cash and Cash Equivalents",
        "account_type": "asset",
        "currency": "USD",
        "description": "Cash on hand and in bank accounts",
        "parent_code": "1100",
    },
    {
        "account_code": "1120",
        "account_name": "Accounts Receivable",
        "account_type": "asset",
        "currency": "USD",
        "description": "Money owed by customers",
        "parent_code": "1100",
    },
    {
        "account_code": "1130",
        "account_name": "Inventory",
        "account_type": "asset",
        "currency": "USD",
        "description": "Raw materials, work in progress, and finished goods",
        "parent_code": "1100",
    },
    {
        "account_code": "1131",
        "account_name": "Raw Materials Inventory",
        "account_type": "asset",
        "currency": "USD",
        "description": "Raw materials for production",
        "parent_code": "1130",
    },
    {
        "account_code": "1132",
        "account_name": "Finished Goods Inventory",
        "account_type": "asset",
        "currency": "USD",
        "description": "Completed products ready for sale",
        "parent_code": "1130",
    },
    # Fixed Assets (1200-1299)
    {
        "account_code": "1200",
        "account_name": "Fixed Assets",
        "account_type": "asset",
        "currency": "USD",
        "description": "Long-term tangible assets",
        "parent_code": "1000",
        "is_posting_account": False,
    },
    {
        "account_code": "1210",
        "account_name": "Property, Plant and Equipment",
        "account_type": "asset",
        "currency": "USD",
        "description": "Land, buildings, and equipment",
        "parent_code": "1200",
    },
    {
        "account_code": "1220",
        "account_name": "Accumulated Depreciation",
        "account_type": "asset",
        "currency": "USD",
        "description": "Contra asset account for depreciation",
        "parent_code": "1200",
    },

    # ============================================
    # LIABILITIES (2000-2999)
    # ============================================
    {
        "account_code": "2000",
        "account_name": "Liabilities",
        "account_type": "liability",
        "currency": "USD",
        "description": "All company liabilities",
        "is_posting_account": False,
    },
    # Current Liabilities (2100-2199)
    {
        "account_code": "2100",
        "account_name": "Current Liabilities",
        "account_type": "liability",
        "currency": "USD",
        "description": "Obligations due within one year",
        "parent_code": "2000",
        "is_posting_account": False,
    },
    {
        "account_code": "2110",
        "account_name": "Accounts Payable",
        "account_type": "liability",
        "currency": "USD",
        "description": "Money owed to suppliers",
        "parent_code": "2100",
    },
    {
        "account_code": "2120",
        "account_name": "Accrued Expenses",
        "account_type": "liability",
        "currency": "USD",
        "description": "Expenses incurred but not yet paid",
        "parent_code": "2100",
    },
    {
        "account_code": "2130",
        "account_name": "Sales Tax Payable",
        "account_type": "liability",
        "currency": "USD",
        "description": "Sales tax collected from customers",
        "parent_code": "2100",
    },
    # Long-term Liabilities (2200-2299)
    {
        "account_code": "2200",
        "account_name": "Long-term Liabilities",
        "account_type": "liability",
        "currency": "USD",
        "description": "Obligations due after one year",
        "parent_code": "2000",
        "is_posting_account": False,
    },
    {
        "account_code": "2210",
        "account_name": "Long-term Debt",
        "account_type": "liability",
        "currency": "USD",
        "description": "Loans and bonds payable",
        "parent_code": "2200",
    },

    # ============================================
    # EQUITY (3000-3999)
    # ============================================
    {
        "account_code": "3000",
        "account_name": "Equity",
        "account_type": "equity",
        "currency": "USD",
        "description": "Owner's equity and retained earnings",
        "is_posting_account": False,
    },
    {
        "account_code": "3100",
        "account_name": "Owner's Capital",
        "account_type": "equity",
        "currency": "USD",
        "description": "Initial and additional capital contributions",
        "parent_code": "3000",
    },
    {
        "account_code": "3200",
        "account_name": "Retained Earnings",
        "account_type": "equity",
        "currency": "USD",
        "description": "Accumulated profits retained in the business",
        "parent_code": "3000",
    },
    {
        "account_code": "3300",
        "account_name": "Drawings",
        "account_type": "equity",
        "currency": "USD",
        "description": "Owner withdrawals from the business",
        "parent_code": "3000",
    },

    # ============================================
    # INCOME/REVENUE (4000-4999)
    # ============================================
    {
        "account_code": "4000",
        "account_name": "Revenue",
        "account_type": "income",
        "currency": "USD",
        "description": "All revenue and income",
        "is_posting_account": False,
    },
    # Sales Revenue (4100-4199)
    {
        "account_code": "4100",
        "account_name": "Sales Revenue",
        "account_type": "income",
        "currency": "USD",
        "description": "Revenue from product sales",
        "parent_code": "4000",
        "is_posting_account": False,
    },
    {
        "account_code": "4110",
        "account_name": "Domestic Sales",
        "account_type": "income",
        "currency": "USD",
        "description": "Sales within the country",
        "parent_code": "4100",
    },
    {
        "account_code": "4120",
        "account_name": "International Sales",
        "account_type": "income",
        "currency": "USD",
        "description": "Export sales",
        "parent_code": "4100",
    },
    {
        "account_code": "4121",
        "account_name": "International Sales - EUR",
        "account_type": "income",
        "currency": "EUR",
        "description": "Export sales in Euros",
        "parent_code": "4120",
    },
    # Service Revenue (4200-4299)
    {
        "account_code": "4200",
        "account_name": "Service Revenue",
        "account_type": "income",
        "currency": "USD",
        "description": "Revenue from services",
        "parent_code": "4000",
    },
    # Other Income (4300-4399)
    {
        "account_code": "4300",
        "account_name": "Other Income",
        "account_type": "income",
        "currency": "USD",
        "description": "Miscellaneous income",
        "parent_code": "4000",
    },
    {
        "account_code": "4310",
        "account_name": "Interest Income",
        "account_type": "income",
        "currency": "USD",
        "description": "Interest earned on investments",
        "parent_code": "4300",
    },

    # ============================================
    # EXPENSES (5000-5999)
    # ============================================
    {
        "account_code": "5000",
        "account_name": "Expenses",
        "account_type": "expense",
        "currency": "USD",
        "description": "All business expenses",
        "is_posting_account": False,
    },
    # Cost of Goods Sold (5100-5199)
    {
        "account_code": "5100",
        "account_name": "Cost of Goods Sold",
        "account_type": "expense",
        "currency": "USD",
        "description": "Direct costs of producing goods",
        "parent_code": "5000",
        "is_posting_account": False,
    },
    {
        "account_code": "5110",
        "account_name": "Material Costs",
        "account_type": "expense",
        "currency": "USD",
        "description": "Cost of raw materials",
        "parent_code": "5100",
    },
    {
        "account_code": "5120",
        "account_name": "Labor Costs",
        "account_type": "expense",
        "currency": "USD",
        "description": "Direct labor costs",
        "parent_code": "5100",
    },
    # Operating Expenses (5200-5299)
    {
        "account_code": "5200",
        "account_name": "Operating Expenses",
        "account_type": "expense",
        "currency": "USD",
        "description": "Day-to-day business expenses",
        "parent_code": "5000",
        "is_posting_account": False,
    },
    {
        "account_code": "5210",
        "account_name": "Salaries and Wages",
        "account_type": "expense",
        "currency": "USD",
        "description": "Employee compensation",
        "parent_code": "5200",
    },
    {
        "account_code": "5220",
        "account_name": "Rent Expense",
        "account_type": "expense",
        "currency": "USD",
        "description": "Office and facility rent",
        "parent_code": "5200",
    },
    {
        "account_code": "5230",
        "account_name": "Utilities",
        "account_type": "expense",
        "currency": "USD",
        "description": "Electricity, water, internet",
        "parent_code": "5200",
    },
    {
        "account_code": "5240",
        "account_name": "Office Supplies",
        "account_type": "expense",
        "currency": "USD",
        "description": "Stationery and office materials",
        "parent_code": "5200",
    },
    # Marketing Expenses (5300-5399)
    {
        "account_code": "5300",
        "account_name": "Marketing and Advertising",
        "account_type": "expense",
        "currency": "USD",
        "description": "Marketing and promotional expenses",
        "parent_code": "5000",
        "is_posting_account": False,
    },
    {
        "account_code": "5310",
        "account_name": "Digital Marketing",
        "account_type": "expense",
        "currency": "USD",
        "description": "Online advertising and social media",
        "parent_code": "5300",
    },
    {
        "account_code": "5320",
        "account_name": "Traditional Marketing",
        "account_type": "expense",
        "currency": "USD",
        "description": "Print, TV, and radio advertising",
        "parent_code": "5300",
    },
    # Other Expenses (5400-5499)
    {
        "account_code": "5400",
        "account_name": "Other Expenses",
        "account_type": "expense",
        "currency": "USD",
        "description": "Miscellaneous expenses",
        "parent_code": "5000",
        "is_posting_account": False,
    },
    {
        "account_code": "5410",
        "account_name": "Bank Charges",
        "account_type": "expense",
        "currency": "USD",
        "description": "Banking fees and charges",
        "parent_code": "5400",
    },
    {
        "account_code": "5420",
        "account_name": "Depreciation Expense",
        "account_type": "expense",
        "currency": "USD",
        "description": "Depreciation of fixed assets",
        "parent_code": "5400",
    },
]


def seed_chart_of_accounts():
    """Insert Chart of Accounts seed data using raw SQL to avoid model relationship issues"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            print("=" * 70)
            print("Chart of Accounts Seeding Script")
            print("=" * 70)
            print(f"\nOrganization ID: {ORG_ID}")
            print(f"Total accounts to create: {len(accounts_data)}")
            print("\nStarting seed process...\n")

            # First pass: Create all accounts without parent relationships
            account_map = {}  # Map account_code to account_id
            created_count = 0
            skipped_count = 0

            for account_data in accounts_data:
                account_code = account_data["account_code"]

                # Check if account already exists
                result = conn.execute(
                    text("""
                        SELECT id FROM accounts 
                        WHERE organization_id = :org_id AND account_code = :code
                    """),
                    {"org_id": str(ORG_ID), "code": account_code}
                )
                existing = result.fetchone()

                if existing:
                    print(f"  ⊘ {account_code} - {account_data['account_name']} (already exists)")
                    account_map[account_code] = existing[0]
                    skipped_count += 1
                    continue

                # Create account without parent first
                account_id = str(uuid.uuid4())
                account_type_value = account_data["account_type"].value if hasattr(account_data["account_type"], 'value') else account_data["account_type"]
                
                conn.execute(
                    text("""
                        INSERT INTO accounts (
                            id, organization_id, account_code, account_name, account_type,
                            currency, description, is_posting_account, status,
                            created_by, updated_by, created_at, updated_at
                        ) VALUES (
                            :id, :org_id, :code, :name, :type,
                            :currency, :description, :is_posting, :status,
                            :created_by, :updated_by, :created_at, :updated_at
                        )
                    """),
                    {
                        "id": account_id,
                        "org_id": str(ORG_ID),
                        "code": account_data["account_code"],
                        "name": account_data["account_name"],
                        "type": account_type_value,
                        "currency": account_data["currency"],
                        "description": account_data.get("description", ""),
                        "is_posting": account_data.get("is_posting_account", True),
                        "status": "ACTIVE",
                        "created_by": ADMIN_USER,
                        "updated_by": ADMIN_USER,
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    }
                )

                account_map[account_code] = account_id
                created_count += 1

                # Print with type indicator
                type_symbol = {
                    "asset": "💰",
                    "liability": "📋",
                    "equity": "🏦",
                    "income": "💵",
                    "expense": "💸",
                }
                symbol = type_symbol.get(account_type_value, "📊")
                print(f"  {symbol} {account_code} - {account_data['account_name']}")

            # Second pass: Set up parent relationships
            print("\nSetting up account hierarchy...")
            hierarchy_count = 0

            for account_data in accounts_data:
                parent_code = account_data.get("parent_code")
                if parent_code:
                    account_code = account_data["account_code"]
                    account_id = account_map.get(account_code)
                    parent_id = account_map.get(parent_code)

                    if account_id and parent_id:
                        conn.execute(
                            text("""
                                UPDATE accounts 
                                SET parent_account_id = :parent_id
                                WHERE id = :account_id
                            """),
                            {"parent_id": parent_id, "account_id": account_id}
                        )
                        hierarchy_count += 1
                        print(f"  ↳ {account_code} → parent: {parent_code}")

            # Commit all changes
            conn.commit()

            # Display summary
            print("\n" + "=" * 70)
            print("Seeding Complete!")
            print("=" * 70)
            print(f"\n📊 Summary:")
            print(f"  • Accounts created: {created_count}")
            print(f"  • Accounts skipped (already exist): {skipped_count}")
            print(f"  • Parent-child relationships: {hierarchy_count}")

            # Display account breakdown by type
            print(f"\n📈 Account Breakdown by Type:")
            type_counts = {}
            for a in accounts_data:
                account_type = a["account_type"].value if hasattr(a["account_type"], 'value') else a["account_type"]
                type_counts[account_type] = type_counts.get(account_type, 0) + 1
            
            for account_type, count in sorted(type_counts.items()):
                print(f"  • {account_type.upper()}: {count} accounts")

            # Display sample accounts
            print(f"\n💡 Sample Accounts:")
            print(f"  • Assets: 1110 (Cash), 1120 (Accounts Receivable), 1130 (Inventory)")
            print(f"  • Liabilities: 2110 (Accounts Payable), 2120 (Accrued Expenses)")
            print(f"  • Equity: 3100 (Owner's Capital), 3200 (Retained Earnings)")
            print(f"  • Income: 4110 (Domestic Sales), 4200 (Service Revenue)")
            print(f"  • Expenses: 5110 (Material Costs), 5210 (Salaries and Wages)")

            print(f"\n✓ Chart of Accounts seed data inserted successfully!")
            print("=" * 70)

        except Exception as e:
            conn.rollback()
            print(f"\n✗ Error during seeding: {e}")
            raise


if __name__ == "__main__":
    seed_chart_of_accounts()
