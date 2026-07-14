-- ===========================================
-- Fix Items Table - Add Missing Columns
-- ===========================================
-- This script adds missing columns to the items table
-- Run this in core_db database
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/fix_items_table.sql

\c core_db;

-- Add missing columns to items table
ALTER TABLE items
ADD COLUMN IF NOT EXISTS item_type itemtype DEFAULT 'stock',
ADD COLUMN IF NOT EXISTS valuation_method valuationmethod DEFAULT 'fifo',
ADD COLUMN IF NOT EXISTS status itemstatus DEFAULT 'active';

-- Add foreign key constraint to item_groups if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'items_item_group_id_fkey'
        AND table_name = 'items'
    ) THEN
        ALTER TABLE items
        ADD CONSTRAINT items_item_group_id_fkey
        FOREIGN KEY (item_group_id) REFERENCES item_groups(id);
    END IF;
END $$;

-- Verify the changes
\echo 'Items table structure after fix:'
\d items

SELECT 'Items table fixed successfully!' AS status;
