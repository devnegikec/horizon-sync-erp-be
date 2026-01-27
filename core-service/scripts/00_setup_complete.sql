-- ===========================================
-- Core Service - Complete Database Setup
-- ===========================================
-- This script runs all setup scripts in order:
--   1. Create enum types
--   2. Create foundation tables
--   3. Seed foundation data
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/00_setup_complete.sql
--   OR
--   psql -U horizon_user -d core_db -f 00_setup_complete.sql

-- Connect to core_db
\c core_db;

\echo '============================================='
\echo 'STEP 1: Creating Enum Types'
\echo '============================================='

-- ===========================================
-- DROP EXISTING TYPES (if any)
-- ===========================================
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
DROP TYPE IF EXISTS customerstatus CASCADE;
DROP TYPE IF EXISTS supplierstatus CASCADE;
DROP TYPE IF EXISTS accounttype CASCADE;
DROP TYPE IF EXISTS invoicetype CASCADE;
DROP TYPE IF EXISTS invoicestatus CASCADE;
DROP TYPE IF EXISTS paymenttype CASCADE;
DROP TYPE IF EXISTS paymentstatus CASCADE;
DROP TYPE IF EXISTS paymentmethod CASCADE;
DROP TYPE IF EXISTS journalstatus CASCADE;
DROP TYPE IF EXISTS pickliststatus CASCADE;

-- Inventory Enums
CREATE TYPE itemtype AS ENUM ('stock', 'non_stock', 'service', 'fixed_asset');
CREATE TYPE itemstatus AS ENUM ('active', 'inactive', 'discontinued');
CREATE TYPE valuationmethod AS ENUM ('fifo', 'lifo', 'moving_average', 'standard');
CREATE TYPE documentstatus AS ENUM ('draft', 'submitted', 'cancelled');
CREATE TYPE warehousetype AS ENUM ('warehouse', 'store', 'virtual', 'transit');
CREATE TYPE stockentrytype AS ENUM ('material_receipt', 'material_issue', 'material_transfer', 'manufacture', 'repack', 'send_to_subcontractor');
CREATE TYPE stockentrystatus AS ENUM ('draft', 'submitted', 'cancelled');
CREATE TYPE movementtype AS ENUM ('in', 'out', 'transfer', 'adjustment');
CREATE TYPE batchstatus AS ENUM ('active', 'expired', 'consumed');

-- Quality Inspection Enums
CREATE TYPE inspectiontype AS ENUM ('incoming', 'outgoing', 'in_process');
CREATE TYPE inspectionstatus AS ENUM ('pending', 'accepted', 'rejected');
CREATE TYPE readingtype AS ENUM ('numeric', 'text', 'pass_fail');

-- Customer/Supplier Enums
CREATE TYPE customerstatus AS ENUM ('active', 'inactive', 'blocked');
CREATE TYPE supplierstatus AS ENUM ('active', 'inactive', 'blocked');

-- Accounting/Billing Enums
CREATE TYPE accounttype AS ENUM ('asset', 'liability', 'equity', 'income', 'expense');
CREATE TYPE invoicetype AS ENUM ('sales', 'purchase');
CREATE TYPE invoicestatus AS ENUM ('draft', 'pending', 'paid', 'partial', 'overdue', 'cancelled');
CREATE TYPE paymenttype AS ENUM ('receive', 'pay');
CREATE TYPE paymentstatus AS ENUM ('pending', 'completed', 'failed', 'cancelled');
CREATE TYPE paymentmethod AS ENUM ('cash', 'bank_transfer', 'credit_card', 'debit_card', 'cheque', 'upi', 'other');
CREATE TYPE journalstatus AS ENUM ('draft', 'posted', 'cancelled');

-- Order Processing Enums
CREATE TYPE pickliststatus AS ENUM ('draft', 'in_progress', 'completed', 'cancelled');

\echo 'Enum types created successfully!'

\echo ''
\echo '============================================='
\echo 'STEP 2: Creating Foundation Tables'
\echo '============================================='

