-- ===========================================
-- Core Service - Fix Enum Values
-- ===========================================
-- This script fixes enum values in core_db
-- Run this if you get errors like: 'stock' is not among the defined enum values
-- 
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/fix_enums.sql
--   OR
--   psql -U horizon_user -d core_db -f fix_enums.sql

-- Connect to core_db (if running manually)
\c core_db;

-- ===========================================
-- Fix ITEMTYPE enum
-- ===========================================
-- Drop and recreate with correct values
DROP TYPE IF EXISTS itemtype CASCADE;

CREATE TYPE itemtype AS ENUM (
    'stock',
    'non_stock',
    'service',
    'fixed_asset'
);

-- ===========================================
-- Fix ITEMSTATUS enum
-- ===========================================
DROP TYPE IF EXISTS itemstatus CASCADE;

CREATE TYPE itemstatus AS ENUM (
    'active',
    'inactive',
    'discontinued'
);

-- ===========================================
-- Fix VALUATIONMETHOD enum
-- ===========================================
DROP TYPE IF EXISTS valuationmethod CASCADE;

CREATE TYPE valuationmethod AS ENUM (
    'fifo',
    'lifo',
    'moving_average',
    'standard'
);

-- ===========================================
-- Fix DOCUMENTSTATUS enum
-- ===========================================
DROP TYPE IF EXISTS documentstatus CASCADE;

CREATE TYPE documentstatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

-- ===========================================
-- Fix WAREHOUSETYPE enum
-- ===========================================
DROP TYPE IF EXISTS warehousetype CASCADE;

CREATE TYPE warehousetype AS ENUM (
    'warehouse',
    'store',
    'virtual',
    'transit'
);

-- ===========================================
-- Fix STOCKENTRYTYPE enum
-- ===========================================
DROP TYPE IF EXISTS stockentrytype CASCADE;

CREATE TYPE stockentrytype AS ENUM (
    'material_receipt',
    'material_issue',
    'material_transfer',
    'manufacture',
    'repack',
    'send_to_subcontractor'
);

-- ===========================================
-- Fix STOCKENTRYSTATUS enum
-- ===========================================
DROP TYPE IF EXISTS stockentrystatus CASCADE;

CREATE TYPE stockentrystatus AS ENUM (
    'draft',
    'submitted',
    'cancelled'
);

-- ===========================================
-- Fix MOVEMENTTYPE enum
-- ===========================================
DROP TYPE IF EXISTS movementtype CASCADE;

CREATE TYPE movementtype AS ENUM (
    'in',
    'out',
    'transfer',
    'adjustment'
);

-- ===========================================
-- Fix BATCHSTATUS enum
-- ===========================================
DROP TYPE IF EXISTS batchstatus CASCADE;

CREATE TYPE batchstatus AS ENUM (
    'active',
    'expired',
    'consumed'
);

-- ===========================================
-- Fix INSPECTIONTYPE enum
-- ===========================================
DROP TYPE IF EXISTS inspectiontype CASCADE;

CREATE TYPE inspectiontype AS ENUM (
    'incoming',
    'outgoing',
    'in_process'
);

-- ===========================================
-- Fix INSPECTIONSTATUS enum
-- ===========================================
DROP TYPE IF EXISTS inspectionstatus CASCADE;

CREATE TYPE inspectionstatus AS ENUM (
    'pending',
    'accepted',
    'rejected'
);

-- ===========================================
-- Fix READINGTYPE enum
-- ===========================================
DROP TYPE IF EXISTS readingtype CASCADE;

CREATE TYPE readingtype AS ENUM (
    'numeric',
    'text',
    'pass_fail'
);

-- ===========================================
-- Verification
-- ===========================================
SELECT 'Enum types created successfully!' AS status;

-- List all enum types
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
