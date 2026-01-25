-- ===========================================
-- Fix Enum Values to Lowercase
-- ===========================================
-- This script recreates enum types with lowercase values
-- WARNING: This will drop and recreate enums. Make sure you have backups!
-- 
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/fix_enum_to_lowercase.sql
--   OR
--   psql -U horizon_user -d core_db -f fix_enum_to_lowercase.sql

\c core_db;

-- ===========================================
-- Step 1: Drop existing enum types
-- ===========================================
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
-- Step 2: Recreate enum types with lowercase values
-- ===========================================

CREATE TYPE itemtype AS ENUM (
    'stock',
    'non_stock',
    'service',
    'fixed_asset'
);

CREATE TYPE itemstatus AS ENUM (
    'active',
    'inactive',
    'discontinued'
);

CREATE TYPE valuationmethod AS ENUM (
    'fifo',
    'lifo',
    'moving_average',
    'standard'
);

CREATE TYPE documentstatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

CREATE TYPE warehousetype AS ENUM (
    'warehouse',
    'store',
    'virtual',
    'transit'
);

CREATE TYPE stockentrytype AS ENUM (
    'material_receipt',
    'material_issue',
    'material_transfer',
    'manufacture',
    'repack',
    'send_to_subcontractor'
);

CREATE TYPE stockentrystatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

CREATE TYPE movementtype AS ENUM (
    'purchase',
    'sale',
    'transfer',
    'adjustment',
    'return',
    'damage'
);

CREATE TYPE batchstatus AS ENUM (
    'active',
    'expired',
    'recalled'
);

CREATE TYPE inspectiontype AS ENUM (
    'incoming',
    'outgoing',
    'in_process'
);

CREATE TYPE inspectionstatus AS ENUM (
    'pending',
    'accepted',
    'rejected'
);

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

SELECT 'Enum types recreated with lowercase values!' AS status;
SELECT 'Now recreate tables or run migrations' AS next_step;