-- ===========================================
-- 1. WAREHOUSES_EXTENDED
-- ===========================================
CREATE TABLE IF NOT EXISTS warehouses_extended (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT,
    parent_warehouse_id UUID,
    warehouse_type warehousetype DEFAULT 'warehouse',
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    contact_name VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(255),
    total_capacity INTEGER,
    capacity_uom VARCHAR(50),
    stock_account_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_warehouses_extended_parent FOREIGN KEY (parent_warehouse_id)
        REFERENCES warehouses_extended(id) ON DELETE SET NULL,
    CONSTRAINT uq_warehouses_extended_org_code UNIQUE (organization_id, code)
);

CREATE INDEX IF NOT EXISTS ix_warehouses_extended_organization_id ON warehouses_extended(organization_id);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_code ON warehouses_extended(code);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_parent_warehouse_id ON warehouses_extended(parent_warehouse_id);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_is_active ON warehouses_extended(is_active);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_deleted_at ON warehouses_extended(deleted_at);

-- ===========================================
-- 2. ITEM_GROUPS
-- ===========================================
CREATE TABLE IF NOT EXISTS item_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT,
    parent_id UUID,
    default_valuation_method valuationmethod,
    default_uom VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_item_groups_parent FOREIGN KEY (parent_id)
        REFERENCES item_groups(id) ON DELETE SET NULL,
    CONSTRAINT uq_item_groups_org_code UNIQUE (organization_id, code)
);

CREATE INDEX IF NOT EXISTS ix_item_groups_organization_id ON item_groups(organization_id);
CREATE INDEX IF NOT EXISTS ix_item_groups_code ON item_groups(code);
CREATE INDEX IF NOT EXISTS ix_item_groups_parent_id ON item_groups(parent_id);
CREATE INDEX IF NOT EXISTS ix_item_groups_is_active ON item_groups(is_active);
CREATE INDEX IF NOT EXISTS ix_item_groups_deleted_at ON item_groups(deleted_at);

-- ===========================================
-- 3. CUSTOMERS
-- ===========================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    customer_code VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    tax_number VARCHAR(50),
    status customerstatus DEFAULT 'active',
    credit_limit NUMERIC(15,2) DEFAULT 0,
    outstanding_balance NUMERIC(15,2) DEFAULT 0,
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_customers_org_code UNIQUE (organization_id, customer_code)
);

CREATE INDEX IF NOT EXISTS ix_customers_organization_id ON customers(organization_id);
CREATE INDEX IF NOT EXISTS ix_customers_customer_code ON customers(customer_code);
CREATE INDEX IF NOT EXISTS ix_customers_customer_name ON customers(customer_name);
CREATE INDEX IF NOT EXISTS ix_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS ix_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS ix_customers_deleted_at ON customers(deleted_at);

-- ===========================================
-- 4. SUPPLIERS
-- ===========================================
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    supplier_name VARCHAR(255) NOT NULL,
    supplier_code VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    tax_number VARCHAR(50),
    status supplierstatus DEFAULT 'active',
    payment_terms INTEGER DEFAULT 30,
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_suppliers_org_code UNIQUE (organization_id, supplier_code)
);

CREATE INDEX IF NOT EXISTS ix_suppliers_organization_id ON suppliers(organization_id);
CREATE INDEX IF NOT EXISTS ix_suppliers_supplier_code ON suppliers(supplier_code);
CREATE INDEX IF NOT EXISTS ix_suppliers_supplier_name ON suppliers(supplier_name);
CREATE INDEX IF NOT EXISTS ix_suppliers_email ON suppliers(email);
CREATE INDEX IF NOT EXISTS ix_suppliers_status ON suppliers(status);
CREATE INDEX IF NOT EXISTS ix_suppliers_deleted_at ON suppliers(deleted_at);

-- ===========================================
-- 5. CHART_OF_ACCOUNTS
-- ===========================================
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type accounttype NOT NULL,
    parent_account_id UUID,
    level INTEGER DEFAULT 1,
    is_group BOOLEAN DEFAULT FALSE,
    opening_balance NUMERIC(15,2) DEFAULT 0,
    current_balance NUMERIC(15,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    tags JSONB,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_chart_of_accounts_parent FOREIGN KEY (parent_account_id)
        REFERENCES chart_of_accounts(id) ON DELETE SET NULL,
    CONSTRAINT uq_chart_of_accounts_org_code UNIQUE (organization_id, account_code)
);

CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_organization_id ON chart_of_accounts(organization_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_account_code ON chart_of_accounts(account_code);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_account_type ON chart_of_accounts(account_type);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_parent_account_id ON chart_of_accounts(parent_account_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_is_active ON chart_of_accounts(is_active);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_deleted_at ON chart_of_accounts(deleted_at);

\echo 'Foundation tables created successfully!'

\echo ''
\echo '============================================='
\echo 'STEP 3: Seeding Foundation Data'
\echo '============================================='

-- ===========================================
-- SEED DATA
-- ===========================================
DO $$
DECLARE
    v_org_id UUID := 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
    v_user_id UUID := 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22';

    v_main_warehouse_id UUID;
    v_raw_materials_id UUID;
    v_finished_goods_id UUID;
    v_consumables_id UUID;
    v_services_id UUID;

    v_assets_id UUID;
    v_liabilities_id UUID;
    v_equity_id UUID;
    v_income_id UUID;
    v_expense_id UUID;

BEGIN
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
        organization_id, name, code, description,
        warehouse_type, address_line1, city, state, postal_code, country,
        contact_name, contact_phone, contact_email,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        v_org_id, 'Retail Store', 'WH-STORE', 'Retail store location',
        'store', '456 Market Street', 'Mumbai', 'Maharashtra', '400002', 'India',
        'Jane Doe', '+91-9876543211', 'store@example.com',
        TRUE, FALSE, v_user_id, v_user_id
    );

    -- Transit Warehouse
    INSERT INTO warehouses_extended (
        organization_id, name, code, description,
        warehouse_type, parent_warehouse_id,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        v_org_id, 'Goods in Transit', 'WH-TRANSIT', 'Virtual warehouse for goods in transit',
        'transit', v_main_warehouse_id,
        TRUE, FALSE, v_user_id, v_user_id
    );

    -- Raw Materials Storage
    INSERT INTO warehouses_extended (
        organization_id, name, code, description,
        warehouse_type, parent_warehouse_id,
        address_line1, city, state, postal_code, country,
        total_capacity, capacity_uom,
        is_active, is_default, created_by, updated_by
    ) VALUES (
        v_org_id, 'Raw Materials Storage', 'WH-RAW', 'Storage for raw materials',
        'warehouse', v_main_warehouse_id,
        '123 Industrial Area, Block B', 'Mumbai', 'Maharashtra', '400001', 'India',
        10000, 'sqft',
        TRUE, FALSE, v_user_id, v_user_id
    );

    RAISE NOTICE 'Seeding item groups...';

    -- Root level groups
    INSERT INTO item_groups (organization_id, name, code, description, default_valuation_method, default_uom, is_active, created_by, updated_by)
    VALUES (v_org_id, 'Raw Materials', 'RAW', 'Raw materials for production', 'fifo', 'Kg', TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_raw_materials_id;

    INSERT INTO item_groups (organization_id, name, code, description, default_valuation_method, default_uom, is_active, created_by, updated_by)
    VALUES (v_org_id, 'Finished Goods', 'FG', 'Finished products ready for sale', 'fifo', 'Nos', TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_finished_goods_id;

    INSERT INTO item_groups (organization_id, name, code, description, default_valuation_method, default_uom, is_active, created_by, updated_by)
    VALUES (v_org_id, 'Consumables', 'CONS', 'Consumable items', 'moving_average', 'Nos', TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_consumables_id;

    INSERT INTO item_groups (organization_id, name, code, description, default_uom, is_active, created_by, updated_by)
    VALUES (v_org_id, 'Services', 'SVC', 'Service items', 'Hour', TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_services_id;

    -- Sub-groups under Raw Materials
    INSERT INTO item_groups (organization_id, name, code, description, parent_id, default_valuation_method, default_uom, is_active, created_by, updated_by)
    VALUES
    (v_org_id, 'Metals', 'RAW-MTL', 'Metal raw materials', v_raw_materials_id, 'fifo', 'Kg', TRUE, v_user_id, v_user_id),
    (v_org_id, 'Plastics', 'RAW-PLS', 'Plastic raw materials', v_raw_materials_id, 'fifo', 'Kg', TRUE, v_user_id, v_user_id),
    (v_org_id, 'Chemicals', 'RAW-CHM', 'Chemical raw materials', v_raw_materials_id, 'fifo', 'L', TRUE, v_user_id, v_user_id);

    -- Sub-groups under Finished Goods
    INSERT INTO item_groups (organization_id, name, code, description, parent_id, default_valuation_method, default_uom, is_active, created_by, updated_by)
    VALUES
    (v_org_id, 'Electronics', 'FG-ELEC', 'Electronic products', v_finished_goods_id, 'fifo', 'Nos', TRUE, v_user_id, v_user_id),
    (v_org_id, 'Furniture', 'FG-FURN', 'Furniture products', v_finished_goods_id, 'fifo', 'Nos', TRUE, v_user_id, v_user_id),
    (v_org_id, 'Apparel', 'FG-APRL', 'Clothing and apparel', v_finished_goods_id, 'moving_average', 'Nos', TRUE, v_user_id, v_user_id);

    -- Sub-groups under Consumables
    INSERT INTO item_groups (organization_id, name, code, description, parent_id, default_valuation_method, default_uom, is_active, created_by, updated_by)
    VALUES
    (v_org_id, 'Office Supplies', 'CONS-OFF', 'Office consumables', v_consumables_id, 'moving_average', 'Nos', TRUE, v_user_id, v_user_id),
    (v_org_id, 'Packaging Materials', 'CONS-PKG', 'Packaging consumables', v_consumables_id, 'moving_average', 'Nos', TRUE, v_user_id, v_user_id);

    RAISE NOTICE 'Seeding customers...';

    INSERT INTO customers (organization_id, customer_name, customer_code, email, phone, address_line1, city, state, postal_code, country, tax_number, status, credit_limit, created_by, updated_by)
    VALUES
    (v_org_id, 'Acme Corporation', 'CUST-001', 'contact@acme.com', '+91-9876543001', '100 Business Park', 'Mumbai', 'Maharashtra', '400001', 'India', 'GSTIN001234567', 'active', 500000.00, v_user_id, v_user_id),
    (v_org_id, 'TechStart Solutions', 'CUST-002', 'sales@techstart.com', '+91-9876543002', '200 IT Hub', 'Bangalore', 'Karnataka', '560001', 'India', 'GSTIN002345678', 'active', 300000.00, v_user_id, v_user_id),
    (v_org_id, 'Green Earth Pvt Ltd', 'CUST-003', 'info@greenearth.com', '+91-9876543003', '50 Eco Park', 'Delhi', 'Delhi', '110001', 'India', 'GSTIN003456789', 'active', 200000.00, v_user_id, v_user_id),
    (v_org_id, 'Metro Retail Chain', 'CUST-004', 'purchase@metroretail.com', '+91-9876543004', 'Mall Road', 'Chennai', 'Tamil Nadu', '600001', 'India', 'GSTIN004567890', 'active', 1000000.00, v_user_id, v_user_id),
    (v_org_id, 'Sunrise Enterprises', 'CUST-005', 'orders@sunrise.com', '+91-9876543005', 'Industrial Estate', 'Pune', 'Maharashtra', '411001', 'India', 'GSTIN005678901', 'active', 150000.00, v_user_id, v_user_id);

    RAISE NOTICE 'Seeding suppliers...';

    INSERT INTO suppliers (organization_id, supplier_name, supplier_code, email, phone, address_line1, city, state, postal_code, country, tax_number, status, payment_terms, created_by, updated_by)
    VALUES
    (v_org_id, 'Steel India Ltd', 'SUPP-001', 'sales@steelindia.com', '+91-9812345001', 'Steel Complex', 'Jamshedpur', 'Jharkhand', '831001', 'India', 'GSTIN101234567', 'active', 30, v_user_id, v_user_id),
    (v_org_id, 'Plastic World', 'SUPP-002', 'orders@plasticworld.com', '+91-9812345002', 'Polymer Park', 'Surat', 'Gujarat', '395001', 'India', 'GSTIN102345678', 'active', 45, v_user_id, v_user_id),
    (v_org_id, 'Chemical Solutions', 'SUPP-003', 'supply@chemsol.com', '+91-9812345003', 'Chemical Hub', 'Vadodara', 'Gujarat', '390001', 'India', 'GSTIN103456789', 'active', 30, v_user_id, v_user_id),
    (v_org_id, 'Electronic Components Inc', 'SUPP-004', 'components@ecinc.com', '+91-9812345004', 'Electronics City', 'Bangalore', 'Karnataka', '560100', 'India', 'GSTIN104567890', 'active', 15, v_user_id, v_user_id),
    (v_org_id, 'PackRight Industries', 'SUPP-005', 'packaging@packright.com', '+91-9812345005', 'Packaging Zone', 'Faridabad', 'Haryana', '121001', 'India', 'GSTIN105678901', 'active', 30, v_user_id, v_user_id);

    RAISE NOTICE 'Seeding chart of accounts...';

    -- Top-level accounts
    INSERT INTO chart_of_accounts (id, organization_id, account_code, account_name, account_type, level, is_group, is_active, created_by, updated_by)
    VALUES (gen_random_uuid(), v_org_id, '1000', 'Assets', 'asset', 1, TRUE, TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_assets_id;

    INSERT INTO chart_of_accounts (id, organization_id, account_code, account_name, account_type, level, is_group, is_active, created_by, updated_by)
    VALUES (gen_random_uuid(), v_org_id, '2000', 'Liabilities', 'liability', 1, TRUE, TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_liabilities_id;

    INSERT INTO chart_of_accounts (id, organization_id, account_code, account_name, account_type, level, is_group, is_active, created_by, updated_by)
    VALUES (gen_random_uuid(), v_org_id, '3000', 'Equity', 'equity', 1, TRUE, TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_equity_id;

    INSERT INTO chart_of_accounts (id, organization_id, account_code, account_name, account_type, level, is_group, is_active, created_by, updated_by)
    VALUES (gen_random_uuid(), v_org_id, '4000', 'Income', 'income', 1, TRUE, TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_income_id;

    INSERT INTO chart_of_accounts (id, organization_id, account_code, account_name, account_type, level, is_group, is_active, created_by, updated_by)
    VALUES (gen_random_uuid(), v_org_id, '5000', 'Expenses', 'expense', 1, TRUE, TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_expense_id;

    -- Asset sub-accounts
    INSERT INTO chart_of_accounts (organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, is_active, created_by, updated_by)
    VALUES
    (v_org_id, '1110', 'Cash and Bank', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1120', 'Accounts Receivable', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1130', 'Inventory', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '1140', 'Stock in Hand', 'asset', v_assets_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Liability sub-accounts
    INSERT INTO chart_of_accounts (organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, is_active, created_by, updated_by)
    VALUES
    (v_org_id, '2110', 'Accounts Payable', 'liability', v_liabilities_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '2120', 'Tax Payable', 'liability', v_liabilities_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Income sub-accounts
    INSERT INTO chart_of_accounts (organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, is_active, created_by, updated_by)
    VALUES
    (v_org_id, '4100', 'Sales Revenue', 'income', v_income_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '4200', 'Service Revenue', 'income', v_income_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    -- Expense sub-accounts
    INSERT INTO chart_of_accounts (organization_id, account_code, account_name, account_type, parent_account_id, level, is_group, is_active, created_by, updated_by)
    VALUES
    (v_org_id, '5100', 'Cost of Goods Sold', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5200', 'Operating Expenses', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5210', 'Salaries and Wages', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id),
    (v_org_id, '5220', 'Rent Expense', 'expense', v_expense_id, 2, FALSE, TRUE, v_user_id, v_user_id);

    RAISE NOTICE 'Seed data inserted successfully!';

END $$;

\echo ''
\echo '============================================='
\echo 'SETUP COMPLETE - Summary'
\echo '============================================='

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

\echo ''
\echo 'Database setup completed successfully!'
\echo 'You can now start the core-service.'
