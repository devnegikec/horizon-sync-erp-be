"""
Simple script to fix default account mappings without dependencies on organizations table.
This script will help you identify and fix broken default account mappings.
"""

import os

from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def main():
    print("=" * 80)
    print("DEFAULT ACCOUNT MAPPINGS FIX TOOL")
    print("=" * 80)
    print()

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if default_accounts table exists
        print("Checking database tables...")
        print("-" * 80)

        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'default_accounts'
            )
        """)
        )

        table_exists = result.fetchone()[0]

        if not table_exists:
            print("❌ ERROR: 'default_accounts' table does not exist!")
            print("\nThis means your database migrations haven't been run yet.")
            print("\nTo fix this, you need to:")
            print("  1. Run database migrations:")
            print("     cd horizon-sync-erp-be/core-service")
            print("     alembic upgrade head")
            print("\n  2. Then run this script again")
            print("\nAlternatively, if you're setting up for the first time:")
            print("  - Make sure your backend server has been started at least once")
            print("  - The server should automatically create tables on first run")
            return

        print("✅ default_accounts table exists\n")

        # Step 1: Show existing accounts
        print("STEP 1: Your Existing Accounts")
        print("-" * 80)

        result = conn.execute(
            text("""
            SELECT id, account_code, account_name, account_type 
            FROM accounts 
            WHERE account_type IN ('asset', 'liability')
            ORDER BY account_code
        """)
        )

        accounts = result.fetchall()

        if not accounts:
            print("❌ No accounts found! Please create accounts first via UI.")
            print("   Go to: Books > Chart of Accounts")
            return

        print(f"Found {len(accounts)} accounts:\n")
        for acc in accounts:
            print(f"  ID: {acc[0]}")
            print(f"  Code: {acc[1]}")
            print(f"  Name: {acc[2]}")
            print(f"  Type: {acc[3]}")
            print()

        # Step 2: Show current default mappings
        print("\nSTEP 2: Current Default Account Mappings")
        print("-" * 80)

        result = conn.execute(
            text("""
            SELECT 
                da.id,
                da.transaction_type,
                da.account_id,
                a.account_code,
                a.account_name,
                CASE WHEN a.id IS NULL THEN '❌ BROKEN' ELSE '✅ OK' END as status
            FROM default_accounts da
            LEFT JOIN accounts a ON da.account_id = a.id
            ORDER BY da.transaction_type
        """)
        )

        mappings = result.fetchall()

        if not mappings:
            print("❌ No default account mappings found!")
            print("\nYou need to create default account mappings.")
            print("\nOption 1: Create via UI (Books > System Configuration)")
            print(
                "Option 2: Create manually with SQL (see FIX_DEFAULT_ACCOUNTS_MANUAL.md)"
            )
            return

        print(f"Found {len(mappings)} mappings:\n")
        broken_mappings = []

        for mapping in mappings:
            print(f"  Transaction Type: {mapping[1]}")
            print(f"  Account ID: {mapping[2]}")
            print(f"  Account Code: {mapping[3] or 'N/A'}")
            print(f"  Account Name: {mapping[4] or 'N/A'}")
            print(f"  Status: {mapping[5]}")
            print()

            if mapping[5] == "❌ BROKEN":
                broken_mappings.append(mapping)

        # Step 3: Provide fix instructions
        if broken_mappings:
            print("\nSTEP 3: Fix Broken Mappings")
            print("-" * 80)
            print(f"❌ Found {len(broken_mappings)} broken mapping(s)!\n")
            print("To fix, run these SQL commands:\n")

            for mapping in broken_mappings:
                transaction_type = mapping[1]
                mapping_id = mapping[0]

                print(f"-- Fix {transaction_type} mapping")
                print("UPDATE default_accounts")
                print("SET account_id = '<your-account-id-from-step-1>'")
                print(f"WHERE id = '{mapping_id}';")
                print()

            print("\nRecommended account mappings:")
            print("  - cash → Cash account (e.g., 1010)")
            print("  - bank → Bank account (e.g., 1020)")
            print("  - checks_received → Bank account (e.g., 1020)")
            print("  - accounts_receivable → Accounts Receivable (e.g., 1200)")
            print("  - accounts_payable → Accounts Payable (e.g., 2000)")
            print()
            print("See FIX_DEFAULT_ACCOUNTS_MANUAL.md for detailed instructions.")
        else:
            print("\nSTEP 3: Verification")
            print("-" * 80)
            print("✅ All default account mappings are valid!")
            print("\nYou can now:")
            print("  1. Restart your backend server")
            print("  2. Test payment confirmation")

        print("\n" + "=" * 80)
        print("DONE")
        print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("  1. Database is running")
        print("  2. Database credentials are correct")
        print(
            "  3. Database URL: postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
        )
