"""Manual verification script for search database schema

This script verifies that the search_documents table and search_configurations
table are correctly created with all required features.

Run with: python verify_schema.py
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def verify_schema():
    """Verify the search database schema"""
    # Get database URL from environment
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/search_db"
    )

    # Convert to async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Create engine
    engine = create_async_engine(database_url, echo=False)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 80)
    print("SEARCH DATABASE SCHEMA VERIFICATION")
    print("=" * 80)
    print()

    async with async_session() as session:
        # Test 1: Verify search_documents table exists
        print("✓ Test 1: Checking search_documents table structure...")
        result = await session.execute(
            text(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'search_documents'
                ORDER BY ordinal_position
                """
            )
        )
        columns = result.fetchall()

        if not columns:
            print("  ✗ FAILED: search_documents table not found")
            return False

        column_names = [col[0] for col in columns]
        required_columns = [
            "id",
            "entity_id",
            "entity_type",
            "title",
            "content",
            "metadata",
            "search_vector",
            "created_at",
            "updated_at",
        ]

        for col in required_columns:
            if col in column_names:
                print(f"  ✓ Column '{col}' exists")
            else:
                print(f"  ✗ Column '{col}' missing")
                return False

        # Test 2: Verify GIN index on search_vector
        print("\n✓ Test 2: Checking GIN index on search_vector...")
        result = await session.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'search_documents'
                AND indexname = 'idx_search_documents_vector'
                """
            )
        )
        index = result.fetchone()

        if index and "gin" in index[1].lower():
            print(f"  ✓ GIN index exists: {index[0]}")
        else:
            print("  ✗ FAILED: GIN index not found")
            return False

        # Test 3: Verify other indexes
        print("\n✓ Test 3: Checking other indexes...")
        indexes_to_check = [
            "idx_search_documents_entity_id",
            "idx_search_documents_entity_type",
            "idx_search_documents_updated_at",
        ]

        for idx_name in indexes_to_check:
            result = await session.execute(
                text(
                    f"""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'search_documents'
                    AND indexname = '{idx_name}'
                    """
                )
            )
            index = result.fetchone()

            if index:
                print(f"  ✓ Index '{idx_name}' exists")
            else:
                print(f"  ✗ Index '{idx_name}' missing")
                return False

        # Test 4: Verify unique constraint
        print("\n✓ Test 4: Checking unique constraint...")
        result = await session.execute(
            text(
                """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'search_documents'
                AND constraint_type = 'UNIQUE'
                AND constraint_name = 'uq_entity_id_type'
                """
            )
        )
        constraint = result.fetchone()

        if constraint:
            print(f"  ✓ Unique constraint exists: {constraint[0]}")
        else:
            print("  ✗ FAILED: Unique constraint not found")
            return False

        # Test 5: Verify search_configurations table
        print("\n✓ Test 5: Checking search_configurations table...")
        result = await session.execute(
            text(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'search_configurations'
                ORDER BY ordinal_position
                """
            )
        )
        columns = result.fetchall()

        if not columns:
            print("  ✗ FAILED: search_configurations table not found")
            return False

        column_names = [col[0] for col in columns]
        required_columns = [
            "entity_type",
            "searchable_fields",
            "boost_factors",
            "filters",
            "created_at",
        ]

        for col in required_columns:
            if col in column_names:
                print(f"  ✓ Column '{col}' exists")
            else:
                print(f"  ✗ Column '{col}' missing")
                return False

        # Test 6: Verify default configurations
        print("\n✓ Test 6: Checking default search configurations...")
        result = await session.execute(
            text("SELECT entity_type FROM search_configurations ORDER BY entity_type")
        )
        entity_types = [row[0] for row in result.fetchall()]

        expected_types = [
            "customers",
            "items",
            "stock_entries",
            "suppliers",
            "warehouses",
        ]

        if entity_types == expected_types:
            print(f"  ✓ All {len(entity_types)} default configurations exist")
            for et in entity_types:
                print(f"    - {et}")
        else:
            print(f"  ✗ FAILED: Expected {expected_types}, got {entity_types}")
            return False

        # Test 7: Test full-text search functionality
        print("\n✓ Test 7: Testing full-text search functionality...")

        # Insert a test document
        await session.execute(
            text(
                """
                INSERT INTO search_documents (entity_id, entity_type, title, content, metadata)
                VALUES ('verify-001', 'items', 'Test Laptop Computer', 'High performance laptop', '{"tags": "electronics"}')
                ON CONFLICT (entity_id, entity_type) DO UPDATE SET title = EXCLUDED.title
                """
            )
        )
        await session.commit()

        # Search for it
        result = await session.execute(
            text(
                """
                SELECT entity_id, title, ts_rank(search_vector, to_tsquery('english', 'laptop')) as rank
                FROM search_documents
                WHERE entity_id = 'verify-001'
                AND search_vector @@ to_tsquery('english', 'laptop')
                """
            )
        )
        row = result.fetchone()

        if row and row[0] == "verify-001":
            print(f"  ✓ Full-text search works (rank: {row[2]:.4f})")
        else:
            print("  ✗ FAILED: Full-text search not working")
            return False

        # Test 8: Verify search_vector auto-generation
        print("\n✓ Test 8: Testing search_vector auto-generation...")
        result = await session.execute(
            text(
                """
                SELECT search_vector IS NOT NULL as has_vector
                FROM search_documents
                WHERE entity_id = 'verify-001'
                """
            )
        )
        row = result.fetchone()

        if row and row[0]:
            print("  ✓ search_vector is automatically generated")
        else:
            print("  ✗ FAILED: search_vector not generated")
            return False

        # Clean up
        await session.execute(
            text("DELETE FROM search_documents WHERE entity_id = 'verify-001'")
        )
        await session.commit()

    await engine.dispose()

    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED - Schema is correctly configured!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(verify_schema())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
