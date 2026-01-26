-- ===========================================
-- Core Service - Simple Manual Seed Data Script
-- ===========================================
-- This script manually inserts seed data into core_db
--
-- IMPORTANT: You need to replace ORG_ID and ADMIN_USER_ID with actual UUIDs
-- Get them by running:
--   \c identity_db;
--   SELECT id FROM organizations WHERE slug = 'default-org';
--   SELECT id FROM users WHERE email = 'admin@example.com';
--   \c core_db;
--
-- Usage:
--   1. First, get the UUIDs from identity_db (see above)
--   2. Replace :org_id and :admin_user_id in this script
--   3. Run: docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/seed_data_simple.sql
--   OR copy-paste this script after replacing the UUIDs

\c core_db;

-- ===========================================
-- STEP 1: Get UUIDs from identity_db
-- ===========================================
-- Run these queries first to get the UUIDs:
--
-- \c identity_db;
-- SELECT id FROM organizations WHERE slug = 'default-org';
-- SELECT id FROM users WHERE email = 'admin@example.com';
--
-- Copy the UUIDs and replace :org_id and :admin_user_id below
-- ===========================================

-- Replace these with actual UUIDs from identity_db
\set org_id '00000000-0000-0000-0000-000000000000'  -- REPLACE THIS
\set admin_user_id '00000000-0000-0000-0000-000000000000'  -- REPLACE THIS

-- ===========================================
-- STEP 2: Create Warehouses
-- ===========================================
INSERT INTO warehouses_extended (
    id, organization_id, name, code, description, warehouse_type,
    address_line1, city, state, postal_code, country,
    is_active, is_default, created_by, updated_by, created_at, updated_at
) VALUES
(
    gen_random_uuid(), :'org_id'::uuid, 'Main Warehouse', 'WH-MAIN',
    'Primary warehouse for storage', 'warehouse',
    '123 Industrial Ave', 'Mumbai', 'Maharashtra', '400001', 'India',
    true, true, :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
),
(
    gen_random_uuid(), :'org_id'::uuid, 'Retail Store', 'WH-STORE',
    'Retail outlet for direct sales', 'store',
    '456 Market Street', 'Mumbai', 'Maharashtra', '400002', 'India',
    true, false, :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
),
(
    gen_random_uuid(), :'org_id'::uuid, 'Transit Warehouse', 'WH-TRANSIT',
    'Temporary storage during transit', 'transit',
    null, null, null, null, null,
    true, false, :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
);

-- ===========================================
-- STEP 3: Create Item Groups
-- ===========================================
-- Store group IDs in variables for later use
DO $$
DECLARE
    ig_rm_id UUID;
    ig_fg_id UUID;
    ig_con_id UUID;
    ig_srv_id UUID;
BEGIN
    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'Raw Materials', 'RM',
        'Raw materials for production', 'fifo', 'Kg', true,
        :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ) RETURNING id INTO ig_rm_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'Finished Goods', 'FG',
        'Finished products ready for sale', 'moving_average', 'Nos', true,
        :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ) RETURNING id INTO ig_fg_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'Consumables', 'CON',
        'Consumable items', 'fifo', 'Nos', true,
        :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ) RETURNING id INTO ig_con_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'Services', 'SRV',
        'Service items (non-stock)', 'Hrs', true,
        :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ) RETURNING id INTO ig_srv_id;

    -- ===========================================
    -- STEP 4: Create Items
    -- ===========================================

    -- Raw Materials
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock, valuation_method,
        standard_rate, valuation_rate, reorder_level, reorder_qty, min_order_qty,
        has_batch_no, status, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'RM-STEEL-001', 'Steel Sheet (2mm)',
        'High quality steel sheet, 2mm thickness', ig_rm_id,
        'stock', 'Kg', true, 'fifo',
        85.00, 75.00, 100, 500, 50,
        true, 'active', :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ),
    (
        gen_random_uuid(), :'org_id'::uuid, 'RM-PLAST-001', 'ABS Plastic Granules',
        'ABS plastic granules for injection molding', ig_rm_id,
        'stock', 'Kg', true, 'moving_average',
        120.00, 100.00, 200, 1000, 100,
        false, 'active', :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    );

    -- Finished Goods
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock, valuation_method,
        standard_rate, valuation_rate, reorder_level, reorder_qty, min_order_qty,
        has_serial_no, barcode, status, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'FG-WIDGET-001', 'Widget Pro',
        'Premium widget for industrial use', ig_fg_id,
        'stock', 'Nos', true, 'moving_average',
        599.00, 350.00, 50, 200, 10,
        true, '8901234567890', 'active', :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ),
    (
        gen_random_uuid(), :'org_id'::uuid, 'FG-GADGET-001', 'Gadget Max',
        'Multi-purpose gadget for home and office', ig_fg_id,
        'stock', 'Nos', true, 'moving_average',
        1299.00, 750.00, 25, 100, 5,
        true, '8901234567891', 'active', :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    );

    -- Consumables
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock, valuation_method,
        standard_rate, valuation_rate, reorder_level, reorder_qty, min_order_qty,
        status, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'CON-PACK-001', 'Packaging Box (Medium)',
        'Medium sized packaging box', ig_con_id,
        'stock', 'Nos', true, 'fifo',
        25.00, 18.00, 500, 2000, 100,
        'active', :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    );

    -- Services
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock,
        standard_rate, valuation_rate, status,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), :'org_id'::uuid, 'SRV-INSTALL-001', 'Installation Service',
        'Professional installation service', ig_srv_id,
        'service', 'Hrs', false,
        500.00, 0.00, 'active',
        :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    ),
    (
        gen_random_uuid(), :'org_id'::uuid, 'SRV-MAINT-001', 'Annual Maintenance Contract',
        'Yearly maintenance and support', ig_srv_id,
        'service', 'Nos', false,
        5000.00, 0.00, 'active',
        :'admin_user_id'::uuid, :'admin_user_id'::uuid, NOW(), NOW()
    );

    RAISE NOTICE '✓ Seeding completed successfully!';
    RAISE NOTICE '  Warehouses: 3';
    RAISE NOTICE '  Item Groups: 4';
    RAISE NOTICE '  Items: 7';
END $$;

-- ===========================================
-- Verification
-- ===========================================
SELECT 'Warehouses:' AS type, COUNT(*) AS count FROM warehouses_extended
UNION ALL
SELECT 'Item Groups:', COUNT(*) FROM item_groups
UNION ALL
SELECT 'Items:', COUNT(*) FROM items;
