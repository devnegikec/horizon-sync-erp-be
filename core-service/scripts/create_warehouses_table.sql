-- ===========================================
-- Core Service - Create Warehouses Table Only
-- ===========================================
-- Run this in core_db database
--
-- This script creates only the warehouses_extended table

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
        REFERENCES warehouses_extended(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_organization_id ON warehouses_extended(organization_id);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_code ON warehouses_extended(code);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_parent_warehouse_id ON warehouses_extended(parent_warehouse_id);

-- Add comments
COMMENT ON TABLE warehouses_extended IS 'Extended warehouse information with hierarchy, capacity, and location details';
COMMENT ON COLUMN warehouses_extended.warehouse_type IS 'Type: warehouse, store, virtual, transit';
COMMENT ON COLUMN warehouses_extended.parent_warehouse_id IS 'Parent warehouse for hierarchical structure';
