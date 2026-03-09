"""
Test script to verify payment account configuration and simulate payment confirmation.
"""

import os

from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def test_payment_accounts():
    print("=" * 80)
    print("PAYMENT ACCOUNT CONFIGURATION TEST")
    print("=" * 80)
    print()

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Get organization ID from default_accounts table
        result = conn.execute(
            text("SELECT DISTINCT organization_id FROM default_accounts LIMIT 1")
        )
        org = result.fetchone()

        if not org:
            print("❌ No default accounts found!")
            print("Please configure default accounts first.")
            return

        org_id = org[0]
        print(f"Organization ID: {org_id}\n")

        # Test Customer Payment (Cash)
        print("TEST 1: Customer Payment - Cash")
        print("-" * 80)

        # Check cash mapping
        result = conn.execute(
            text("""
            SELECT da.account_id, a.account_code, a.account_name, a.is_posting_account
            FROM default_accounts da
            JOIN accounts a ON da.account_id = a.id
            WHERE da.transaction_type = 'cash' 
            AND da.organization_id = :org_id
            LIMIT 1
        """),
            {"org_id": org_id},
        )

        cash_account = result.fetchone()
        if cash_account:
            print(f"✅ Cash Account: {cash_account[1]} - {cash_account[2]}")
            print(f"   ID: {cash_account[0]}")
            print(f"   Is Posting Account: {cash_account[3]}")
            if not cash_account[3]:
                print("   ⚠️  WARNING: This is not a posting account!")
        else:
            print("❌ No cash account mapping found!")

        print()

        # Check accounts_receivable mapping
        result = conn.execute(
            text("""
            SELECT da.account_id, a.account_code, a.account_name, a.is_posting_account
            FROM default_accounts da
            JOIN accounts a ON da.account_id = a.id
            WHERE da.transaction_type = 'accounts_receivable' 
            AND da.organization_id = :org_id
            LIMIT 1
        """),
            {"org_id": org_id},
        )

        ar_account = result.fetchone()
        if ar_account:
            print(f"✅ Accounts Receivable: {ar_account[1]} - {ar_account[2]}")
            print(f"   ID: {ar_account[0]}")
            print(f"   Is Posting Account: {ar_account[3]}")
            if not ar_account[3]:
                print("   ⚠️  WARNING: This is not a posting account!")
        else:
            print("❌ No accounts receivable mapping found!")

        print()
        print()

        # Test Supplier Payment (Bank)
        print("TEST 2: Supplier Payment - Bank Transfer")
        print("-" * 80)

        # Check bank mapping
        result = conn.execute(
            text("""
            SELECT da.account_id, a.account_code, a.account_name, a.is_posting_account
            FROM default_accounts da
            JOIN accounts a ON da.account_id = a.id
            WHERE da.transaction_type = 'bank' 
            AND da.organization_id = :org_id
            LIMIT 1
        """),
            {"org_id": org_id},
        )

        bank_account = result.fetchone()
        if bank_account:
            print(f"✅ Bank Account: {bank_account[1]} - {bank_account[2]}")
            print(f"   ID: {bank_account[0]}")
            print(f"   Is Posting Account: {bank_account[3]}")
            if not bank_account[3]:
                print("   ⚠️  WARNING: This is not a posting account!")
        else:
            print("❌ No bank account mapping found!")

        print()

        # Check accounts_payable mapping
        result = conn.execute(
            text("""
            SELECT da.account_id, a.account_code, a.account_name, a.is_posting_account
            FROM default_accounts da
            JOIN accounts a ON da.account_id = a.id
            WHERE da.transaction_type = 'accounts_payable' 
            AND da.organization_id = :org_id
            LIMIT 1
        """),
            {"org_id": org_id},
        )

        ap_account = result.fetchone()
        if ap_account:
            print(f"✅ Accounts Payable: {ap_account[1]} - {ap_account[2]}")
            print(f"   ID: {ap_account[0]}")
            print(f"   Is Posting Account: {ap_account[3]}")
            if not ap_account[3]:
                print("   ⚠️  WARNING: This is not a posting account!")
        else:
            print("❌ No accounts payable mapping found!")

        print()
        print()

        # Check for non-posting accounts
        print("POTENTIAL ISSUES")
        print("-" * 80)

        result = conn.execute(
            text("""
            SELECT da.transaction_type, a.account_code, a.account_name, a.is_posting_account
            FROM default_accounts da
            JOIN accounts a ON da.account_id = a.id
            WHERE da.organization_id = :org_id
            AND da.transaction_type IN ('cash', 'bank', 'checks_received', 'accounts_receivable', 'accounts_payable')
            AND a.is_posting_account = FALSE
        """),
            {"org_id": org_id},
        )

        non_posting = result.fetchall()

        if non_posting:
            print("⚠️  Found non-posting accounts used in payment mappings:")
            print()
            for row in non_posting:
                print(f"  Transaction Type: {row[0]}")
                print(f"  Account: {row[1]} - {row[2]}")
                print(f"  Is Posting Account: {row[3]}")
                print()
            print("Non-posting accounts (usually group/parent accounts) cannot be used")
            print("in journal entries. You need to map to actual posting accounts.")
        else:
            print("✅ All payment-related accounts are posting accounts")

        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print()
        print("If you see any warnings above, fix them before confirming payments.")
        print("Non-posting accounts will cause journal entry creation to fail.")


if __name__ == "__main__":
    try:
        test_payment_accounts()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
