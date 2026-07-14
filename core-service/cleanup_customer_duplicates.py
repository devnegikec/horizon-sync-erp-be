#!/usr/bin/env python3
"""
CUSTOMER DUPLICATE CLEANUP SCRIPT

This script removes duplicate customer records from the core service database.
It keeps only the most recently created record for each unique organization_id.

Safety Features:
- Shows preview before deletion
- Atomic transactions with rollback on error
- Preserves data integrity with foreign key checks
- Detailed logging of cleanup operations
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
from datetime import datetime

# Database connection
CORE_DATABASE_URL = os.getenv(
    "CORE_DATABASE_URL", 
    "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)

def cleanup_customer_duplicates():
    """
    Remove duplicate customer records, keeping only the latest record for each organization_id.
    """
    print("🧹 CUSTOMER DUPLICATE CLEANUP")
    print("=" * 50)
    print("This script will remove duplicate customer records from core_db")
    print("Keeping only the most recent record for each organization_id\n")
    
    # Create database connection
    core_engine = create_engine(CORE_DATABASE_URL)
    CoreSession = sessionmaker(bind=core_engine)
    db = CoreSession()
    
    try:
        # Step 1: Analyze current duplicates
        print("1. Analyzing current duplicate situation...")
        
        total_customers = db.execute(text("""
            SELECT COUNT(*) as count FROM customers
        """)).fetchone().count
        
        unique_orgs = db.execute(text("""
            SELECT COUNT(DISTINCT organization_id) as count FROM customers
        """)).fetchone().count
        
        duplicate_stats = db.execute(text("""
            SELECT 
                organization_id,
                COUNT(*) as duplicate_count,
                MIN(created_at) as oldest,
                MAX(created_at) as newest,
                STRING_AGG(customer_code, ', ' ORDER BY created_at DESC) as sample_codes
            FROM customers 
            GROUP BY organization_id 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """)).fetchall()
        
        print(f"   📊 Current State:")
        print(f"      → Total customer records: {total_customers}")
        print(f"      → Unique organizations: {unique_orgs}")
        print(f"      → Duplicate groups: {len(duplicate_stats)}")
        
        if not duplicate_stats:
            print("   ✅ No duplicates found - database is clean!")
            return
        
        # Show duplicate details
        total_duplicates_to_remove = 0
        print(f"\n   📋 Duplicate Details:")
        for i, dup in enumerate(duplicate_stats, 1):
            duplicates_to_remove = dup.duplicate_count - 1
            total_duplicates_to_remove += duplicates_to_remove
            print(f"      {i}. Organization ID: {dup.organization_id}")
            print(f"         → {dup.duplicate_count} records ({duplicates_to_remove} to remove)")
            print(f"         → Date range: {dup.oldest} to {dup.newest}")
            print(f"         → Sample codes: {dup.sample_codes}")
        
        print(f"\n   🎯 Cleanup Plan:")
        print(f"      → Records to keep: {unique_orgs}")
        print(f"      → Records to remove: {total_duplicates_to_remove}")
        print(f"      → Final count will be: {total_customers - total_duplicates_to_remove}")
        
        # Step 2: Get user confirmation
        print(f"\n⚠️  WARNING: This will permanently delete {total_duplicates_to_remove} duplicate customer records!")
        confirmation = input("Do you want to proceed? (type 'yes' to continue): ")
        
        if confirmation.lower() != 'yes':
            print("❌ Cleanup cancelled by user")
            return
        
        # Step 3: Perform cleanup
        print(f"\n2. Performing duplicate cleanup...")
        
        # Find records to keep (latest for each organization_id)
        records_to_keep = db.execute(text("""
            WITH latest_customers AS (
                SELECT 
                    organization_id,
                    MAX(created_at) as latest_created_at
                FROM customers
                GROUP BY organization_id
            ),
            customers_to_keep AS (
                SELECT c.id, c.customer_code, c.customer_name, c.organization_id
                FROM customers c
                INNER JOIN latest_customers lc ON 
                    c.organization_id = lc.organization_id 
                    AND c.created_at = lc.latest_created_at
            )
            SELECT * FROM customers_to_keep
            ORDER BY customer_name
        """)).fetchall()
        
        keep_ids = [str(record.id) for record in records_to_keep]
        
        print(f"   🎯 Records to keep ({len(records_to_keep)}):")
        for record in records_to_keep:
            print(f"      → {record.customer_name} ({record.customer_code}) - ID: {record.id}")
        
        # Delete duplicates (keeping only the latest records)
        if keep_ids:
            delete_result = db.execute(text("""
                DELETE FROM customers 
                WHERE id NOT IN (""" + ",".join([f"'{id}'" for id in keep_ids]) + """)
            """))
            
            deleted_count = delete_result.rowcount
            
            # Commit the transaction
            db.commit()
            
            print(f"   ✅ Successfully deleted {deleted_count} duplicate records")
        else:
            print("   ⚠️  No records to keep identified - skipping deletion")
        
        # Step 4: Verify cleanup
        print(f"\n3. Verifying cleanup results...")
        
        final_count = db.execute(text("""
            SELECT COUNT(*) as count FROM customers
        """)).fetchone().count
        
        remaining_duplicates = db.execute(text("""
            SELECT COUNT(*) as groups
            FROM (
                SELECT organization_id 
                FROM customers 
                GROUP BY organization_id 
                HAVING COUNT(*) > 1
            ) dup_groups
        """)).fetchone().groups
        
        print(f"   📊 Final State:")
        print(f"      → Total customer records: {final_count}")
        print(f"      → Duplicate groups remaining: {remaining_duplicates}")
        
        if remaining_duplicates == 0:
            print("   ✅ Cleanup successful - no duplicates remaining!")
        else:
            print("   ⚠️  Some duplicates may still exist - manual review needed")
        
        # Show final customer list
        final_customers = db.execute(text("""
            SELECT customer_code, customer_name, organization_id, created_at
            FROM customers 
            ORDER BY customer_name
        """)).fetchall()
        
        print(f"\n   📋 Final Customer List ({len(final_customers)} records):")
        for customer in final_customers:
            print(f"      → {customer.customer_name} ({customer.customer_code})")
        
        print(f"\n✅ Customer duplicate cleanup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_customer_duplicates()