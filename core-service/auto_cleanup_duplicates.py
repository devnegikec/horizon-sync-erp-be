#!/usr/bin/env python3
"""
AUTOMATED CUSTOMER DUPLICATE CLEANUP

Removes duplicate customer records automatically, keeping only the latest record per organization_id.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
CORE_DATABASE_URL = os.getenv(
    "CORE_DATABASE_URL", 
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)

def auto_cleanup_duplicates():
    print("🧹 AUTO CUSTOMER DUPLICATE CLEANUP")
    print("=" * 45)
    
    core_engine = create_engine(CORE_DATABASE_URL)
    CoreSession = sessionmaker(bind=core_engine)
    db = CoreSession()
    
    try:
        # Check current state
        total_before = db.execute(text("SELECT COUNT(*) as count FROM customers")).fetchone().count
        unique_orgs = db.execute(text("SELECT COUNT(DISTINCT organization_id) as count FROM customers")).fetchone().count
        
        print(f"📊 Before cleanup: {total_before} records, {unique_orgs} unique organizations")
        
        # Get records to keep (latest for each organization_id)  
        print("🎯 Identifying latest record for each organization...")
        
        # Delete duplicates, keeping only the most recent record per organization_id
        result = db.execute(text("""
            DELETE FROM customers 
            WHERE id NOT IN (
                SELECT DISTINCT ON (organization_id) id
                FROM customers
                ORDER BY organization_id, created_at DESC
            )
        """))
        
        deleted_count = result.rowcount
        
        # Commit the transaction
        db.commit()
        
        # Verify results
        total_after = db.execute(text("SELECT COUNT(*) as count FROM customers")).fetchone().count
        
        print(f"✅ Cleanup completed:")
        print(f"   → Deleted {deleted_count} duplicate records") 
        print(f"   → Remaining records: {total_after}")
        print(f"   → Expected: {unique_orgs} (one per organization)")
        
        if total_after == unique_orgs:
            print("🎉 SUCCESS: No duplicates remaining!")
        else:
            print("⚠️  Manual review may be needed")
            
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
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    auto_cleanup_duplicates()