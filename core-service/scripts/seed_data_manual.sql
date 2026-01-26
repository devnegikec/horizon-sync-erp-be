-- ===========================================
-- Core Service - Manual Seed Data Script
-- ===========================================
-- This script manually inserts seed data into core_db
-- It fetches organization_id and admin_user_id from identity_db
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/seed_data_manual.sql
--   OR
--   psql -U horizon_user -d core_db -f seed_data_manual.sql

\c core_db;

-- ===========================================
-- Step 1: Get IDs from identity_db
-- ===========================================
DO $$
DECLARE
    org_id UUID;
    admin_user_id UUID;
    wh_main_id UUID;
    wh_store_id UUID;
    wh_transit_id UUID;
    ig_rm_id UUID;
    ig_fg_id UUID;
    ig_con_id UUID;
    ig_srv_id UUID;
BEGIN
    -- Get organization ID from identity_db
    SELECT id INTO org_id
    FROM dblink('dbname=identity_db user=horizon_user password=horizon_pass',
        'SELECT id FROM organizations WHERE slug = ''default-org'' LIMIT 1')
    AS t(id UUID);

    -- Get admin user ID from identity_db
    SELECT id INTO admin_user_id
    FROM dblink('dbname=identity_db user=horizon_user password=horizon_pass',
        'SELECT id FROM users WHERE email = ''admin@example.com'' LIMIT 1')
    AS t(id UUID);

    -- If dblink doesn't work, use direct connection
    -- You may need to run these queries separately:
    -- \c identity_db;
    -- SELECT id FROM organizations WHERE slug = 'default-org';
    -- SELECT id FROM users WHERE email = 'admin@example.com';
    -- \c core_db;
    -- Then manually set: org_id := 'paste-uuid-here';
    --                    admin_user_id := 'paste-uuid-here';

    -- For now, we'll use a simpler approach - fetch via psql variables
    RAISE NOTICE 'Organization ID: %', org_id;
    RAISE NOTICE 'Admin User ID: %', admin_user_id;

    -- If IDs are NULL, you need to fetch them manually first
    IF org_id IS NULL OR admin_user_id IS NULL THEN
        RAISE EXCEPTION 'Could not fetch organization or admin user ID. Please run the queries manually:

        1. Connect to identity_db:
           \c identity_db;

        2. Get organization ID:
           SELECT id FROM organizations WHERE slug = ''default-org'';

        3. Get admin user ID:
           SELECT id FROM users WHERE email = ''admin@example.com'';

        4. Then update this script with the UUIDs and run again.';
    END IF;

    -- ===========================================
    -- Step 2: Create Warehouses
    -- ===========================================
    RAISE NOTICE 'Creating warehouses...';

    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description, warehouse_type,
        address_line1, city, state, postal_code, country,
        is_active, is_default, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Main Warehouse', 'WH-MAIN',
        'Primary warehouse for storage', 'warehouse',
        '123 Industrial Ave', 'Mumbai', 'Maharashtra', '400001', 'India',
        true, true, admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO wh_main_id;

    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description, warehouse_type,
        address_line1, city, state, postal_code, country,
        is_active, is_default, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Retail Store', 'WH-STORE',
        'Retail outlet for direct sales', 'store',
        '456 Market Street', 'Mumbai', 'Maharashtra', '400002', 'India',
        true, false, admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO wh_store_id;

    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description, warehouse_type,
        is_active, is_default, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Transit Warehouse', 'WH-TRANSIT',
        'Temporary storage during transit', 'transit',
        true, false, admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO wh_transit_id;

    RAISE NOTICE '✓ Created 3 warehouses';

    -- ===========================================
    -- Step 3: Create Item Groups
    -- ===========================================
    RAISE NOTICE 'Creating item groups...';

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Raw Materials', 'RM',
        'Raw materials for production', 'fifo', 'Kg', true,
        admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO ig_rm_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Finished Goods', 'FG',
        'Finished products ready for sale', 'moving_average', 'Nos', true,
        admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO ig_fg_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Consumables', 'CON',
        'Consumable items', 'fifo', 'Nos', true,
        admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO ig_con_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_uom, is_active,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'Services', 'SRV',
        'Service items (non-stock)', 'Hrs', true,
        admin_user_id, admin_user_id, NOW(), NOW()
    ) RETURNING id INTO ig_srv_id;

    RAISE NOTICE '✓ Created 4 item groups';

    -- ===========================================
    -- Step 4: Create Items
    -- ===========================================
    RAISE NOTICE 'Creating items...';

    -- Raw Materials
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock, valuation_method,
        standard_rate, valuation_rate, reorder_level, reorder_qty, min_order_qty,
        has_batch_no, status, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'RM-STEEL-001', 'Steel Sheet (2mm)',
        'High quality steel sheet, 2mm thickness', ig_rm_id,
        'stock', 'Kg', true, 'fifo',
        85.00, 75.00, 100, 500, 50,
        true, 'active', admin_user_id, admin_user_id, NOW(), NOW()
    ),
    (
        gen_random_uuid(), org_id, 'RM-PLAST-001', 'ABS Plastic Granules',
        'ABS plastic granules for injection molding', ig_rm_id,
        'stock', 'Kg', true, 'moving_average',
        120.00, 100.00, 200, 1000, 100,
        false, 'active', admin_user_id, admin_user_id, NOW(), NOW()
    );

    -- Finished Goods
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock, valuation_method,
        standard_rate, valuation_rate, reorder_level, reorder_qty, min_order_qty,
        has_serial_no, barcode, status, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'FG-WIDGET-001', 'Widget Pro',
        'Premium widget for industrial use', ig_fg_id,
        'stock', 'Nos', true, 'moving_average',
        599.00, 350.00, 50, 200, 10,
        true, '8901234567890', 'active', admin_user_id, admin_user_id, NOW(), NOW()
    ),
    (
        gen_random_uuid(), org_id, 'FG-GADGET-001', 'Gadget Max',
        'Multi-purpose gadget for home and office', ig_fg_id,
        'stock', 'Nos', true, 'moving_average',
        1299.00, 750.00, 25, 100, 5,
        true, '8901234567891', 'active', admin_user_id, admin_user_id, NOW(), NOW()
    );

    -- Consumables
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock, valuation_method,
        standard_rate, valuation_rate, reorder_level, reorder_qty, min_order_qty,
        status, created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'CON-PACK-001', 'Packaging Box (Medium)',
        'Medium sized packaging box', ig_con_id,
        'stock', 'Nos', true, 'fifo',
        25.00, 18.00, 500, 2000, 100,
        'active', admin_user_id, admin_user_id, NOW(), NOW()
    );

    -- Services
    INSERT INTO items (
        id, organization_id, item_code, item_name, description, item_group_id,
        item_type, uom, maintain_stock,
        standard_rate, valuation_rate, status,
        created_by, updated_by, created_at, updated_at
    ) VALUES
    (
        gen_random_uuid(), org_id, 'SRV-INSTALL-001', 'Installation Service',
        'Professional installation service', ig_srv_id,
        'service', 'Hrs', false,
        500.00, 0.00, 'active',
        admin_user_id, admin_user_id, NOW(), NOW()
    ),
    (
        gen_random_uuid(), org_id, 'SRV-MAINT-001', 'Annual Maintenance Contract',
        'Yearly maintenance and support', ig_srv_id,
        'service', 'Nos', false,
        5000.00, 0.00, 'active',
        admin_user_id, admin_user_id, NOW(), NOW()
    );

    RAISE NOTICE '✓ Created 7 items';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Core Service database seeding completed successfully!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Seeded Data Summary:';
    RAISE NOTICE '  Warehouses: 3';
    RAISE NOTICE '  Item Groups: 4';
    RAISE NOTICE '  Items: 7';
    RAISE NOTICE '============================================================';

END $$;
