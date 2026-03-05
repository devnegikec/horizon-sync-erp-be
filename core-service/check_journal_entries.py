"""
Check if journal entries exist in the database and diagnose UI display issues.
"""

import os
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://horizon_user:horizon_pass@localhost:5432/core_db'
)

def check_journal_entries():
    print("=" * 80)
    print("JOURNAL ENTRIES DIAGNOSTIC")
    print("=" * 80)
    print()
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if journal_entries table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'journal_entries'
            )
        """))
        
        if not result.fetchone()[0]:
            print("❌ journal_entries table does not exist!")
            print("Run database migrations: alembic upgrade head")
            return
        
        print("✅ journal_entries table exists\n")
        
        # Get organization ID
        result = conn.execute(text("SELECT DISTINCT organization_id FROM default_accounts LIMIT 1"))
        org = result.fetchone()
        
        if not org:
            print("❌ No organization found!")
            return
        
        org_id = org[0]
        print(f"Organization ID: {org_id}\n")
        
        # Check total journal entries
        print("STEP 1: Check Journal Entries in Database")
        print("-" * 80)
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM journal_entries
            WHERE organization_id = :org_id
        """), {"org_id": org_id})
        
        total_count = result.fetchone()[0]
        print(f"Total journal entries: {total_count}\n")
        
        if total_count == 0:
            print("❌ No journal entries found in database!")
            print("\nPossible reasons:")
            print("  1. No payments have been confirmed yet")
            print("  2. Payment confirmation is failing silently")
            print("  3. Journal posting service is not being called")
            print("\nTo test:")
            print("  1. Go to Revenue > Payments")
            print("  2. Create a payment and confirm it")
            print("  3. Check backend logs for errors")
            print("  4. Run this script again")
            return
        
        # Show recent journal entries
        print("STEP 2: Recent Journal Entries")
        print("-" * 80)
        
        result = conn.execute(text("""
            SELECT 
                je.id,
                je.entry_number,
                je.posting_date,
                je.voucher_type,
                je.total_debit,
                je.total_credit,
                je.status,
                je.created_at
            FROM journal_entries je
            WHERE je.organization_id = :org_id
            ORDER BY je.created_at DESC
            LIMIT 10
        """), {"org_id": org_id})
        
        entries = result.fetchall()
        
        if entries:
            for entry in entries:
                print(f"Entry Number: {entry[1]}")
                print(f"  ID: {entry[0]}")
                print(f"  Posting Date: {entry[2]}")
                print(f"  Voucher Type: {entry[3]}")
                print(f"  Total Debit: {entry[4]}")
                print(f"  Total Credit: {entry[5]}")
                print(f"  Status: {entry[6]}")
                print(f"  Created At: {entry[7]}")
                print()
        
        # Check journal entry lines
        print("\nSTEP 3: Check Journal Entry Lines")
        print("-" * 80)
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM journal_entry_lines jel
            JOIN journal_entries je ON jel.journal_entry_id = je.id
            WHERE je.organization_id = :org_id
        """), {"org_id": org_id})
        
        lines_count = result.fetchone()[0]
        print(f"Total journal entry lines: {lines_count}\n")
        
        # Show sample lines for first entry
        if entries:
            first_entry_id = entries[0][0]
            
            result = conn.execute(text("""
                SELECT 
                    jel.id,
                    a.account_code,
                    a.account_name,
                    jel.debit,
                    jel.credit,
                    jel.remarks
                FROM journal_entry_lines jel
                JOIN accounts a ON jel.account_id = a.id
                WHERE jel.journal_entry_id = :entry_id
                ORDER BY jel.sort_order
            """), {"entry_id": first_entry_id})
            
            lines = result.fetchall()
            
            if lines:
                print(f"Lines for entry {entries[0][1]}:")
                for line in lines:
                    print(f"  {line[1]} - {line[2]}")
                    print(f"    Debit: {line[3]}, Credit: {line[4]}")
                    print(f"    Remarks: {line[5]}")
                    print()
        
        # Check payment entries with journal entries
        print("\nSTEP 4: Check Payment Entries with Journal Entries")
        print("-" * 80)
        
        result = conn.execute(text("""
            SELECT 
                pe.receipt_number,
                pe.payment_date,
                pe.amount,
                pe.payment_mode,
                pe.status,
                COUNT(je.id) as journal_entry_count
            FROM payment_entries pe
            LEFT JOIN journal_entries je ON je.reference_type = 'PaymentEntry' 
                AND je.reference_id = pe.id
            WHERE pe.organization_id = :org_id
            GROUP BY pe.id, pe.receipt_number, pe.payment_date, pe.amount, pe.payment_mode, pe.status
            ORDER BY pe.created_at DESC
            LIMIT 10
        """), {"org_id": org_id})
        
        payments = result.fetchall()
        
        if payments:
            print(f"Found {len(payments)} recent payments:\n")
            for payment in payments:
                print(f"Receipt: {payment[0]}")
                print(f"  Date: {payment[1]}")
                print(f"  Amount: {payment[2]}")
                print(f"  Mode: {payment[3]}")
                print(f"  Status: {payment[4]}")
                print(f"  Journal Entries: {payment[5]}")
                if payment[5] == 0 and payment[4] == 'confirmed':
                    print(f"  ⚠️  WARNING: Confirmed payment has no journal entry!")
                print()
        else:
            print("No payment entries found")
        
        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)
        
        # Summary
        print("\nSUMMARY:")
        print(f"  - Journal Entries in DB: {total_count}")
        print(f"  - Journal Entry Lines: {lines_count}")
        print(f"  - Recent Payments: {len(payments) if payments else 0}")
        
        if total_count > 0:
            print("\n✅ Journal entries exist in database!")
            print("\nIf they're not showing in UI, check:")
            print("  1. Frontend API call is working (check browser console)")
            print("  2. Backend API endpoint is returning data")
            print("  3. Frontend component is rendering correctly")
            print("  4. Organization ID matches between frontend and backend")
        else:
            print("\n❌ No journal entries in database")
            print("Confirm a payment first, then run this script again")

if __name__ == "__main__":
    try:
        check_journal_entries()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
