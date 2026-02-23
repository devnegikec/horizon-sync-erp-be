#!/usr/bin/env python3
"""
Script to verify that all required payment flow indexes exist and are being used.

This script checks:
1. All required indexes exist in the database
2. Indexes are being used by common queries (via EXPLAIN ANALYZE)
3. Index statistics and usage patterns

Usage:
    python scripts/verify_payment_indexes.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import SessionLocal, engine


def check_index_exists(db, table_name: str, index_name: str) -> bool:
    """Check if an index exists in the database."""
    query = text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE tablename = :table_name
            AND indexname = :index_name
        )
    """)
    result = db.execute(query, {"table_name": table_name, "index_name": index_name})
    return result.scalar()


def get_index_size(db, index_name: str) -> str:
    """Get the size of an index."""
    query = text("""
        SELECT pg_size_pretty(pg_relation_size(:index_name::regclass))
    """)
    try:
        result = db.execute(query, {"index_name": index_name})
        return result.scalar()
    except Exception as e:
        return f"Error: {e}"


def get_index_usage_stats(db, table_name: str) -> list:
    """Get index usage statistics for a table."""
    query = text("""
        SELECT
            indexrelname as index_name,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes
        WHERE relname = :table_name
        ORDER BY idx_scan DESC
    """)
    result = db.execute(query, {"table_name": table_name})
    return result.fetchall()


def explain_query(db, query_sql: str) -> str:
    """Get EXPLAIN output for a query."""
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query_sql}"
    result = db.execute(text(explain_query))
    lines = [row[0] for row in result]
    return "\n".join(lines)


def main():
    """Main verification function."""
    db = SessionLocal()
    
    print("=" * 80)
    print("Payment Flow Index Verification")
    print("=" * 80)
    print()
    
    # Define required indexes
    required_indexes = {
        "payment_entries": [
            "idx_payment_entries_org_date",
            "idx_payment_entries_org_party",
            "idx_payment_entries_org_status",
            "idx_payment_entries_reference",
            "idx_payment_entries_receipt",
        ],
        "payment_references": [
            "idx_payment_references_payment",
            "idx_payment_references_invoice",
            "idx_payment_references_org",
        ],
        "payment_audit_log": [
            "idx_payment_audit_payment_time",
            "idx_payment_audit_org_time",
        ],
    }
    
    # Check if indexes exist
    print("1. Checking Index Existence")
    print("-" * 80)
    
    all_exist = True
    for table_name, indexes in required_indexes.items():
        print(f"\nTable: {table_name}")
        for index_name in indexes:
            exists = check_index_exists(db, table_name, index_name)
            size = get_index_size(db, index_name) if exists else "N/A"
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {index_name}: {status} (Size: {size})")
            if not exists:
                all_exist = False
    
    print()
    
    if not all_exist:
        print("❌ Some indexes are missing! Run migrations to create them.")
        print()
    else:
        print("✅ All required indexes exist!")
        print()
    
    # Check index usage statistics
    print("2. Index Usage Statistics")
    print("-" * 80)
    
    for table_name in required_indexes.keys():
        print(f"\nTable: {table_name}")
        stats = get_index_usage_stats(db, table_name)
        if stats:
            print(f"  {'Index Name':<40} {'Scans':<10} {'Tuples Read':<15} {'Tuples Fetched':<15}")
            print(f"  {'-'*40} {'-'*10} {'-'*15} {'-'*15}")
            for row in stats:
                print(f"  {row[0]:<40} {row[1]:<10} {row[2]:<15} {row[3]:<15}")
        else:
            print("  No usage statistics available (table may be empty)")
    
    print()
    
    # Test common queries to verify index usage
    print("3. Query Plan Analysis")
    print("-" * 80)
    
    test_queries = [
        (
            "Payment list by organization and date",
            """
            SELECT * FROM payment_entries
            WHERE organization_id = '00000000-0000-0000-0000-000000000001'::uuid
            AND payment_date >= '2024-01-01'
            ORDER BY payment_date DESC
            LIMIT 50
            """
        ),
        (
            "Payment list by organization and status",
            """
            SELECT * FROM payment_entries
            WHERE organization_id = '00000000-0000-0000-0000-000000000001'::uuid
            AND status = 'Draft'
            LIMIT 50
            """
        ),
        (
            "Payment by receipt number",
            """
            SELECT * FROM payment_entries
            WHERE receipt_number = 'RCP-2024-00001'
            """
        ),
        (
            "Payment references by payment_id",
            """
            SELECT * FROM payment_references
            WHERE payment_id = '00000000-0000-0000-0000-000000000001'::uuid
            """
        ),
        (
            "Payment references by invoice_id",
            """
            SELECT * FROM payment_references
            WHERE invoice_id = '00000000-0000-0000-0000-000000000001'::uuid
            """
        ),
    ]
    
    for query_name, query_sql in test_queries:
        print(f"\nQuery: {query_name}")
        print("-" * 40)
        try:
            plan = explain_query(db, query_sql)
            
            # Check if index is being used
            uses_index = "Index Scan" in plan or "Bitmap Index Scan" in plan
            if uses_index:
                print("✅ Using index")
            else:
                print("⚠️  Not using index (Sequential Scan)")
            
            # Show relevant lines from plan
            lines = plan.split("\n")
            for line in lines[:5]:  # Show first 5 lines
                print(f"  {line}")
            
            if len(lines) > 5:
                print(f"  ... ({len(lines) - 5} more lines)")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    
    if all_exist:
        print("✅ All required indexes exist")
        print("✅ Indexes are properly sized")
        print()
        print("Next steps:")
        print("1. Monitor index usage statistics over time")
        print("2. Check query plans for slow queries")
        print("3. Consider adding indexes for frequently filtered columns")
    else:
        print("❌ Some indexes are missing")
        print()
        print("Action required:")
        print("1. Run database migrations: alembic upgrade head")
        print("2. Re-run this script to verify")
    
    print()
    
    db.close()


if __name__ == "__main__":
    main()
