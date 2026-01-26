-- ===========================================
-- Fix Enum Values to Uppercase
-- ===========================================
-- This script recreates enum types with UPPERCASE values
-- WARNING: This will drop and recreate enums. Make sure you have backups!
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/fix_enum_to_uppercase.sql
--   OR
--   psql -U horizon_user -d core_db -f fix_enum_to_uppercase.sql

\c core_db;

-- ===========================================
-- Step 1: Drop existing enum types
-- ===========================================
-- Note: This will fail if there are columns using these enums
-- You may need to drop dependent columns first or use CASCADE

DROP TYPE IF EXISTS itemtype CASCADE;
DROP TYPE IF EXISTS itemstatus CASCADE;
DROP TYPE IF EXISTS valuationmethod CASCADE;
DROP TYPE IF EXISTS documentstatus CASCADE;
DROP TYPE IF EXISTS warehousetype CASCADE;
DROP TYPE IF EXISTS stockentrytype CASCADE;
DROP TYPE IF EXISTS stockentrystatus CASCADE;
DROP TYPE IF EXISTS movementtype CASCADE;
DROP TYPE IF EXISTS batchstatus CASCADE;
DROP TYPE IF EXISTS inspectiontype CASCADE;
DROP TYPE IF EXISTS inspectionstatus CASCADE;
DROP TYPE IF EXISTS readingtype CASCADE;

-- ===========================================
-- Step 2: Recreate enum types with UPPERCASE values
-- ===========================================

CREATE TYPE itemtype AS ENUM (
    'STOCK',
    'NON_STOCK',
    'SERVICE',
    'FIXED_ASSET'
);

CREATE TYPE itemstatus AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'DISCONTINUED'
);

CREATE TYPE valuationmethod AS ENUM (
    'FIFO',
    'LIFO',
    'MOVING_AVERAGE',
    'STANDARD'
);

CREATE TYPE documentstatus AS ENUM (
    'DRAFT',
    'SUBMITTED',
    'CANCELLED'
);

CREATE TYPE warehousetype AS ENUM (
    'WAREHOUSE',
    'STORE',
    'VIRTUAL',
    'TRANSIT'
);

CREATE TYPE stockentrytype AS ENUM (
    'MATERIAL_RECEIPT',
    'MATERIAL_ISSUE',
    'MATERIAL_TRANSFER',
    'MANUFACTURE',
    'REPACK',
    'SEND_TO_SUBCONTRACTOR'
);

CREATE TYPE stockentrystatus AS ENUM (
    'DRAFT',
    'SUBMITTED',
    'CANCELLED'
);

CREATE TYPE movementtype AS ENUM (
    'PURCHASE',
    'SALE',
    'TRANSFER',
    'ADJUSTMENT',
    'RETURN',
    'DAMAGE'
);

CREATE TYPE batchstatus AS ENUM (
    'ACTIVE',
    'EXPIRED',
    'RECALLED'
);

CREATE TYPE inspectiontype AS ENUM (
    'INCOMING',
    'OUTGOING',
    'IN_PROCESS'
);

CREATE TYPE inspectionstatus AS ENUM (
    'PENDING',
    'ACCEPTED',
    'REJECTED'
);

CREATE TYPE readingtype AS ENUM (
    'NUMERIC',
    'TEXT',
    'PASS_FAIL'
);

-- ===========================================
-- Step 3: Verify enum types
-- ===========================================
SELECT
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN (
    'itemtype', 'itemstatus', 'valuationmethod', 'documentstatus',
    'warehousetype', 'stockentrytype', 'stockentrystatus', 'movementtype',
    'batchstatus', 'inspectiontype', 'inspectionstatus', 'readingtype'
)
GROUP BY t.typname
ORDER BY t.typname;

-- ===========================================
-- Step 4: Recreate tables (if they were dropped)
-- ===========================================
-- After fixing enums, you'll need to recreate tables:
--   \i /app/scripts/create_tables.sql
-- OR run Alembic migrations:
--   python -m alembic upgrade head

SELECT 'Enum types recreated with UPPERCASE values!' AS status;
SELECT 'Now recreate tables or run migrations' AS next_step;
