-- ===========================================
-- Core Service - Foundation Seed Data
-- ===========================================
-- This script seeds foundation/master data for development and testing
-- Run this AFTER creating tables (02_create_foundation_tables.sql)
--
-- Pre-requisite:
--   - An organization must exist in identity_db
--   - Use the organization_id from identity_db
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/03_seed_foundation_data.sql
--   OR
--   psql -U horizon_user -d core_db -f 03_seed_foundation_data.sql

-- Connect to core_db (if running manually)
\c core_db;

-- ===========================================
-- SET VARIABLES
-- ===========================================
-- Replace this with your actual organization_id from identity_db
-- You can get it by: SELECT id FROM organizations WHERE slug = 'demo-org';

DO $$
DECLARE
    v_org_id UUID := 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'; -- Demo Organization ID
    v_user_id UUID := 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'; -- Demo Admin User ID

    -- Warehouse IDs
    v_main_warehouse_id UUID;
    v_store_warehouse_id UUID;
    v_transit_warehouse_id UUID;

    -- Item Group IDs
    v_raw_materials_id UUID;
    v_finished_goods_id UUID;
    v_consumables_id UUID;
    v_services_id UUID;

    -- Chart of Accounts IDs
    v_assets_id UUID;
    v_liabilities_id UUID;
    v_equity_id UUID;
    v_income_id UUID;
    v_expense_id UUID;

