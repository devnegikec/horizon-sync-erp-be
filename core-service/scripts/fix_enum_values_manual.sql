-- ===========================================
-- Core Service - Manual Fix for Enum Values
-- ===========================================
-- This script fixes enum values in core_db database
-- Run this manually if you get errors like: 'stock' is not among the defined enum values
--
-- IMPORTANT: This will drop and recreate enums. If you have data, you may need to migrate it first.
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/fix_enum_values_manual.sql
--   OR
--   psql -U horizon_user -d core_db -f fix_enum_values_manual.sql

-- Connect to core_db
\c core_db;

-- ===========================================
-- Step 1: Drop all dependent tables first
-- ===========================================
-- Note: Only drop if tables are empty or you've backed up data
-- Uncomment these if you need to drop tables:

-- DROP TABLE IF EXISTS stock_reconciliation_items CASCADE;
-- DROP TABLE IF EXISTS stock_reconciliations CASCADE;
-- DROP TABLE IF EXISTS stock_entry_items CASCADE;
-- DROP TABLE IF EXISTS stock_entries CASCADE;
-- DROP TABLE IF EXISTS quality_inspection_readings CASCADE;
-- DROP TABLE IF EXISTS quality_inspections CASCADE;
-- DROP TABLE IF EXISTS quality_inspection_parameters CASCADE;
-- DROP TABLE IF EXISTS quality_inspection_templates CASCADE;
-- DROP TABLE IF EXISTS put_away_rules CASCADE;
-- DROP TABLE IF EXISTS serial_no_history CASCADE;
-- DROP TABLE IF EXISTS serial_nos CASCADE;
-- DROP TABLE IF EXISTS batches CASCADE;
-- DROP TABLE IF EXISTS item_suppliers CASCADE;
-- DROP TABLE IF EXISTS item_prices CASCADE;
-- DROP TABLE IF EXISTS items CASCADE;
-- DROP TABLE IF EXISTS item_groups CASCADE;
-- DROP TABLE IF EXISTS warehouses_extended CASCADE;

-- ===========================================
-- Step 2: Drop and recreate all enum types with correct lowercase values
-- ===========================================

-- Fix ITEMTYPE enum
DROP TYPE IF EXISTS itemtype CASCADE;
CREATE TYPE itemtype AS ENUM (
    'stock',
    'non_stock',
    'service',
    'fixed_asset'
);

-- Fix ITEMSTATUS enum
DROP TYPE IF EXISTS itemstatus CASCADE;
CREATE TYPE itemstatus AS ENUM (
    'active',
    'inactive',
    'discontinued'
);

-- Fix VALUATIONMETHOD enum
DROP TYPE IF EXISTS valuationmethod CASCADE;
CREATE TYPE valuationmethod AS ENUM (
    'fifo',
    'lifo',
    'moving_average',
    'standard'
);

-- Fix DOCUMENTSTATUS enum
DROP TYPE IF EXISTS documentstatus CASCADE;
CREATE TYPE documentstatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

-- Fix WAREHOUSETYPE enum
DROP TYPE IF EXISTS warehousetype CASCADE;
CREATE TYPE warehousetype AS ENUM (
    'warehouse',
    'store',
    'virtual',
    'transit'
);

-- Fix STOCKENTRYTYPE enum
DROP TYPE IF EXISTS stockentrytype CASCADE;
CREATE TYPE stockentrytype AS ENUM (
    'material_receipt',
    'material_issue',
    'material_transfer',
    'manufacture',
    'repack',
    'send_to_subcontractor'
);

-- Fix STOCKENTRYSTATUS enum
DROP TYPE IF EXISTS stockentrystatus CASCADE;
CREATE TYPE stockentrystatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

-- Fix MOVEMENTTYPE enum
DROP TYPE IF EXISTS movementtype CASCADE;
CREATE TYPE movementtype AS ENUM (
    'in',
    'out',
    'transfer',
    'adjustment'
);

-- Fix BATCHSTATUS enum
DROP TYPE IF EXISTS batchstatus CASCADE;
CREATE TYPE batchstatus AS ENUM (
    'active',
    'expired',
    'consumed'
);

-- Fix INSPECTIONTYPE enum
DROP TYPE IF EXISTS inspectiontype CASCADE;
CREATE TYPE inspectiontype AS ENUM (
    'incoming',
    'outgoing',
    'in_process'
);

-- Fix INSPECTIONSTATUS enum
DROP TYPE IF EXISTS inspectionstatus CASCADE;
CREATE TYPE inspectionstatus AS ENUM (
    'pending',
    'accepted',
    'rejected'
);

-- Fix READINGTYPE enum
DROP TYPE IF EXISTS readingtype CASCADE;
CREATE TYPE readingtype AS ENUM (
    'numeric',
    'text',
    'pass_fail'
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
-- Step 4: Recreate tables (if you dropped them)
-- ===========================================
-- After fixing enums, you can run:
--   \i /app/scripts/create_tables.sql
-- OR let Alembic migrations recreate them

SELECT 'Enum types fixed! Now run migrations or create_tables.sql' AS next_step;
