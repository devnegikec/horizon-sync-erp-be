# Database Migration Guide

## Overview

This guide covers the database migration scripts for the Unified Search API. The migration creates the necessary schema for full-text search functionality with PostgreSQL.

## Migration: 001_create_search_tables

**Revision ID:** 001  
**Requirements:** 8.1, 8.4

### What This Migration Does

#### 1. Creates `search_documents` Table

The main table for storing searchable content with full-text search support:

```sql
CREATE TABLE search_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    search_vector TSVECTOR GENERATED ALWAYS AS (...) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(entity_id, entity_type)
);
```

**Key Features:**
- **UUID Primary Key**: Unique identifier for each search document
- **Entity Reference**: Links to entities via `entity_id` and `entity_type`
- **Full-Text Search**: Generated `search_vector` column with weighted text search
  - Title: Weight A (highest priority)
  - Content: Weight B (medium priority)
  - Metadata tags: Weight C (lower priority)
- **JSONB Metadata**: Flexible storage for entity-specific data
- **Timestamps**: Automatic tracking of creation and updates

#### 2. Creates Optimized Indexes

Four indexes for optimal search performance:

1. **GIN Index on search_vector**: Enables fast full-text search queries
2. **Index on entity_id**: Fast lookups by entity identifier
3. **Index on entity_type**: Efficient filtering by entity type
4. **Index on updated_at**: Supports synchronization queries

#### 3. Creates Update Trigger

Automatically updates the `updated_at` timestamp when records are modified:

```sql
CREATE TRIGGER trigger_update_search_documents_updated_at
BEFORE UPDATE ON search_documents
FOR EACH ROW
EXECUTE FUNCTION update_search_documents_updated_at();
```

#### 4. Creates `search_configurations` Table

Stores entity-specific search configurations:

```sql
CREATE TABLE search_configurations (
    entity_type VARCHAR PRIMARY KEY,
    searchable_fields JSONB NOT NULL,
    boost_factors JSONB,
    filters JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 5. Seeds Default Configurations

Pre-populates configurations for 5 ERP entity types:

##### Items Configuration
- **Searchable Fields**: item_code, item_name, description, item_group
- **Boost Factors**: item_code (2.0x), item_name (1.5x), description (1.0x)
- **Filters**: item_type, status

##### Customers Configuration
- **Searchable Fields**: customer_code, customer_name, email, phone
- **Boost Factors**: customer_code (2.0x), customer_name (1.5x), email (1.2x)
- **Filters**: status

##### Suppliers Configuration
- **Searchable Fields**: supplier_code, supplier_name, email, phone
- **Boost Factors**: supplier_code (2.0x), supplier_name (1.5x), email (1.2x)
- **Filters**: status

##### Warehouses Configuration
- **Searchable Fields**: warehouse_code, warehouse_name, location
- **Boost Factors**: warehouse_code (2.0x), warehouse_name (1.5x)
- **Filters**: warehouse_type

##### Stock Entries Configuration
- **Searchable Fields**: entry_number, purpose, remarks
- **Boost Factors**: entry_number (2.0x), purpose (1.5x)
- **Filters**: entry_type, status

## Running Migrations

### Prerequisites

1. PostgreSQL database must be running
2. Database URL must be configured in `.env` file:
   ```
   DATABASE_URL=postgresql://user:password@host:port/search_db
   ```
3. Required PostgreSQL extensions must be enabled:
   - `uuid-ossp` (for UUID generation)
   - `pg_trgm` (for fuzzy text search)

### Apply Migration

To apply the migration and create all tables:

```bash
cd search-service
alembic upgrade head
```

### Rollback Migration

To rollback the migration and drop all tables:

```bash
cd search-service
alembic downgrade -1
```

### Check Migration Status

To see the current migration status:

```bash
cd search-service
alembic current
```

### View Migration History

To see all migrations:

```bash
cd search-service
alembic history
```

## Docker Deployment

When using Docker Compose, migrations are automatically applied on service startup:

```bash
# Start all services (migrations run automatically)
docker compose up -d

# View migration logs
docker compose logs search-service
```

The search-service container runs migrations before starting the application:

```bash
python -m alembic upgrade head
```

## Verification

### Verify Migration Applied

Run the verification script:

```bash
cd search-service
python verify_migration.py
```

### Manual Verification

Connect to the database and check tables:

```sql
-- Connect to search_db
\c search_db

-- List all tables
\dt

-- Check search_documents structure
\d search_documents

-- Check search_configurations structure
\d search_configurations

-- View seeded configurations
SELECT entity_type, searchable_fields FROM search_configurations;
```

### Expected Output

You should see:
- `search_documents` table with 9 columns
- `search_configurations` table with 5 columns
- 4 indexes on `search_documents`
- 5 rows in `search_configurations` (one for each entity type)

## Troubleshooting

### Migration Fails with "relation already exists"

The tables already exist. Either:
1. Drop the tables manually and re-run the migration
2. Mark the migration as applied: `alembic stamp head`

### Migration Fails with "extension does not exist"

Required PostgreSQL extensions are missing. Run:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Migration Fails with "permission denied"

Database user lacks necessary permissions. Grant privileges:

```sql
GRANT ALL PRIVILEGES ON DATABASE search_db TO your_user;
```

### Async Engine Errors

Ensure `asyncpg` is installed:

```bash
pip install asyncpg
```

## Adding New Entity Types

To add a new entity type configuration:

1. Create a new migration:
   ```bash
   alembic revision -m "add_new_entity_config"
   ```

2. Add INSERT statement in the upgrade function:
   ```python
   op.execute("""
       INSERT INTO search_configurations (entity_type, searchable_fields, boost_factors, filters)
       VALUES (
           'new_entity',
           '["field1", "field2"]'::jsonb,
           '{"field1": 2.0, "field2": 1.5}'::jsonb,
           '{"status": ["active", "inactive"]}'::jsonb
       );
   """)
   ```

3. Add DELETE statement in the downgrade function:
   ```python
   op.execute("DELETE FROM search_configurations WHERE entity_type = 'new_entity'")
   ```

4. Apply the migration:
   ```bash
   alembic upgrade head
   ```

## Best Practices

1. **Always backup** the database before running migrations in production
2. **Test migrations** in a development environment first
3. **Review migration SQL** before applying to production
4. **Monitor performance** after adding new indexes
5. **Keep configurations in sync** with entity schemas
6. **Document changes** in migration comments

## Related Files

- Migration script: `alembic/versions/001_create_search_tables.py`
- Alembic config: `alembic.ini`
- Alembic environment: `alembic/env.py`
- Database models: `app/models/search.py`
- Verification script: `verify_migration.py`

## Requirements Validation

This migration satisfies:

- **Requirement 8.1**: Incremental index updates without full rebuilds
- **Requirement 8.4**: Optimized storage through appropriate data structures

The migration creates the foundation for:
- Full-text search with PostgreSQL
- Entity-specific search configurations
- Efficient query performance through proper indexing
- Flexible metadata storage for future extensibility