BEGIN
    -- ===========================================
    -- 1. SEED WAREHOUSES
    -- ===========================================
    RAISE NOTICE 'Seeding warehouses...';

    -- Main Warehouse
    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description,
        warehouse_type, address_line1, city, state, postal_code, country,
        contact_name, contact_phone, contact_email,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Main Warehouse', 'WH-MAIN', 'Primary warehouse for finished goods',
        'warehouse', '123 Industrial Area', 'Mumbai', 'Maharashtra', '400001', 'India',
        'John Smith', '+91-9876543210', 'warehouse@example.com',
        TRUE, TRUE, v_user_id, v_user_id
    ) RETURNING id INTO v_main_warehouse_id;

    -- Store Warehouse
    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description,
        warehouse_type, address_line1, city, state, postal_code, country,
        contact_name, contact_phone, contact_email,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Retail Store', 'WH-STORE', 'Retail store location',
        'store', '456 Market Street', 'Mumbai', 'Maharashtra', '400002', 'India',
        'Jane Doe', '+91-9876543211', 'store@example.com',
        TRUE, FALSE, v_user_id, v_user_id
    ) RETURNING id INTO v_store_warehouse_id;

    -- Transit Warehouse
    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description,
        warehouse_type, parent_warehouse_id,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Goods in Transit', 'WH-TRANSIT', 'Virtual warehouse for goods in transit',
        'transit', v_main_warehouse_id,
        TRUE, FALSE, v_user_id, v_user_id
    ) RETURNING id INTO v_transit_warehouse_id;

    -- Raw Materials Storage
    INSERT INTO warehouses_extended (
        id, organization_id, name, code, description,
        warehouse_type, parent_warehouse_id,
        address_line1, city, state, postal_code, country,
        total_capacity, capacity_uom,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Raw Materials Storage', 'WH-RAW', 'Storage for raw materials',
        'warehouse', v_main_warehouse_id,
        '123 Industrial Area, Block B', 'Mumbai', 'Maharashtra', '400001', 'India',
        10000, 'sqft',
        TRUE, FALSE, v_user_id, v_user_id
    );

    RAISE NOTICE 'Warehouses seeded successfully!';

    -- ===========================================
    -- 2. SEED ITEM GROUPS
    -- ===========================================
    RAISE NOTICE 'Seeding item groups...';

    -- Root level groups
    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Raw Materials', 'RAW', 'Raw materials for production',
        'fifo', 'Kg',
        TRUE, v_user_id, v_user_id
    ) RETURNING id INTO v_raw_materials_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Finished Goods', 'FG', 'Finished products ready for sale',
        'fifo', 'Nos',
        TRUE, v_user_id, v_user_id
    ) RETURNING id INTO v_finished_goods_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Consumables', 'CONS', 'Consumable items',
        'moving_average', 'Nos',
        TRUE, v_user_id, v_user_id
    ) RETURNING id INTO v_consumables_id;

    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES (
        gen_random_uuid(), v_org_id, 'Services', 'SVC', 'Service items',
        NULL, 'Hour',
        TRUE, v_user_id, v_user_id
    ) RETURNING id INTO v_services_id;

    -- Sub-groups under Raw Materials
    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        parent_id, default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, 'Metals', 'RAW-MTL', 'Metal raw materials', v_raw_materials_id, 'fifo', 'Kg', TRUE, v_user_id, v_user_id),
    (gen_random_uuid(), v_org_id, 'Plastics', 'RAW-PLS', 'Plastic raw materials', v_raw_materials_id, 'fifo', 'Kg', TRUE, v_user_id, v_user_id),
    (gen_random_uuid(), v_org_id, 'Chemicals', 'RAW-CHM', 'Chemical raw materials', v_raw_materials_id, 'fifo', 'L', TRUE, v_user_id, v_user_id);

    -- Sub-groups under Finished Goods
    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        parent_id, default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, 'Electronics', 'FG-ELEC', 'Electronic products', v_finished_goods_id, 'fifo', 'Nos', TRUE, v_user_id, v_user_id),
    (gen_random_uuid(), v_org_id, 'Furniture', 'FG-FURN', 'Furniture products', v_finished_goods_id, 'fifo', 'Nos', TRUE, v_user_id, v_user_id),
    (gen_random_uuid(), v_org_id, 'Apparel', 'FG-APRL', 'Clothing and apparel', v_finished_goods_id, 'moving_average', 'Nos', TRUE, v_user_id, v_user_id);

    -- Sub-groups under Consumables
    INSERT INTO item_groups (
        id, organization_id, name, code, description,
        parent_id, default_valuation_method, default_uom,
        is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, 'Office Supplies', 'CONS-OFF', 'Office consumables', v_consumables_id, 'moving_average', 'Nos', TRUE, v_user_id, v_user_id),
    (gen_random_uuid(), v_org_id, 'Packaging Materials', 'CONS-PKG', 'Packaging consumables', v_consumables_id, 'moving_average', 'Nos', TRUE, v_user_id, v_user_id);

    RAISE NOTICE 'Item groups seeded successfully!';

    -- ===========================================
    -- 3. SEED CUSTOMERS
    -- ===========================================
    RAISE NOTICE 'Seeding customers...';

    INSERT INTO customers (
        organization_id, customer_name, customer_code,
        email, phone, address_line1, city, state, postal_code, country,
        tax_number, status, credit_limit,
        created_by, updated_by
    ) VALUES
    (v_org_id, 'Acme Corporation', 'CUST-001', 'contact@acme.com', '+91-9876543001', '100 Business Park', 'Mumbai', 'Maharashtra', '400001', 'India', 'GSTIN001234567', 'active', 500000.00, v_user_id, v_user_id),
    (v_org_id, 'TechStart Solutions', 'CUST-002', 'sales@techstart.com', '+91-9876543002', '200 IT Hub', 'Bangalore', 'Karnataka', '560001', 'India', 'GSTIN002345678', 'active', 300000.00, v_user_id, v_user_id),
    (v_org_id, 'Green Earth Pvt Ltd', 'CUST-003', 'info@greenearth.com', '+91-9876543003', '50 Eco Park', 'Delhi', 'Delhi', '110001', 'India', 'GSTIN003456789', 'active', 200000.00, v_user_id, v_user_id),
    (v_org_id, 'Metro Retail Chain', 'CUST-004', 'purchase@metroretail.com', '+91-9876543004', 'Mall Road', 'Chennai', 'Tamil Nadu', '600001', 'India', 'GSTIN004567890', 'active', 1000000.00, v_user_id, v_user_id),
    (v_org_id, 'Sunrise Enterprises', 'CUST-005', 'orders@sunrise.com', '+91-9876543005', 'Industrial Estate', 'Pune', 'Maharashtra', '411001', 'India', 'GSTIN005678901', 'active', 150000.00, v_user_id, v_user_id),
    (v_org_id, 'Global Traders', 'CUST-006', 'trade@globaltraders.com', '+91-9876543006', 'Export Zone', 'Kolkata', 'West Bengal', '700001', 'India', 'GSTIN006789012', 'active', 750000.00, v_user_id, v_user_id),
    (v_org_id, 'Local Mart', 'CUST-007', 'shop@localmart.com', '+91-9876543007', 'Main Street', 'Hyderabad', 'Telangana', '500001', 'India', 'GSTIN007890123', 'active', 100000.00, v_user_id, v_user_id),
    (v_org_id, 'BuildRight Construction', 'CUST-008', 'supply@buildright.com', '+91-9876543008', 'Construction House', 'Ahmedabad', 'Gujarat', '380001', 'India', 'GSTIN008901234', 'active', 2000000.00, v_user_id, v_user_id),
    (v_org_id, 'FoodChain India', 'CUST-009', 'procurement@foodchain.com', '+91-9876543009', 'Food Park', 'Jaipur', 'Rajasthan', '302001', 'India', 'GSTIN009012345', 'active', 500000.00, v_user_id, v_user_id),
    (v_org_id, 'Digital Dynamics', 'CUST-010', 'buy@digitaldynamics.com', '+91-9876543010', 'Tech Tower', 'Noida', 'Uttar Pradesh', '201301', 'India', 'GSTIN010123456', 'active', 400000.00, v_user_id, v_user_id);

    RAISE NOTICE 'Customers seeded successfully!';

    -- ===========================================
    -- 4. SEED SUPPLIERS
    -- ===========================================
    RAISE NOTICE 'Seeding suppliers...';

    INSERT INTO suppliers (
        organization_id, supplier_name, supplier_code,
        email, phone, address_line1, city, state, postal_code, country,
        tax_number, status, payment_terms,
        created_by, updated_by
    ) VALUES
    (v_org_id, 'Steel India Ltd', 'SUPP-001', 'sales@steelindia.com', '+91-9812345001', 'Steel Complex', 'Jamshedpur', 'Jharkhand', '831001', 'India', 'GSTIN101234567', 'active', 30, v_user_id, v_user_id),
    (v_org_id, 'Plastic World', 'SUPP-002', 'orders@plasticworld.com', '+91-9812345002', 'Polymer Park', 'Surat', 'Gujarat', '395001', 'India', 'GSTIN102345678', 'active', 45, v_user_id, v_user_id),
    (v_org_id, 'Chemical Solutions', 'SUPP-003', 'supply@chemsol.com', '+91-9812345003', 'Chemical Hub', 'Vadodara', 'Gujarat', '390001', 'India', 'GSTIN103456789', 'active', 30, v_user_id, v_user_id),
    (v_org_id, 'Electronic Components Inc', 'SUPP-004', 'components@ecinc.com', '+91-9812345004', 'Electronics City', 'Bangalore', 'Karnataka', '560100', 'India', 'GSTIN104567890', 'active', 15, v_user_id, v_user_id),
    (v_org_id, 'PackRight Industries', 'SUPP-005', 'packaging@packright.com', '+91-9812345005', 'Packaging Zone', 'Faridabad', 'Haryana', '121001', 'India', 'GSTIN105678901', 'active', 30, v_user_id, v_user_id),
    (v_org_id, 'Timber Trade Co', 'SUPP-006', 'wood@timbertrade.com', '+91-9812345006', 'Timber Yard', 'Nagpur', 'Maharashtra', '440001', 'India', 'GSTIN106789012', 'active', 60, v_user_id, v_user_id),
    (v_org_id, 'Fabric Mills', 'SUPP-007', 'textile@fabricmills.com', '+91-9812345007', 'Textile Park', 'Surat', 'Gujarat', '395002', 'India', 'GSTIN107890123', 'active', 45, v_user_id, v_user_id),
    (v_org_id, 'Hardware Hub', 'SUPP-008', 'parts@hardwarehub.com', '+91-9812345008', 'Industrial Estate', 'Ludhiana', 'Punjab', '141001', 'India', 'GSTIN108901234', 'active', 30, v_user_id, v_user_id),
    (v_org_id, 'Office Essentials', 'SUPP-009', 'supply@officeess.com', '+91-9812345009', 'Commercial Complex', 'Delhi', 'Delhi', '110002', 'India', 'GSTIN109012345', 'active', 15, v_user_id, v_user_id),
    (v_org_id, 'Import Export Trading', 'SUPP-010', 'trade@importexport.com', '+91-9812345010', 'Port Area', 'Mumbai', 'Maharashtra', '400003', 'India', 'GSTIN110123456', 'active', 60, v_user_id, v_user_id);

    RAISE NOTICE 'Suppliers seeded successfully!';

    -- ===========================================
    -- 5. SEED CHART OF ACCOUNTS
    -- ===========================================
    RAISE NOTICE 'Seeding chart of accounts...';

    -- Top-level accounts
    INSERT INTO chart_of_accounts (
        id, organization_id, account_code, account_name, account_type,
        level, is_group, is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, '1000', 'Assets', 'asset', 1, TRUE, TRUE, v_user_id, v_user_id) RETURNING id INTO v_assets_id;

    INSERT INTO chart_of_accounts (
        id, organization_id, account_code, account_name, account_type,
        level, is_group, is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, '2000', 'Liabilities', 'liability', 1, TRUE, TRUE, v_user_id, v_user_id) RETURNING id INTO v_liabilities_id;

    INSERT INTO chart_of_accounts (
        id, organization_id, account_code, account_name, account_type,
        level, is_group, is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, '3000', 'Equity', 'equity', 1, TRUE, TRUE, v_user_id, v_user_id) RETURNING id INTO v_equity_id;

    INSERT INTO chart_of_accounts (
        id, organization_id, account_code, account_name, account_type,
        level, is_group, is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, '4000', 'Income', 'income', 1, TRUE, TRUE, v_user_id, v_user_id) RETURNING id INTO v_income_id;

    INSERT INTO chart_of_accounts (
        id, organization_id, account_code, account_name, account_type,
        level, is_group, is_active, created_by, updated_by
    ) VALUES
    (gen_random_uuid(), v_org_id, '5000', 'Expenses', 'expense', 1, TRUE, TRUE, v_user_id, v_user_id) RETURNING id INTO v_expense_id;

    -- Asset sub-accounts
    INSERT INTO chart_of_accounts (
        organization_id, account_code, account_name, account_type,
        parent_account_id, level, is_group, is_active, created_by, updated_by
    ) VALUES
    (v_org_id, '1100', 'Current Assets', 'asset', v_assets_id, 2, TRUE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1200', 'Fixed Assets', 'asset', v_assets_id, 2, TRUE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1110', 'Cash and Bank', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1120', 'Accounts Receivable', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1130', 'Inventory', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1140', 'Stock in Hand', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Liability sub-accounts
    INSERT INTO chart_of_accounts (
        organization_id, account_code, account_name, account_type,
        parent_account_id, level, is_group, is_active, created_by, updated_by
    ) VALUES
    (v_org_id, '2100', 'Current Liabilities', 'liability', v_liabilities_id, 2, TRUE, TRUE, v_user_id, v_user_id),
    (v_org_id, '2200', 'Long-term Liabilities', 'liability', v_liabilities_id, 2, TRUE, TRUE, v_user_id, v_user_id),
    (v_org_id, '2110', 'Accounts Payable', 'liability', v_liabilities_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '2120', 'Tax Payable', 'liability', v_liabilities_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Equity sub-accounts
    INSERT INTO chart_of_accounts (
        organization_id, account_code, account_name, account_type,
        parent_account_id, level, is_group, is_active, created_by, updated_by
    ) VALUES
    (v_org_id, '3100', 'Share Capital', 'equity', v_equity_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '3200', 'Retained Earnings', 'equity', v_equity_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Income sub-accounts
    INSERT INTO chart_of_accounts (
        organization_id, account_code, account_name, account_type,
        parent_account_id, level, is_group, is_active, created_by, updated_by
    ) VALUES
    (v_org_id, '4100', 'Sales Revenue', 'income', v_income_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '4200', 'Service Revenue', 'income', v_income_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '4300', 'Other Income', 'income', v_income_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Expense sub-accounts
    INSERT INTO chart_of_accounts (
        organization_id, account_code, account_name, account_type,
        parent_account_id, level, is_group, is_active, created_by, updated_by
    ) VALUES
    (v_org_id, '5100', 'Cost of Goods Sold', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5200', 'Operating Expenses', 'expense', v_expense_id, 2, TRUE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5210', 'Salaries and Wages', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5220', 'Rent Expense', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5230', 'Utilities', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5240', 'Depreciation', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5300', 'Administrative Expenses', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    RAISE NOTICE 'Chart of accounts seeded successfully!';

    -- ===========================================
    -- SUMMARY
    -- ===========================================
    RAISE NOTICE '';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'SEED DATA SUMMARY';
    RAISE NOTICE '===========================================';

END $$;

-- Show counts
SELECT 'warehouses_extended' AS table_name, COUNT(*) AS record_count FROM warehouses_extended
UNION ALL
SELECT 'item_groups', COUNT(*) FROM item_groups
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'suppliers', COUNT(*) FROM suppliers
UNION ALL
SELECT 'chart_of_accounts', COUNT(*) FROM chart_of_accounts
ORDER BY table_name;
