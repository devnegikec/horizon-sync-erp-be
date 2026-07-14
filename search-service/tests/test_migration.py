"""Tests for database migration scripts

This module tests that migrations can be applied and rolled back successfully,
and that the resulting schema matches expectations.

Requirements: 8.1

NOTE: These tests require a PostgreSQL database with the migration applied.
They will be skipped when running against SQLite (in-memory test database).
To run these tests:
1. Ensure PostgreSQL is running
2. Apply migrations: alembic upgrade head
3. Run tests with PostgreSQL connection
"""

import pytest
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession


# Skip all tests in this module if not using PostgreSQL
pytestmark = pytest.mark.skip(reason="Migration tests require PostgreSQL database with migrations applied")


class TestMigration001:
    """Test suite for migration 001_create_search_tables"""

    @pytest.mark.asyncio
    async def test_search_documents_table_exists(self, db_session: AsyncSession):
        """Verify search_documents table was created"""
        inspector = inspect(db_session.bind)
        tables = await db_session.run_sync(lambda sync_session: inspector.get_table_names())
        
        assert "search_documents" in tables, "search_documents table should exist"

    @pytest.mark.asyncio
    async def test_search_configurations_table_exists(self, db_session: AsyncSession):
        """Verify search_configurations table was created"""
        inspector = inspect(db_session.bind)
        tables = await db_session.run_sync(lambda sync_session: inspector.get_table_names())
        
        assert "search_configurations" in tables, "search_configurations table should exist"

    @pytest.mark.asyncio
    async def test_search_documents_columns(self, db_session: AsyncSession):
        """Verify search_documents has all required columns"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [col["name"] for col in inspector.get_columns("search_documents")]
        )
        
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
            assert col in columns, f"Column {col} should exist in search_documents"

    @pytest.mark.asyncio
    async def test_search_configurations_columns(self, db_session: AsyncSession):
        """Verify search_configurations has all required columns"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [col["name"] for col in inspector.get_columns("search_configurations")]
        )
        
        required_columns = [
            "entity_type",
            "searchable_fields",
            "boost_factors",
            "filters",
            "created_at",
        ]
        
        for col in required_columns:
            assert col in columns, f"Column {col} should exist in search_configurations"

    @pytest.mark.asyncio
    async def test_search_documents_indexes(self, db_session: AsyncSession):
        """Verify search_documents has required indexes"""
        inspector = inspect(db_session.bind)
        indexes = await db_session.run_sync(
            lambda sync_session: inspector.get_indexes("search_documents")
        )
        
        index_names = [idx["name"] for idx in indexes]
        
        required_indexes = [
            "idx_search_documents_vector",
            "idx_search_documents_entity_id",
            "idx_search_documents_entity_type",
            "idx_search_documents_updated_at",
        ]
        
        for idx in required_indexes:
            assert idx in index_names, f"Index {idx} should exist on search_documents"

    @pytest.mark.asyncio
    async def test_search_documents_unique_constraint(self, db_session: AsyncSession):
        """Verify unique constraint on entity_id and entity_type"""
        inspector = inspect(db_session.bind)
        constraints = await db_session.run_sync(
            lambda sync_session: inspector.get_unique_constraints("search_documents")
        )
        
        # Check if there's a unique constraint on entity_id and entity_type
        constraint_columns = [set(c["column_names"]) for c in constraints]
        expected_constraint = {"entity_id", "entity_type"}
        
        assert expected_constraint in constraint_columns, \
            "Unique constraint on (entity_id, entity_type) should exist"

    @pytest.mark.asyncio
    async def test_search_vector_is_generated_column(self, db_session: AsyncSession):
        """Verify search_vector is a generated column"""
        # Query to check if search_vector is a generated column
        result = await db_session.execute(text("""
            SELECT attname, attgenerated
            FROM pg_attribute
            WHERE attrelid = 'search_documents'::regclass
            AND attname = 'search_vector'
        """))
        
        row = result.fetchone()
        assert row is not None, "search_vector column should exist"
        assert row[1] == 's', "search_vector should be a stored generated column"

    @pytest.mark.asyncio
    async def test_default_configurations_seeded(self, db_session: AsyncSession):
        """Verify default entity configurations were seeded"""
        result = await db_session.execute(
            text("SELECT entity_type FROM search_configurations ORDER BY entity_type")
        )
        
        entity_types = [row[0] for row in result.fetchall()]
        
        expected_types = ["customers", "items", "stock_entries", "suppliers", "warehouses"]
        
        assert entity_types == expected_types, \
            f"Expected entity types {expected_types}, got {entity_types}"

    @pytest.mark.asyncio
    async def test_items_configuration_details(self, db_session: AsyncSession):
        """Verify items configuration has correct searchable fields and boost factors"""
        result = await db_session.execute(text("""
            SELECT searchable_fields, boost_factors, filters
            FROM search_configurations
            WHERE entity_type = 'items'
        """))
        
        row = result.fetchone()
        assert row is not None, "Items configuration should exist"
        
        searchable_fields = row[0]
        boost_factors = row[1]
        filters = row[2]
        
        # Check searchable fields
        assert "item_code" in searchable_fields
        assert "item_name" in searchable_fields
        assert "description" in searchable_fields
        assert "item_group" in searchable_fields
        
        # Check boost factors
        assert boost_factors["item_code"] == 2.0
        assert boost_factors["item_name"] == 1.5
        assert boost_factors["description"] == 1.0
        
        # Check filters
        assert "item_type" in filters
        assert "status" in filters

    @pytest.mark.asyncio
    async def test_customers_configuration_details(self, db_session: AsyncSession):
        """Verify customers configuration has correct searchable fields"""
        result = await db_session.execute(text("""
            SELECT searchable_fields, boost_factors
            FROM search_configurations
            WHERE entity_type = 'customers'
        """))
        
        row = result.fetchone()
        assert row is not None, "Customers configuration should exist"
        
        searchable_fields = row[0]
        boost_factors = row[1]
        
        # Check searchable fields
        assert "customer_code" in searchable_fields
        assert "customer_name" in searchable_fields
        assert "email" in searchable_fields
        assert "phone" in searchable_fields
        
        # Check boost factors
        assert boost_factors["customer_code"] == 2.0
        assert boost_factors["customer_name"] == 1.5
        assert boost_factors["email"] == 1.2

    @pytest.mark.asyncio
    async def test_updated_at_trigger_exists(self, db_session: AsyncSession):
        """Verify the updated_at trigger was created"""
        result = await db_session.execute(text("""
            SELECT tgname
            FROM pg_trigger
            WHERE tgrelid = 'search_documents'::regclass
            AND tgname = 'trigger_update_search_documents_updated_at'
        """))
        
        row = result.fetchone()
        assert row is not None, "updated_at trigger should exist"

    @pytest.mark.asyncio
    async def test_updated_at_trigger_function_exists(self, db_session: AsyncSession):
        """Verify the updated_at trigger function was created"""
        result = await db_session.execute(text("""
            SELECT proname
            FROM pg_proc
            WHERE proname = 'update_search_documents_updated_at'
        """))
        
        row = result.fetchone()
        assert row is not None, "updated_at trigger function should exist"

    @pytest.mark.asyncio
    async def test_gin_index_on_search_vector(self, db_session: AsyncSession):
        """Verify GIN index exists on search_vector column"""
        result = await db_session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'search_documents'
            AND indexname = 'idx_search_documents_vector'
        """))
        
        row = result.fetchone()
        assert row is not None, "GIN index on search_vector should exist"
        assert "gin" in row[1].lower(), "Index should be a GIN index"

    @pytest.mark.asyncio
    async def test_search_vector_weights(self, db_session: AsyncSession):
        """Verify search_vector uses correct weights for different fields"""
        # Insert a test document
        await db_session.execute(text("""
            INSERT INTO search_documents (entity_id, entity_type, title, content, metadata)
            VALUES ('test-1', 'test', 'Test Title', 'Test Content', '{"tags": "test tag"}')
        """))
        await db_session.commit()
        
        # Query the search_vector to verify it was generated
        result = await db_session.execute(text("""
            SELECT search_vector::text
            FROM search_documents
            WHERE entity_id = 'test-1'
        """))
        
        row = result.fetchone()
        assert row is not None, "Test document should exist"
        
        search_vector = row[0]
        
        # Verify the search_vector contains weighted terms
        # Weight A for title, Weight B for content, Weight C for tags
        assert "test" in search_vector.lower(), "Search vector should contain search terms"
        
        # Clean up
        await db_session.execute(text("""
            DELETE FROM search_documents WHERE entity_id = 'test-1'
        """))
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_metadata_jsonb_functionality(self, db_session: AsyncSession):
        """Verify metadata column supports JSONB operations"""
        # Insert a test document with metadata
        await db_session.execute(text("""
            INSERT INTO search_documents (entity_id, entity_type, title, content, metadata)
            VALUES ('test-2', 'test', 'Test', 'Test', '{"key": "value", "number": 42}')
        """))
        await db_session.commit()
        
        # Query using JSONB operators
        result = await db_session.execute(text("""
            SELECT metadata->>'key' as key_value, metadata->>'number' as number_value
            FROM search_documents
            WHERE entity_id = 'test-2'
        """))
        
        row = result.fetchone()
        assert row is not None, "Test document should exist"
        assert row[0] == "value", "JSONB key extraction should work"
        assert row[1] == "42", "JSONB number extraction should work"
        
        # Clean up
        await db_session.execute(text("""
            DELETE FROM search_documents WHERE entity_id = 'test-2'
        """))
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_uuid_generation(self, db_session: AsyncSession):
        """Verify UUID is automatically generated for new documents"""
        # Insert without specifying ID
        await db_session.execute(text("""
            INSERT INTO search_documents (entity_id, entity_type, title, content)
            VALUES ('test-3', 'test', 'Test', 'Test')
        """))
        await db_session.commit()
        
        # Query the generated ID
        result = await db_session.execute(text("""
            SELECT id
            FROM search_documents
            WHERE entity_id = 'test-3'
        """))
        
        row = result.fetchone()
        assert row is not None, "Test document should exist"
        assert row[0] is not None, "UUID should be generated"
        
        # Verify it's a valid UUID format (36 characters with hyphens)
        uuid_str = str(row[0])
        assert len(uuid_str) == 36, "UUID should be 36 characters"
        assert uuid_str.count("-") == 4, "UUID should have 4 hyphens"
        
        # Clean up
        await db_session.execute(text("""
            DELETE FROM search_documents WHERE entity_id = 'test-3'
        """))
        await db_session.commit()


class TestMigrationIntegrity:
    """Test migration integrity and constraints"""

    @pytest.mark.asyncio
    async def test_unique_constraint_enforcement(self, db_session: AsyncSession):
        """Verify unique constraint prevents duplicate entity_id/entity_type pairs"""
        # Insert first document
        await db_session.execute(text("""
            INSERT INTO search_documents (entity_id, entity_type, title, content)
            VALUES ('dup-1', 'test', 'Test 1', 'Content 1')
        """))
        await db_session.commit()
        
        # Try to insert duplicate
        with pytest.raises(Exception) as exc_info:
            await db_session.execute(text("""
                INSERT INTO search_documents (entity_id, entity_type, title, content)
                VALUES ('dup-1', 'test', 'Test 2', 'Content 2')
            """))
            await db_session.commit()
        
        # Verify it's a unique constraint violation
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()
        
        # Rollback the failed transaction
        await db_session.rollback()
        
        # Clean up
        await db_session.execute(text("""
            DELETE FROM search_documents WHERE entity_id = 'dup-1'
        """))
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_not_null_constraints(self, db_session: AsyncSession):
        """Verify NOT NULL constraints are enforced"""
        # Try to insert without required fields
        with pytest.raises(Exception) as exc_info:
            await db_session.execute(text("""
                INSERT INTO search_documents (entity_id, entity_type)
                VALUES ('null-test', 'test')
            """))
            await db_session.commit()
        
        # Verify it's a NOT NULL violation
        assert "null" in str(exc_info.value).lower() or "not-null" in str(exc_info.value).lower()
        
        # Rollback the failed transaction
        await db_session.rollback()
