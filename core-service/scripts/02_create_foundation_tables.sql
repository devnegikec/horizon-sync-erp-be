-- ===========================================
-- Core Service - Foundation Tables
-- ===========================================
-- This script creates foundation/master tables for core-service
-- Run this AFTER creating enum types (01_create_enums.sql)
--
-- Tables:
--   1. warehouses_extended
--   2. item_groups
--   3. customers
--   4. suppliers
--   5. chart_of_accounts
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/02_create_foundation_tables.sql
--   OR
--   psql -U horizon_user -d core_db -f 02_create_foundation_tables.sql

-- Connect to core_db (if running manually)
\c core_db;

-- ===========================================
-- 1. WAREHOUSES_EXTENDED
-- ===========================================
-- Extended warehouse model with hierarchy, capacity, and location
CREATE TABLE IF NOT EXISTS warehouses_extended (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,

    -- Basic Information
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT,

    -- Hierarchy
    parent_warehouse_id UUID,
    warehouse_type warehousetype DEFAULT 'warehouse',

    -- Address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),

    -- Contact
    contact_name VARCHAR(255),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(255),

    -- Capacity
    total_capacity INTEGER,
    capacity_uom VARCHAR(50),

    -- Accounting
    stock_account_id UUID,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,

    -- Extra
    extra_data JSONB,

    -- Audit fields
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT fk_warehouses_extended_parent FOREIGN KEY (parent_warehouse_id)
        REFERENCES warehouses_extended(id) ON DELETE SET NULL,
    CONSTRAINT uq_warehouses_extended_org_code UNIQUE (organization_id, code)
);

-- Indexes for warehouses_extended
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_organization_id ON warehouses_extended(organization_id);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_code ON warehouses_extended(code);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_parent_warehouse_id ON warehouses_extended(parent_warehouse_id);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_is_active ON warehouses_extended(is_active);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_deleted_at ON warehouses_extended(deleted_at);

-- ===========================================
-- 2. ITEM_GROUPS
-- ===========================================
-- Item categorization with hierarchy support
CREATE TABLE IF NOT EXISTS item_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,

    -- Basic Information
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT,

    -- Hierarchy
    parent_id UUID,

    -- Defaults
    default_valuation_method valuationmethod,
    default_uom VARCHAR(50),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Extra
    extra_data JSONB,

    -- Audit fields
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT fk_item_groups_parent FOREIGN KEY (parent_id)
        REFERENCES item_groups(id) ON DELETE SET NULL,
    CONSTRAINT uq_item_groups_org_code UNIQUE (organization_id, code)
);

-- Indexes for item_groups
CREATE INDEX IF NOT EXISTS ix_item_groups_organization_id ON item_groups(organization_id);
CREATE INDEX IF NOT EXISTS ix_item_groups_code ON item_groups(code);
CREATE INDEX IF NOT EXISTS ix_item_groups_parent_id ON item_groups(parent_id);
CREATE INDEX IF NOT EXISTS ix_item_groups_is_active ON item_groups(is_active);
CREATE INDEX IF NOT EXISTS ix_item_groups_deleted_at ON item_groups(deleted_at);

-- ===========================================
-- 3. CUSTOMERS
-- ===========================================
-- Customer master data
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,

    -- Basic Information
    customer_name VARCHAR(255) NOT NULL,
    customer_code VARCHAR(50) NOT NULL,

    -- Contact
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Address
    address TEXT,
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),

    -- Tax
    tax_number VARCHAR(50),

    -- Status
    status customerstatus DEFAULT 'active',

    -- Credit
    credit_limit NUMERIC(15,2) DEFAULT 0,
    outstanding_balance NUMERIC(15,2) DEFAULT 0,

    -- Extra
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,

    -- Audit fields
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT uq_customers_org_code UNIQUE (organization_id, customer_code)
);

-- Indexes for customers
CREATE INDEX IF NOT EXISTS ix_customers_organization_id ON customers(organization_id);
CREATE INDEX IF NOT EXISTS ix_customers_customer_code ON customers(customer_code);
CREATE INDEX IF NOT EXISTS ix_customers_customer_name ON customers(customer_name);
CREATE INDEX IF NOT EXISTS ix_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS ix_customers_status ON customers(status);
CREATE INDEX IF NOT EXISTS ix_customers_deleted_at ON customers(deleted_at);

-- ===========================================
-- 4. SUPPLIERS
-- ===========================================
-- Supplier master data
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,

    -- Basic Information
    supplier_name VARCHAR(255) NOT NULL,
    supplier_code VARCHAR(50) NOT NULL,

    -- Contact
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Address
    address TEXT,
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),

    -- Tax
    tax_number VARCHAR(50),

    -- Status
    status supplierstatus DEFAULT 'active',

    -- Payment Terms
    payment_terms INTEGER DEFAULT 30, -- days

    -- Extra
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,

    -- Audit fields
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT uq_suppliers_org_code UNIQUE (organization_id, supplier_code)
);

-- Indexes for suppliers
CREATE INDEX IF NOT EXISTS ix_suppliers_organization_id ON suppliers(organization_id);
CREATE INDEX IF NOT EXISTS ix_suppliers_supplier_code ON suppliers(supplier_code);
CREATE INDEX IF NOT EXISTS ix_suppliers_supplier_name ON suppliers(supplier_name);
CREATE INDEX IF NOT EXISTS ix_suppliers_email ON suppliers(email);
CREATE INDEX IF NOT EXISTS ix_suppliers_status ON suppliers(status);
CREATE INDEX IF NOT EXISTS ix_suppliers_deleted_at ON suppliers(deleted_at);

-- ===========================================
-- 5. CHART_OF_ACCOUNTS
-- ===========================================
-- Chart of accounts with hierarchy
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,

    -- Basic Information
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type accounttype NOT NULL,

    -- Hierarchy
    parent_account_id UUID,
    level INTEGER DEFAULT 1,
    is_group BOOLEAN DEFAULT FALSE,

    -- Balances
    opening_balance NUMERIC(15,2) DEFAULT 0,
    current_balance NUMERIC(15,2) DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Extra
    tags JSONB,
    extra_data JSONB,

    -- Audit fields
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT fk_chart_of_accounts_parent FOREIGN KEY (parent_account_id)
        REFERENCES chart_of_accounts(id) ON DELETE SET NULL,
    CONSTRAINT uq_chart_of_accounts_org_code UNIQUE (organization_id, account_code)
);

-- Indexes for chart_of_accounts
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_organization_id ON chart_of_accounts(organization_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_account_code ON chart_of_accounts(account_code);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_account_type ON chart_of_accounts(account_type);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_parent_account_id ON chart_of_accounts(parent_account_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_is_active ON chart_of_accounts(is_active);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_deleted_at ON chart_of_accounts(deleted_at);

-- ===========================================
-- Verification
-- ===========================================
SELECT 'Foundation tables created successfully!' AS status;

-- Show table counts
SELECT
    schemaname,
    tablename,
    'created' as status
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('warehouses_extended', 'item_groups', 'customers', 'suppliers', 'chart_of_accounts')
ORDER BY tablename;
