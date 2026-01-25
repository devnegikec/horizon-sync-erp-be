-- ===========================================
-- Check Enum Values in Database
-- ===========================================
-- This script checks all enum types and their values in core_db
-- 
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/check_enum_values.sql
--   OR
--   psql -U horizon_user -d core_db -f check_enum_values.sql

\c core_db;

-- ===========================================
-- Check All Enum Types and Their Values
-- ===========================================
SELECT 
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values,
    COUNT(e.enumlabel) AS value_count
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname IN (
    'itemtype', 
    'itemstatus', 
    'valuationmethod', 
    'documentstatus',
    'warehousetype', 
    'stockentrytype', 
    'stockentrystatus', 
    'movementtype',
    'batchstatus', 
    'inspectiontype', 
    'inspectionstatus', 
    'readingtype'
)
GROUP BY t.typname
ORDER BY t.typname;

-- ===========================================
-- Check Specific Enum: itemtype
-- ===========================================
SELECT 
    'itemtype' AS enum_name,
    e.enumlabel AS enum_value,
    e.enumsortorder AS sort_order
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'itemtype'
ORDER BY e.enumsortorder;

-- ===========================================
-- Check Specific Enum: itemstatus
-- ===========================================
SELECT 
    'itemstatus' AS enum_name,
    e.enumlabel AS enum_value,
    e.enumsortorder AS sort_order
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'itemstatus'
ORDER BY e.enumsortorder;

-- ===========================================
-- Check Specific Enum: valuationmethod
-- ===========================================
SELECT 
    'valuationmethod' AS enum_name,
    e.enumlabel AS enum_value,
    e.enumsortorder AS sort_order
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'valuationmethod'
ORDER BY e.enumsortorder;

-- ===========================================
-- Check Specific Enum: warehousetype
-- ===========================================
SELECT 
    'warehousetype' AS enum_name,
    e.enumlabel AS enum_value,
    e.enumsortorder AS sort_order
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname = 'warehousetype'
ORDER BY e.enumsortorder;

-- ===========================================
-- Check if items table exists and sample data
-- ===========================================
SELECT 
    'items table check' AS info,
    COUNT(*) AS total_items,
    COUNT(DISTINCT item_type) AS distinct_item_types,
    string_agg(DISTINCT item_type::text, ', ') AS item_types_found
FROM items
WHERE item_type IS NOT NULL;

-- ===========================================
-- Sample items with their enum values
-- ===========================================
SELECT 
    item_code,
    item_name,
    item_type::text AS item_type_value,
    status::text AS status_value,
    valuation_method::text AS valuation_method_value
FROM items
LIMIT 10;
