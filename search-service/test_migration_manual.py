"""Manual test script for verifying migration against PostgreSQL

This script connects to a PostgreSQL database and verifies that the migration
was applied correctly. Run this after applying migrations with:
    alembic upgrade head

Usage:
    python test_migration_manual.py

Requirements:
    - PostgreSQL database running
    - DATABASE_URL environment variable set
    - Migrations applied (alembic upgrade head)
"""

import asyncio
import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def test_migration():
    """Test that migration 001 was applied correctly"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("   Set it to your PostgreSQL connection string:")
        print("   export DATABASE_URL=postgresql://user:pass@host:port/search_db")
        return False
    
    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    print(f"Connecting to database...")
    print(f"URL: {database_url.split('@')[0]}@***")  # Hide credentials
    
    try:
        # Create engine
        engine = create_async_engine(database_url, echo=False)
        
        # Create session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            print("\n" + "=" * 60)
            print("Testing Migration 001: create_search_tables")
            print("=" * 60)
            
            # Test 1: Check tables exist
            print("\n1. Checking tables exist...")
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('search_documents', 'search_configurations')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if 'search_documents' in tables and 'search_configurations' in tables:
                print("   ✓ Both tables exist")
            else:
                print(f"   ❌ Missing tables. Found: {tables}")
                return False
            
            # Test 2: Check search_documents columns
            print("\n2. Checking search_documents columns...")
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'search_documents'
                ORDER BY ordinal_position
            """))
            columns = {row[0]: row[1] for row in result.fetchall()}
            
            required_columns = {
                'id': 'uuid',
                'entity_id': 'character varying',
                'entity_type': 'character varying',
                'title': 'text',
                'content': 'text',
                'metadata': 'jsonb',
                'search_vector': 'tsvector',
                'created_at': 'timestamp with time zone',
                'updated_at': 'timestamp with time zone',
            }
            
            all_present = True
            for col, expected_type in required_columns.items():
                if col in columns:
                    print(f"   ✓ {col} ({columns[col]})")
                else:
                    print(f"   ❌ {col} missing")
                    all_present = False
            
            if not all_present:
                return False
            
            # Test 3: Check indexes
            print("\n3. Checking indexes...")
            result = await session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'search_documents'
                ORDER BY indexname
            """))
            indexes = {row[0]: row[1] for row in result.fetchall()}
            
            required_indexes = [
                'idx_search_documents_vector',
                'idx_search_documents_entity_id',
                'idx_search_documents_entity_type',
                'idx_search_documents_updated_at',
            ]
            
            all_present = True
            for idx in required_indexes:
                if idx in indexes:
                    is_gin = 'gin' in indexes[idx].lower()
                    if idx == 'idx_search_documents_vector' and is_gin:
                        print(f"   ✓ {idx} (GIN)")
                    elif idx == 'idx_search_documents_vector' and not is_gin:
                        print(f"   ⚠ {idx} exists but is not a GIN index")
                    else:
                        print(f"   ✓ {idx}")
                else:
                    print(f"   ❌ {idx} missing")
                    all_present = False
            
            if not all_present:
                return False
            
            # Test 4: Check unique constraint
            print("\n4. Checking unique constraint...")
            result = await session.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'search_documents'
                AND constraint_type = 'UNIQUE'
            """))
            constraints = list(result.fetchall())
            
            if constraints:
                print(f"   ✓ Unique constraint exists: {constraints[0][0]}")
            else:
                print("   ❌ Unique constraint missing")
                return False
            
            # Test 5: Check search_vector is generated
            print("\n5. Checking search_vector is a generated column...")
            result = await session.execute(text("""
                SELECT attname, attgenerated
                FROM pg_attribute
                WHERE attrelid = 'search_documents'::regclass
                AND attname = 'search_vector'
            """))
            row = result.fetchone()
            
            if row and row[1] == 's':
                print("   ✓ search_vector is a stored generated column")
            else:
                print("   ❌ search_vector is not a generated column")
                return False
            
            # Test 6: Check trigger exists
            print("\n6. Checking updated_at trigger...")
            result = await session.execute(text("""
                SELECT tgname
                FROM pg_trigger
                WHERE tgrelid = 'search_documents'::regclass
                AND tgname = 'trigger_update_search_documents_updated_at'
            """))
            row = result.fetchone()
            
            if row:
                print("   ✓ Trigger exists")
            else:
                print("   ❌ Trigger missing")
                return False
            
            # Test 7: Check seeded configurations
            print("\n7. Checking seeded configurations...")
            result = await session.execute(text("""
                SELECT entity_type, searchable_fields, boost_factors
                FROM search_configurations
                ORDER BY entity_type
            """))
            configs = list(result.fetchall())
            
            expected_types = ['customers', 'items', 'stock_entries', 'suppliers', 'warehouses']
            actual_types = [row[0] for row in configs]
            
            if actual_types == expected_types:
                print(f"   ✓ All {len(configs)} entity types configured")
                for config in configs:
                    entity_type = config[0]
                    searchable_fields = config[1]
                    boost_factors = config[2]
                    print(f"     - {entity_type}: {len(searchable_fields)} fields, {len(boost_factors)} boost factors")
            else:
                print(f"   ❌ Expected {expected_types}, got {actual_types}")
                return False
            
            # Test 8: Test search_vector generation
            print("\n8. Testing search_vector generation...")
            try:
                # Insert test document
                await session.execute(text("""
                    INSERT INTO search_documents (entity_id, entity_type, title, content, metadata)
                    VALUES ('test-migration', 'test', 'Test Title', 'Test Content', '{"tags": "test"}')
                """))
                await session.commit()
                
                # Query search_vector
                result = await session.execute(text("""
                    SELECT search_vector::text
                    FROM search_documents
                    WHERE entity_id = 'test-migration'
                """))
                row = result.fetchone()
                
                if row and 'test' in row[0].lower():
                    print("   ✓ search_vector generated correctly")
                else:
                    print("   ❌ search_vector not generated")
                    return False
                
                # Clean up
                await session.execute(text("""
                    DELETE FROM search_documents WHERE entity_id = 'test-migration'
                """))
                await session.commit()
                
            except Exception as e:
                print(f"   ❌ Error testing search_vector: {e}")
                await session.rollback()
                return False
            
            print("\n" + "=" * 60)
            print("✓ All migration tests passed!")
            print("=" * 60)
            return True
        
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. DATABASE_URL is correct")
        print("3. Migrations have been applied (alembic upgrade head)")
        return False
    finally:
        await engine.dispose()


def main():
    """Run the migration tests"""
    print("Migration Test Script")
    print("=" * 60)
    
    result = asyncio.run(test_migration())
    
    if result:
        print("\n✓ Migration verification complete!")
        sys.exit(0)
    else:
        print("\n❌ Migration verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
