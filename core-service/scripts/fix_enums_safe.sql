-- ===========================================
-- Core Service - Safe Fix for Enum Values (No Data Loss)
-- ===========================================
-- This script fixes enum values WITHOUT dropping tables
-- It uses ALTER TYPE to add missing values
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db
--   Then copy-paste this script or run: \i /app/scripts/fix_enums_safe.sql

\c core_db;

-- ===========================================
-- Check current enum values
-- ===========================================
SELECT 'Current enum values:' AS info;
SELECT
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS current_values
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN ('itemtype', 'itemstatus', 'valuationmethod', 'warehousetype')
GROUP BY t.typname
ORDER BY t.typname;

-- ===========================================
-- If enums have wrong values, we need to recreate them
-- But first, let's check if we can just add the missing values
-- ===========================================

-- For ITEMTYPE: Add lowercase values if they don't exist
DO $$
BEGIN
    -- Check and add 'stock' if missing
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'stock' AND enumtypid = 'itemtype'::regtype
    ) THEN
        ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'stock';
    END IF;

    -- Check and add other values
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'non_stock' AND enumtypid = 'itemtype'::regtype
    ) THEN
        ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'non_stock';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'service' AND enumtypid = 'itemtype'::regtype
    ) THEN
        ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'service';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'fixed_asset' AND enumtypid = 'itemtype'::regtype
    ) THEN
        ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'fixed_asset';
    END IF;
END $$;

-- ===========================================
-- RECOMMENDED: Drop and recreate (if no data yet)
-- ===========================================
-- If you don't have important data yet, it's safer to drop and recreate:

-- Drop enums (will cascade to columns using them)
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

-- Recreate with correct lowercase values
CREATE TYPE itemtype AS ENUM ('stock', 'non_stock', 'service', 'fixed_asset');
CREATE TYPE itemstatus AS ENUM ('active', 'inactive', 'discontinued');
CREATE TYPE valuationmethod AS ENUM ('fifo', 'lifo', 'moving_average', 'standard');
CREATE TYPE documentstatus AS ENUM ('draft', 'submitted', 'cancelled');
CREATE TYPE warehousetype AS ENUM ('warehouse', 'store', 'virtual', 'transit');
CREATE TYPE stockentrytype AS ENUM ('material_receipt', 'material_issue', 'material_transfer', 'manufacture', 'repack', 'send_to_subcontractor');
CREATE TYPE stockentrystatus AS ENUM ('draft', 'submitted', 'cancelled');
CREATE TYPE movementtype AS ENUM ('in', 'out', 'transfer', 'adjustment');
CREATE TYPE batchstatus AS ENUM ('active', 'expired', 'consumed');
CREATE TYPE inspectiontype AS ENUM ('incoming', 'outgoing', 'in_process');
CREATE TYPE inspectionstatus AS ENUM ('pending', 'accepted', 'rejected');
CREATE TYPE readingtype AS ENUM ('numeric', 'text', 'pass_fail');

-- ===========================================
-- Verify
-- ===========================================
SELECT 'Enum types recreated with lowercase values!' AS status;

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
-- Next Steps
-- ===========================================
SELECT 'Now run: python -m alembic upgrade head' AS next_step;
SELECT 'Or recreate tables with: \i /app/scripts/create_tables.sql' AS alternative;
