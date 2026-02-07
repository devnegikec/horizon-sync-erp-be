-- ===========================================
-- Step 1: Add new resource types to enum
-- Run this FIRST, then run seed_permissions_four_modules.sql
-- This must complete and commit before using the new values.
-- ===========================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'customer' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'customer';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'sales_order' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'sales_order';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'invoice' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'invoice';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'supplier' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'supplier';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'purchase_order' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'purchase_order';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'chart_of_account' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'chart_of_account';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'payment' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'payment';
    END IF;
END$$;
