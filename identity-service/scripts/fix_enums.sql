-- ===========================================
-- Identity Service - Fix/Update Enum Values
-- ===========================================
-- This script adds new enum values to existing enum types
-- Safe to run on existing databases (uses IF NOT EXISTS pattern)
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d identity_db -f /app/scripts/fix_enums.sql

\c identity_db;

-- ===========================================
-- Add new values to resourcetype enum
-- ===========================================
-- PostgreSQL 9.1+ supports ALTER TYPE ... ADD VALUE

DO $$
BEGIN
    -- Add inventory resource types
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'item' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'item';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'item_group' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'item_group';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'warehouse' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'warehouse';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'stock_entry' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'stock_entry';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'batch' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'batch';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'serial' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'serial';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'report' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'report';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'setting' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'setting';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'all' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'all';
    END IF;
END$$;

-- ===========================================
-- Verify enum types
-- ===========================================
SELECT
    t.typname AS enum_name,
    string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
WHERE t.typname IN ('resourcetype', 'actiontype', 'usertype', 'userstatus', 'organizationtype', 'organizationstatus')
GROUP BY t.typname
ORDER BY t.typname;

SELECT 'Enum types updated successfully!' AS status;
