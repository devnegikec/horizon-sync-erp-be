"""
Cleanup script for payment testing data.
Removes all payments, allocations, invoices, and related data to start fresh.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)


def cleanup_payment_test_data():
    """Remove all payment-related test data"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("\n" + "="*60)
        print("PAYMENT SYSTEM DATA CLEANUP")
        print("="*60 + "\n")

        # Get organization ID from default_accounts (since organizations is in different DB)
        result = db.execute(text("SELECT DISTINCT organization_id FROM default_accounts LIMIT 1"))
        org_row = result.fetchone()
        
        if not org_row:
            print("❌ No organization found in default_accounts.")
            print("   Cannot determine organization ID.")
            return
        
        org_id = org_row[0]
        print(f"✓ Using Organization ID: {org_id}\n")

        # 1. Delete Payment Audit Log (table name: payment_audit_log, not payment_audit_logs)
        print("1. Deleting payment audit log...")
        try:
            result = db.execute(text("""
                DELETE FROM payment_audit_log 
                WHERE organization_id = :org_id
            """), {"org_id": org_id})
            print(f"   ✓ Deleted {result.rowcount} audit log entries\n")
        except Exception as e:
            print(f"   ⚠ Skipped (table may not exist): {e}\n")

        # 2. Delete Payment Allocations (table name: payment_allocations)
        print("2. Deleting payment allocations...")
        try:
            result = db.execute(text("""
                DELETE FROM payment_allocations 
                WHERE organization_id = :org_id
            """), {"org_id": org_id})
            print(f"   ✓ Deleted {result.rowcount} payment allocations\n")
        except Exception as e:
            print(f"   ⚠ Skipped (table may not exist): {e}\n")

        # 3. Delete Payment References
        print("3. Deleting payment references...")
        result = db.execute(text("""
            DELETE FROM payment_references 
            WHERE organization_id = :org_id
        """), {"org_id": org_id})
        print(f"   ✓ Deleted {result.rowcount} payment references\n")

        # 4. Delete Payment Entries
        print("4. Deleting payment entries...")
        result = db.execute(text("""
            DELETE FROM payment_entries 
            WHERE organization_id = :org_id
        """), {"org_id": org_id})
        print(f"   ✓ Deleted {result.rowcount} payment entries\n")

        # 5. Delete Payments (if different from payment_entries)
        print("5. Deleting payments...")
        try:
            result = db.execute(text("""
                DELETE FROM payments 
                WHERE organization_id = :org_id
            """), {"org_id": org_id})
            print(f"   ✓ Deleted {result.rowcount} payments\n")
        except Exception as e:
            print(f"   ⚠ Skipped (table may not exist): {e}\n")

        # 6. Delete Journal Entry Lines
        print("6. Deleting journal entry lines...")
        result = db.execute(text("""
            DELETE FROM journal_entry_lines 
            WHERE journal_entry_id IN (
                SELECT id FROM journal_entries 
                WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        print(f"   ✓ Deleted {result.rowcount} journal entry lines\n")

        # 7. Delete Journal Entries
        print("7. Deleting journal entries...")
        result = db.execute(text("""
            DELETE FROM journal_entries 
            WHERE organization_id = :org_id
        """), {"org_id": org_id})
        print(f"   ✓ Deleted {result.rowcount} journal entries\n")

        # 8. Delete Invoice Items
        print("8. Deleting invoice items...")
        result = db.execute(text("""
            DELETE FROM invoice_items 
            WHERE invoice_id IN (
                SELECT id FROM invoices 
                WHERE organization_id = :org_id
            )
        """), {"org_id": org_id})
        print(f"   ✓ Deleted {result.rowcount} invoice items\n")

        # 9. Delete Invoices
        print("9. Deleting invoices...")
        result = db.execute(text("""
            DELETE FROM invoices 
            WHERE organization_id = :org_id
        """), {"org_id": org_id})
        print(f"   ✓ Deleted {result.rowcount} invoices\n")

        # 10. Delete Quotation Items (must delete before quotations)
        print("10. Deleting quotation items...")
        try:
            result = db.execute(text("""
                DELETE FROM quotation_items 
                WHERE quotation_id IN (
                    SELECT id FROM quotations 
                    WHERE organization_id = :org_id
                )
            """), {"org_id": org_id})
            print(f"   ✓ Deleted {result.rowcount} quotation items\n")
        except Exception as e:
            print(f"   ⚠ Skipped: {e}\n")

        # 11. Delete Quotations (must delete before customers)
        print("11. Deleting quotations...")
        try:
            result = db.execute(text("""
                DELETE FROM quotations 
                WHERE organization_id = :org_id
            """), {"org_id": org_id})
            print(f"   ✓ Deleted {result.rowcount} quotations\n")
        except Exception as e:
            print(f"   ⚠ Skipped: {e}\n")

        # 12. Delete Customers (OPTIONAL - only if you want to remove all customers)
        print("12. Deleting customers (OPTIONAL - skipping to preserve data)...")
        # Uncomment the lines below if you want to delete ALL customers
        # result = db.execute(text("""
        #     DELETE FROM customers 
        #     WHERE organization_id = :org_id
        # """), {"org_id": org_id})
        # print(f"   ✓ Deleted {result.rowcount} customers\n")
        print(f"   ⚠ Skipped (preserving existing customers)\n")

        # 13. Delete Suppliers (OPTIONAL - only if you want to remove all suppliers)
        print("13. Deleting suppliers (OPTIONAL - skipping to preserve data)...")
        # Uncomment the lines below if you want to delete ALL suppliers
        # result = db.execute(text("""
        #     DELETE FROM suppliers 
        #     WHERE organization_id = :org_id
        # """), {"org_id": org_id})
        # print(f"   ✓ Deleted {result.rowcount} suppliers\n")
        print(f"   ⚠ Skipped (preserving existing suppliers)\n")

        # 14. Reset document numbering sequences (table name: document_sequence_counter)
        print("14. Resetting document numbering sequences...")
        try:
            result = db.execute(text("""
                UPDATE document_sequence_counter 
                SET current_number = 0 
                WHERE organization_id = :org_id 
                AND document_type IN ('payment', 'invoice', 'customer', 'supplier', 'journal_entry')
            """), {"org_id": org_id})
            print(f"   ✓ Reset {result.rowcount} document numbering sequences\n")
        except Exception as e:
            print(f"   ⚠ Skipped (table may not exist): {e}\n")

        # Commit all changes
        db.commit()

        print("="*60)
        print("✅ CLEANUP COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nYou can now run the seed script to create fresh test data.")
        print("\nNext steps:")
        print("1. python seed_payment_test_data.py")
        print("2. Restart backend server")
        print("3. Test payment confirmation in UI")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during cleanup: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_payment_test_data()
