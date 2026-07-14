#!/usr/bin/env python3
"""
SMART CUSTOMER DUPLICATE CLEANUP WITH FOREIGN KEY HANDLING

This script safely removes duplicate customer records by:
1. Identifying foreign key relationships
2. Updating references to point to the record we want to keep
3. Then deleting duplicate records
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
CORE_DATABASE_URL = os.getenv(
    "CORE_DATABASE_URL", 
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)

def safe_cleanup_customer_duplicates():
    print("🔒 SAFE CUSTOMER DUPLICATE CLEANUP (WITH FOREIGN KEY HANDLING)")
    print("=" * 70)
    
    core_engine = create_engine(CORE_DATABASE_URL)
    CoreSession = sessionmaker(bind=core_engine)
    db = CoreSession()
    
    try:
        # Step 1: Analyze current situation
        print("1. Analyzing duplicate situation...")
        
        total_customers = db.execute(text("SELECT COUNT(*) as count FROM customers")).fetchone().count
        unique_orgs = db.execute(text("SELECT COUNT(DISTINCT organization_id) as count FROM customers")).fetchone().count
        
        duplicates = db.execute(text("""
            SELECT organization_id, COUNT(*) as count
            FROM customers 
            GROUP BY organization_id 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """)).fetchall()
        
        print(f"   📊 Current state: {total_customers} total, {unique_orgs} unique orgs, {len(duplicates)} duplicate groups")
        
        if not duplicates:
            print("   ✅ No duplicates found!")
            return
        
        # Step 2: For each duplicate group, handle foreign keys and cleanup
        total_deleted = 0
        
        for dup in duplicates:
            org_id = dup.organization_id
            dup_count = dup.count
            
            print(f"\n2. Processing organization {org_id} ({dup_count} duplicates)...")
            
            # Get all customer records for this organization (ordered by created_at DESC)
            org_customers = db.execute(text("""
                SELECT id, customer_code, customer_name, created_at
                FROM customers 
                WHERE organization_id = :org_id
                ORDER BY created_at DESC
            """), {'org_id': org_id}).fetchall()
            
            # Keep the most recent record, delete the rest
            keep_customer = org_customers[0]  # Most recent
            delete_customers = org_customers[1:]  # Older ones
            
            print(f"   → Keeping: {keep_customer.customer_name} ({keep_customer.customer_code}) - {keep_customer.created_at}")
            print(f"   → Deleting {len(delete_customers)} older records")
            
            # Step 3: Handle foreign key references
            for old_customer in delete_customers:
                print(f"   🔗 Checking references for customer {old_customer.customer_code}...")
                
                # Check for foreign key references
                
                # 1. Check quotations table (ON DELETE RESTRICT)
                quotation_refs = db.execute(text("""
                    SELECT COUNT(*) as count FROM quotations 
                    WHERE customer_id = :old_id
                """), {'old_id': old_customer.id}).fetchone().count
                
                if quotation_refs > 0:
                    print(f"      → Updating {quotation_refs} quotations to reference kept customer")
                    db.execute(text("""
                        UPDATE quotations 
                        SET customer_id = :new_id, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = :old_id
                    """), {'new_id': keep_customer.id, 'old_id': old_customer.id})
                
                # 2. Check sales_orders table (ON DELETE RESTRICT)
                sales_order_refs = db.execute(text("""
                    SELECT COUNT(*) as count FROM sales_orders 
                    WHERE customer_id = :old_id
                """), {'old_id': old_customer.id}).fetchone().count
                
                if sales_order_refs > 0:
                    print(f"      → Updating {sales_order_refs} sales orders to reference kept customer")
                    db.execute(text("""
                        UPDATE sales_orders 
                        SET customer_id = :new_id, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = :old_id
                    """), {'new_id': keep_customer.id, 'old_id': old_customer.id})
                
                # 3. Check delivery_notes table (ON DELETE CASCADE - but we'll update anyway)
                delivery_note_refs = db.execute(text("""
                    SELECT COUNT(*) as count FROM delivery_notes 
                    WHERE customer_id = :old_id
                """), {'old_id': old_customer.id}).fetchone().count
                
                if delivery_note_refs > 0:
                    print(f"      → Updating {delivery_note_refs} delivery notes to reference kept customer")
                    db.execute(text("""
                        UPDATE delivery_notes 
                        SET customer_id = :new_id, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = :old_id
                    """), {'new_id': keep_customer.id, 'old_id': old_customer.id})
            
            # Step 4: Now safe to delete the duplicate customers
            delete_ids = [str(customer.id) for customer in delete_customers]
            if delete_ids:
                print(f"   🗑️  Deleting {len(delete_ids)} duplicate customers...")
                
                result = db.execute(text(f"""
                    DELETE FROM customers 
                    WHERE id IN ({','.join([f"'{id}'" for id in delete_ids])})
                """))
                
                deleted_count = result.rowcount
                total_deleted += deleted_count
                print(f"   ✅ Deleted {deleted_count} records for this organization")
        
        # Step 5: Commit all changes
        db.commit()
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   → Total records deleted: {total_deleted}")
        
        # Step 6: Verify final state
        final_count = db.execute(text("SELECT COUNT(*) as count FROM customers")).fetchone().count
        final_unique = db.execute(text("SELECT COUNT(DISTINCT organization_id) as count FROM customers")).fetchone().count
        
        print(f"\n📊 Final state:")
        print(f"   → Total customer records: {final_count}")
        print(f"   → Unique organizations: {final_unique}")
        
        if final_count == final_unique:
            print("   🎉 SUCCESS: No duplicates remaining!")
        else:
            print("   ⚠️  Some duplicates may still exist")
        
        # Show final customers
        final_customers = db.execute(text("""
            SELECT customer_code, customer_name, organization_id, created_at
            FROM customers 
            ORDER BY customer_name
        """)).fetchall()
        
        print(f"\n📋 Final Customer List ({len(final_customers)} records):")
        for customer in final_customers:
            print(f"   → {customer.customer_name} ({customer.customer_code})")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    safe_cleanup_customer_duplicates()