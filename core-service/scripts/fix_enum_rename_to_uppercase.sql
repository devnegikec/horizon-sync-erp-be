-- ===========================================
-- Rename Enum Values to UPPERCASE (Safe - No Data Loss)
-- ===========================================
-- This script renames existing enum values from lowercase to UPPERCASE
-- Using ALTER TYPE ... RENAME VALUE (PostgreSQL 10+)
-- This is safe and preserves all existing data!
-- 
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/fix_enum_rename_to_uppercase.sql

\c core_db;

-- ===========================================
-- Fix itemtype: stock -> STOCK, etc.
-- ===========================================
ALTER TYPE itemtype RENAME VALUE 'stock' TO 'STOCK';
ALTER TYPE itemtype RENAME VALUE 'non_stock' TO 'NON_STOCK';
ALTER TYPE itemtype RENAME VALUE 'service' TO 'SERVICE';
ALTER TYPE itemtype RENAME VALUE 'fixed_asset' TO 'FIXED_ASSET';

-- ===========================================
-- Fix valuationmethod: fifo -> FIFO, etc.
-- ===========================================
ALTER TYPE valuationmethod RENAME VALUE 'fifo' TO 'FIFO';
ALTER TYPE valuationmethod RENAME VALUE 'lifo' TO 'LIFO';
ALTER TYPE valuationmethod RENAME VALUE 'moving_average' TO 'MOVING_AVERAGE';
ALTER TYPE valuationmethod RENAME VALUE 'standard' TO 'STANDARD';

-- ===========================================
-- Fix warehousetype (if lowercase)
-- ===========================================
-- Uncomment if needed:
-- ALTER TYPE warehousetype RENAME VALUE 'warehouse' TO 'WAREHOUSE';
-- ALTER TYPE warehousetype RENAME VALUE 'store' TO 'STORE';
-- ALTER TYPE warehousetype RENAME VALUE 'virtual' TO 'VIRTUAL';
-- ALTER TYPE warehousetype RENAME VALUE 'transit' TO 'TRANSIT';

-- ===========================================
-- Verify the changes
-- ===========================================
SELECT 
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname IN ('itemtype', 'valuationmethod', 'warehousetype', 'itemstatus')
GROUP BY t.typname
ORDER BY t.typname;

SELECT 'Enum values renamed to UPPERCASE successfully!' AS status;
