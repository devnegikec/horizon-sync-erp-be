-- ===========================================
-- Core Service - Database Tables Creation Script
-- ===========================================
-- This script creates all tables for core-service (Inventory, Lead-to-Order, Billing)
-- Run this in core_db database
-- 
-- IMPORTANT: All enum types use public schema (e.g., public.itemtype)
-- Enum values are UPPERCASE (e.g., 'STOCK', 'ACTIVE', 'DRAFT')
-- 
-- Total Tables: 39 tables
-- 
-- Categories:
--   Inventory: warehouses_extended, item_groups, items, item_prices, item_suppliers,
--              batches, serial_nos, serial_no_history, stock_entries, stock_entry_items,
--              stock_levels, stock_movements, stock_reconciliations, stock_reconciliation_items,
--              stock_settings, put_away_rules, quality_inspection_templates,
--              quality_inspection_parameters, quality_inspections, quality_inspection_readings
--   Lead-to-Order: customers, suppliers, pick_lists, pick_list_items, delivery_notes,
--                  delivery_note_items, purchase_receipts, purchase_receipt_items,
--                  landed_cost_vouchers, landed_cost_purchase_receipts, landed_cost_items,
--                  landed_cost_taxes_and_charges
--   Billing: chart_of_accounts, invoices, invoice_items, payments, payment_allocations,
--            journal_entries, journal_entry_lines

-- ===========================================
-- INVENTORY TABLES
-- ===========================================

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
    warehouse_type public.warehousetype,
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
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT fk_warehouses_extended_parent FOREIGN KEY (parent_warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_warehouses_extended_organization_id ON warehouses_extended(organization_id);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_code ON warehouses_extended(code);
CREATE INDEX IF NOT EXISTS ix_warehouses_extended_parent_warehouse_id ON warehouses_extended(parent_warehouse_id);

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
    default_valuation_method public.valuationmethod,
    default_uom VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    extra_data JSONB,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT fk_item_groups_parent FOREIGN KEY (parent_id) 
        REFERENCES item_groups(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_item_groups_organization_id ON item_groups(organization_id);
CREATE INDEX IF NOT EXISTS ix_item_groups_code ON item_groups(code);
CREATE INDEX IF NOT EXISTS ix_item_groups_parent_id ON item_groups(parent_id);

-- ===========================================
-- 3. ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    item_code VARCHAR(100) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    item_group_id UUID,
    item_type public.itemtype,
    uom VARCHAR(50),
    maintain_stock BOOLEAN,
    valuation_method public.valuationmethod,
    allow_negative_stock BOOLEAN,
    has_variants BOOLEAN,
    variant_of UUID,
    variant_attributes JSONB,
    has_batch_no BOOLEAN,
    has_serial_no BOOLEAN,
    batch_number_series VARCHAR(100),
    serial_number_series VARCHAR(100),
    standard_rate NUMERIC(15,2),
    valuation_rate NUMERIC(15,2),
    enable_auto_reorder BOOLEAN,
    reorder_level INTEGER,
    reorder_qty INTEGER,
    min_order_qty INTEGER,
    max_order_qty INTEGER,
    weight_per_unit NUMERIC(10,3),
    weight_uom VARCHAR(50),
    inspection_required_before_purchase BOOLEAN,
    inspection_required_before_delivery BOOLEAN,
    quality_inspection_template UUID,
    barcode VARCHAR(100),
    status public.itemstatus,
    image_url VARCHAR(500),
    images JSONB,
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT fk_items_item_group FOREIGN KEY (item_group_id) 
        REFERENCES item_groups(id) ON DELETE SET NULL,
    CONSTRAINT fk_items_variant_of FOREIGN KEY (variant_of) 
        REFERENCES items(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_items_organization_id ON items(organization_id);
CREATE INDEX IF NOT EXISTS ix_items_item_code ON items(item_code);
CREATE INDEX IF NOT EXISTS ix_items_item_group_id ON items(item_group_id);
CREATE INDEX IF NOT EXISTS ix_items_variant_of ON items(variant_of);
CREATE INDEX IF NOT EXISTS ix_items_barcode ON items(barcode);

-- ===========================================
-- 4. ITEM_PRICES
-- ===========================================
CREATE TABLE IF NOT EXISTS item_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    item_id UUID NOT NULL,
    price_list_id UUID,
    price NUMERIC(15,2),
    currency VARCHAR(10),
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_upto TIMESTAMP WITH TIME ZONE,
    min_qty INTEGER,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_item_prices_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_item_prices_item_id ON item_prices(item_id);
CREATE INDEX IF NOT EXISTS ix_item_prices_organization_id ON item_prices(organization_id);

-- ===========================================
-- 5. ITEM_SUPPLIERS
-- ===========================================
CREATE TABLE IF NOT EXISTS item_suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    item_id UUID NOT NULL,
    supplier_id UUID NOT NULL,
    supplier_part_no VARCHAR(100),
    lead_time_days INTEGER,
    is_default BOOLEAN,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_item_suppliers_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_item_suppliers_item_id ON item_suppliers(item_id);
CREATE INDEX IF NOT EXISTS ix_item_suppliers_supplier_id ON item_suppliers(supplier_id);
CREATE INDEX IF NOT EXISTS ix_item_suppliers_organization_id ON item_suppliers(organization_id);

-- ===========================================
-- 6. BATCHES
-- ===========================================
CREATE TABLE IF NOT EXISTS batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    batch_no VARCHAR(100) NOT NULL,
    item_id UUID NOT NULL,
    manufacturing_date TIMESTAMP WITH TIME ZONE,
    expiry_date TIMESTAMP WITH TIME ZONE,
    supplier_id UUID,
    supplier_batch_no VARCHAR(100),
    status public.batchstatus,
    reference_type VARCHAR(50),
    reference_id UUID,
    description TEXT,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_batches_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_batches_organization_id ON batches(organization_id);
CREATE INDEX IF NOT EXISTS ix_batches_item_id ON batches(item_id);
CREATE INDEX IF NOT EXISTS ix_batches_batch_no ON batches(batch_no);

-- ===========================================
-- 7. SERIAL_NOS
-- ===========================================
CREATE TABLE IF NOT EXISTS serial_nos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    serial_no VARCHAR(100) NOT NULL,
    item_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    status VARCHAR(50),
    purchase_date TIMESTAMP WITH TIME ZONE,
    purchase_rate NUMERIC(15,2),
    supplier_id UUID,
    delivery_date TIMESTAMP WITH TIME ZONE,
    customer_id UUID,
    warranty_period INTEGER,
    warranty_expiry_date TIMESTAMP WITH TIME ZONE,
    amc_expiry_date TIMESTAMP WITH TIME ZONE,
    batch_no VARCHAR(100),
    description TEXT,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_serial_nos_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_serial_nos_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_serial_nos_organization_id ON serial_nos(organization_id);
CREATE INDEX IF NOT EXISTS ix_serial_nos_item_id ON serial_nos(item_id);
CREATE INDEX IF NOT EXISTS ix_serial_nos_warehouse_id ON serial_nos(warehouse_id);
CREATE INDEX IF NOT EXISTS ix_serial_nos_serial_no ON serial_nos(serial_no);

-- ===========================================
-- 8. SERIAL_NO_HISTORY
-- ===========================================
CREATE TABLE IF NOT EXISTS serial_no_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    serial_no_id UUID NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    transaction_id UUID,
    from_warehouse_id UUID,
    to_warehouse_id UUID,
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_serial_no_history_serial_no FOREIGN KEY (serial_no_id) 
        REFERENCES serial_nos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_serial_no_history_organization_id ON serial_no_history(organization_id);
CREATE INDEX IF NOT EXISTS ix_serial_no_history_serial_no_id ON serial_no_history(serial_no_id);
CREATE INDEX IF NOT EXISTS ix_serial_no_history_transaction_id ON serial_no_history(transaction_id);

-- ===========================================
-- 9. STOCK_ENTRIES
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    stock_entry_no VARCHAR(100) NOT NULL,
    stock_entry_type public.stockentrytype NOT NULL,
    from_warehouse_id UUID,
    to_warehouse_id UUID,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    posting_time VARCHAR(10),
    status public.stockentrystatus,
    reference_type VARCHAR(50),
    reference_id UUID,
    remarks TEXT,
    total_value NUMERIC(15,2),
    expense_account_id UUID,
    cost_center_id UUID,
    is_backflush BOOLEAN,
    bom_id UUID,
    extra_data JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    CONSTRAINT fk_stock_entries_from_warehouse FOREIGN KEY (from_warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE SET NULL,
    CONSTRAINT fk_stock_entries_to_warehouse FOREIGN KEY (to_warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_stock_entries_organization_id ON stock_entries(organization_id);
CREATE INDEX IF NOT EXISTS ix_stock_entries_stock_entry_no ON stock_entries(stock_entry_no);
CREATE INDEX IF NOT EXISTS ix_stock_entries_posting_date ON stock_entries(posting_date);

-- ===========================================
-- 10. STOCK_ENTRY_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_entry_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    stock_entry_id UUID NOT NULL,
    item_id UUID NOT NULL,
    source_warehouse_id UUID,
    target_warehouse_id UUID,
    qty NUMERIC(15,3) NOT NULL,
    uom VARCHAR(50) NOT NULL,
    basic_rate NUMERIC(15,2),
    basic_amount NUMERIC(15,2),
    valuation_rate NUMERIC(15,2),
    batch_no VARCHAR(100),
    serial_nos JSONB,
    quality_inspection_id UUID,
    description TEXT,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_entry_items_stock_entry FOREIGN KEY (stock_entry_id) 
        REFERENCES stock_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_entry_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_entry_items_source_warehouse FOREIGN KEY (source_warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE SET NULL,
    CONSTRAINT fk_stock_entry_items_target_warehouse FOREIGN KEY (target_warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_stock_entry_items_organization_id ON stock_entry_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_stock_entry_items_stock_entry_id ON stock_entry_items(stock_entry_id);
CREATE INDEX IF NOT EXISTS ix_stock_entry_items_item_id ON stock_entry_items(item_id);

-- ===========================================
-- 11. STOCK_LEVELS
-- ===========================================
-- Note: schema.dbml uses product_id, but for core-service we reference items
CREATE TABLE IF NOT EXISTS stock_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    product_id UUID NOT NULL,  -- References items.id
    warehouse_id UUID NOT NULL,
    quantity_on_hand INTEGER,
    quantity_reserved INTEGER,
    quantity_available INTEGER,
    last_counted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_levels_product FOREIGN KEY (product_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_levels_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE,
    CONSTRAINT uq_stock_levels_product_warehouse UNIQUE (product_id, warehouse_id)
);

CREATE INDEX IF NOT EXISTS ix_stock_levels_organization_id ON stock_levels(organization_id);
CREATE INDEX IF NOT EXISTS ix_stock_levels_product_id ON stock_levels(product_id);
CREATE INDEX IF NOT EXISTS ix_stock_levels_warehouse_id ON stock_levels(warehouse_id);

-- ===========================================
-- 12. STOCK_MOVEMENTS
-- ===========================================
-- Note: schema.dbml uses product_id, but for core-service we reference items
CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    product_id UUID NOT NULL,  -- References items.id
    warehouse_id UUID NOT NULL,
    movement_type public.movementtype NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost NUMERIC(15,2),
    reference_type VARCHAR(50),
    reference_id UUID,
    notes TEXT,
    performed_by UUID,
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_movements_product FOREIGN KEY (product_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_movements_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_stock_movements_organization_id ON stock_movements(organization_id);
CREATE INDEX IF NOT EXISTS ix_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS ix_stock_movements_warehouse_id ON stock_movements(warehouse_id);
CREATE INDEX IF NOT EXISTS ix_stock_movements_reference ON stock_movements(reference_type, reference_id);

-- ===========================================
-- 13. STOCK_RECONCILIATIONS
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    reconciliation_no VARCHAR(100) NOT NULL,
    purpose VARCHAR(100),
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    posting_time VARCHAR(10),
    status public.stockentrystatus,
    expense_account_id UUID,
    difference_account_id UUID,
    remarks TEXT,
    extra_data JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

CREATE INDEX IF NOT EXISTS ix_stock_reconciliations_organization_id ON stock_reconciliations(organization_id);
CREATE INDEX IF NOT EXISTS ix_stock_reconciliations_reconciliation_no ON stock_reconciliations(reconciliation_no);

-- ===========================================
-- 14. STOCK_RECONCILIATION_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_reconciliation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    reconciliation_id UUID NOT NULL,
    item_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    current_qty NUMERIC(15,3),
    qty NUMERIC(15,3) NOT NULL,
    qty_difference NUMERIC(15,3),
    current_valuation_rate NUMERIC(15,2),
    valuation_rate NUMERIC(15,2),
    batch_no VARCHAR(100),
    serial_nos JSONB,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_reconciliation_items_reconciliation FOREIGN KEY (reconciliation_id) 
        REFERENCES stock_reconciliations(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_reconciliation_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_stock_reconciliation_items_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_stock_reconciliation_items_organization_id ON stock_reconciliation_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_stock_reconciliation_items_reconciliation_id ON stock_reconciliation_items(reconciliation_id);

-- ===========================================
-- 15. STOCK_SETTINGS
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL UNIQUE,
    item_naming_by VARCHAR(50),
    item_naming_series VARCHAR(100),
    stock_entry_naming_series VARCHAR(100),
    delivery_note_naming_series VARCHAR(100),
    purchase_receipt_naming_series VARCHAR(100),
    default_warehouse_id UUID,
    allow_negative_stock BOOLEAN,
    over_delivery_receipt_allowance NUMERIC(5,2),
    over_billing_allowance NUMERIC(5,2),
    auto_indent BOOLEAN,
    auto_indent_notification JSONB,
    default_valuation_method VARCHAR(50),
    auto_create_serial_no BOOLEAN,
    default_quality_inspection_template_id UUID,
    stock_frozen_upto VARCHAR(50),
    stock_frozen_upto_days INTEGER,
    show_barcode_field BOOLEAN,
    convert_item_desc_to_transaction_desc BOOLEAN,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_settings_default_warehouse FOREIGN KEY (default_warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_stock_settings_organization_id ON stock_settings(organization_id);

-- ===========================================
-- 16. PUT_AWAY_RULES
-- ===========================================
CREATE TABLE IF NOT EXISTS put_away_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    item_id UUID,
    item_group_id UUID,
    warehouse_id UUID NOT NULL,
    capacity INTEGER,
    priority INTEGER,
    min_qty INTEGER,
    max_qty INTEGER,
    is_active BOOLEAN,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_put_away_rules_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_put_away_rules_item_group FOREIGN KEY (item_group_id) 
        REFERENCES item_groups(id) ON DELETE CASCADE,
    CONSTRAINT fk_put_away_rules_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_put_away_rules_organization_id ON put_away_rules(organization_id);
CREATE INDEX IF NOT EXISTS ix_put_away_rules_warehouse_id ON put_away_rules(warehouse_id);

-- ===========================================
-- 17. QUALITY_INSPECTION_TEMPLATES
-- ===========================================
CREATE TABLE IF NOT EXISTS quality_inspection_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    description TEXT,
    item_id UUID,
    item_group_id UUID,
    is_active BOOLEAN,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_quality_inspection_templates_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_quality_inspection_templates_item_group FOREIGN KEY (item_group_id) 
        REFERENCES item_groups(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_quality_inspection_templates_organization_id ON quality_inspection_templates(organization_id);

-- ===========================================
-- 18. QUALITY_INSPECTION_PARAMETERS
-- ===========================================
CREATE TABLE IF NOT EXISTS quality_inspection_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    template_id UUID NOT NULL,
    parameter_name VARCHAR(255) NOT NULL,
    description TEXT,
    reading_type public.readingtype NOT NULL,
    min_value NUMERIC(15,3),
    max_value NUMERIC(15,3),
    acceptance_criteria TEXT,
    non_conformance_action VARCHAR(100),
    sequence INTEGER,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_quality_inspection_parameters_template FOREIGN KEY (template_id) 
        REFERENCES quality_inspection_templates(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_quality_inspection_parameters_organization_id ON quality_inspection_parameters(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_parameters_template_id ON quality_inspection_parameters(template_id);

-- ===========================================
-- 19. QUALITY_INSPECTIONS
-- ===========================================
CREATE TABLE IF NOT EXISTS quality_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    inspection_no VARCHAR(100) NOT NULL,
    item_id UUID NOT NULL,
    item_name VARCHAR(255),
    template_id UUID,
    inspection_type public.inspectiontype NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    batch_no VARCHAR(100),
    serial_no VARCHAR(100),
    sample_size NUMERIC(15,3),
    inspected_by UUID,
    inspection_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status public.inspectionstatus,
    verified BOOLEAN,
    remarks TEXT,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_quality_inspections_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_quality_inspections_template FOREIGN KEY (template_id) 
        REFERENCES quality_inspection_templates(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_quality_inspections_organization_id ON quality_inspections(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspections_inspection_no ON quality_inspections(inspection_no);
CREATE INDEX IF NOT EXISTS ix_quality_inspections_item_id ON quality_inspections(item_id);

-- ===========================================
-- 20. QUALITY_INSPECTION_READINGS
-- ===========================================
CREATE TABLE IF NOT EXISTS quality_inspection_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    inspection_id UUID NOT NULL,
    parameter_id UUID NOT NULL,
    parameter_name VARCHAR(255),
    reading_value VARCHAR(255),
    numeric_value NUMERIC(15,3),
    status VARCHAR(50),
    remarks TEXT,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_quality_inspection_readings_inspection FOREIGN KEY (inspection_id) 
        REFERENCES quality_inspections(id) ON DELETE CASCADE,
    CONSTRAINT fk_quality_inspection_readings_parameter FOREIGN KEY (parameter_id) 
        REFERENCES quality_inspection_parameters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_quality_inspection_readings_organization_id ON quality_inspection_readings(organization_id);
CREATE INDEX IF NOT EXISTS ix_quality_inspection_readings_inspection_id ON quality_inspection_readings(inspection_id);

-- ===========================================
-- LEAD TO ORDER TABLES
-- ===========================================

-- ===========================================
-- 21. CUSTOMERS
-- ===========================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    customer_code VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    tax_number VARCHAR(100),
    status VARCHAR(50),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMP WITH TIME ZONE,
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_customers_organization_id ON customers(organization_id);
CREATE INDEX IF NOT EXISTS ix_customers_customer_code ON customers(customer_code);
CREATE INDEX IF NOT EXISTS ix_customers_email ON customers(email);

-- ===========================================
-- 22. SUPPLIERS
-- ===========================================
CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    supplier_name VARCHAR(255) NOT NULL,
    supplier_code VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    tax_number VARCHAR(100),
    status VARCHAR(50),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMP WITH TIME ZONE,
    tags JSONB,
    custom_fields JSONB,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_suppliers_organization_id ON suppliers(organization_id);
CREATE INDEX IF NOT EXISTS ix_suppliers_supplier_code ON suppliers(supplier_code);
CREATE INDEX IF NOT EXISTS ix_suppliers_email ON suppliers(email);

-- ===========================================
-- 23. PICK_LISTS
-- ===========================================
CREATE TABLE IF NOT EXISTS pick_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    pick_list_no VARCHAR(100) NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    warehouse_id UUID NOT NULL,
    status VARCHAR(50),
    pick_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    assigned_to UUID,
    notes TEXT,
    extra_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pick_lists_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_pick_lists_organization_id ON pick_lists(organization_id);
CREATE INDEX IF NOT EXISTS ix_pick_lists_pick_list_no ON pick_lists(pick_list_no);
CREATE INDEX IF NOT EXISTS ix_pick_lists_warehouse_id ON pick_lists(warehouse_id);

-- ===========================================
-- 24. PICK_LIST_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS pick_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    pick_list_id UUID NOT NULL,
    item_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    qty_to_pick INTEGER NOT NULL,
    qty_picked INTEGER,
    batch_no VARCHAR(100),
    serial_nos JSONB,
    bin_location VARCHAR(100),
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pick_list_items_pick_list FOREIGN KEY (pick_list_id) 
        REFERENCES pick_lists(id) ON DELETE CASCADE,
    CONSTRAINT fk_pick_list_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_pick_list_items_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_pick_list_items_organization_id ON pick_list_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_pick_list_items_pick_list_id ON pick_list_items(pick_list_id);

-- ===========================================
-- 25. DELIVERY_NOTES
-- ===========================================
CREATE TABLE IF NOT EXISTS delivery_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    delivery_note_no VARCHAR(100) NOT NULL,
    customer_id UUID NOT NULL,
    customer_name VARCHAR(255),
    sales_order_id UUID,
    pick_list_id UUID,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    delivery_date TIMESTAMP WITH TIME ZONE,
    warehouse_id UUID NOT NULL,
    status public.documentstatus,
    shipping_address_line1 VARCHAR(255),
    shipping_address_line2 VARCHAR(255),
    shipping_city VARCHAR(100),
    shipping_state VARCHAR(100),
    shipping_postal_code VARCHAR(20),
    shipping_country VARCHAR(100),
    tracking_number VARCHAR(100),
    carrier VARCHAR(100),
    total_qty NUMERIC(15,3),
    total_amount NUMERIC(15,2),
    over_delivery_percentage NUMERIC(5,2),
    sales_invoice_id UUID,
    remarks TEXT,
    extra_data JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_delivery_notes_customer FOREIGN KEY (customer_id) 
        REFERENCES customers(id) ON DELETE CASCADE,
    CONSTRAINT fk_delivery_notes_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE,
    CONSTRAINT fk_delivery_notes_pick_list FOREIGN KEY (pick_list_id) 
        REFERENCES pick_lists(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_delivery_notes_organization_id ON delivery_notes(organization_id);
CREATE INDEX IF NOT EXISTS ix_delivery_notes_delivery_note_no ON delivery_notes(delivery_note_no);
CREATE INDEX IF NOT EXISTS ix_delivery_notes_customer_id ON delivery_notes(customer_id);

-- ===========================================
-- 26. DELIVERY_NOTE_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS delivery_note_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    delivery_note_id UUID NOT NULL,
    item_id UUID NOT NULL,
    item_name VARCHAR(255),
    description TEXT,
    warehouse_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    uom VARCHAR(50) NOT NULL,
    rate NUMERIC(15,2) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    sales_order_item_id UUID,
    batch_no VARCHAR(100),
    serial_nos JSONB,
    quality_inspection_id UUID,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_delivery_note_items_delivery_note FOREIGN KEY (delivery_note_id) 
        REFERENCES delivery_notes(id) ON DELETE CASCADE,
    CONSTRAINT fk_delivery_note_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_delivery_note_items_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_delivery_note_items_organization_id ON delivery_note_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_delivery_note_items_delivery_note_id ON delivery_note_items(delivery_note_id);

-- ===========================================
-- 27. PURCHASE_RECEIPTS
-- ===========================================
CREATE TABLE IF NOT EXISTS purchase_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    purchase_receipt_no VARCHAR(100) NOT NULL,
    supplier_id UUID NOT NULL,
    supplier_name VARCHAR(255),
    purchase_order_id UUID,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    warehouse_id UUID NOT NULL,
    status public.documentstatus,
    supplier_delivery_note VARCHAR(100),
    supplier_invoice_no VARCHAR(100),
    total_qty NUMERIC(15,3),
    total_amount NUMERIC(15,2),
    over_receipt_percentage NUMERIC(5,2),
    apply_putaway_rule BOOLEAN,
    purchase_invoice_id UUID,
    remarks TEXT,
    extra_data JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_purchase_receipts_supplier FOREIGN KEY (supplier_id) 
        REFERENCES suppliers(id) ON DELETE CASCADE,
    CONSTRAINT fk_purchase_receipts_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_purchase_receipts_organization_id ON purchase_receipts(organization_id);
CREATE INDEX IF NOT EXISTS ix_purchase_receipts_purchase_receipt_no ON purchase_receipts(purchase_receipt_no);
CREATE INDEX IF NOT EXISTS ix_purchase_receipts_supplier_id ON purchase_receipts(supplier_id);

-- ===========================================
-- 28. PURCHASE_RECEIPT_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS purchase_receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    purchase_receipt_id UUID NOT NULL,
    item_id UUID NOT NULL,
    item_name VARCHAR(255),
    description TEXT,
    warehouse_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    received_qty NUMERIC(15,3),
    uom VARCHAR(50) NOT NULL,
    rate NUMERIC(15,2) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    purchase_order_item_id UUID,
    batch_no VARCHAR(100),
    serial_nos JSONB,
    quality_inspection_id UUID,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_purchase_receipt_items_purchase_receipt FOREIGN KEY (purchase_receipt_id) 
        REFERENCES purchase_receipts(id) ON DELETE CASCADE,
    CONSTRAINT fk_purchase_receipt_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT fk_purchase_receipt_items_warehouse FOREIGN KEY (warehouse_id) 
        REFERENCES warehouses_extended(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_purchase_receipt_items_organization_id ON purchase_receipt_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_purchase_receipt_items_purchase_receipt_id ON purchase_receipt_items(purchase_receipt_id);

-- ===========================================
-- 29. LANDED_COST_VOUCHERS
-- ===========================================
CREATE TABLE IF NOT EXISTS landed_cost_vouchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    voucher_no VARCHAR(100) NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status public.documentstatus,
    distribute_charges_based_on VARCHAR(50),
    total_landed_cost NUMERIC(15,2),
    remarks TEXT,
    extra_data JSONB,
    submitted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_landed_cost_vouchers_organization_id ON landed_cost_vouchers(organization_id);
CREATE INDEX IF NOT EXISTS ix_landed_cost_vouchers_voucher_no ON landed_cost_vouchers(voucher_no);

-- ===========================================
-- 30. LANDED_COST_PURCHASE_RECEIPTS
-- ===========================================
CREATE TABLE IF NOT EXISTS landed_cost_purchase_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    landed_cost_voucher_id UUID NOT NULL,
    purchase_receipt_id UUID NOT NULL,
    grand_total NUMERIC(15,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_landed_cost_purchase_receipts_voucher FOREIGN KEY (landed_cost_voucher_id) 
        REFERENCES landed_cost_vouchers(id) ON DELETE CASCADE,
    CONSTRAINT fk_landed_cost_purchase_receipts_purchase_receipt FOREIGN KEY (purchase_receipt_id) 
        REFERENCES purchase_receipts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_landed_cost_purchase_receipts_organization_id ON landed_cost_purchase_receipts(organization_id);

-- ===========================================
-- 31. LANDED_COST_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS landed_cost_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    landed_cost_voucher_id UUID NOT NULL,
    purchase_receipt_item_id UUID NOT NULL,
    item_id UUID NOT NULL,
    qty NUMERIC(15,3) NOT NULL,
    rate NUMERIC(15,2) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    applicable_charges NUMERIC(15,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_landed_cost_items_voucher FOREIGN KEY (landed_cost_voucher_id) 
        REFERENCES landed_cost_vouchers(id) ON DELETE CASCADE,
    CONSTRAINT fk_landed_cost_items_purchase_receipt_item FOREIGN KEY (purchase_receipt_item_id) 
        REFERENCES purchase_receipt_items(id) ON DELETE CASCADE,
    CONSTRAINT fk_landed_cost_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_landed_cost_items_organization_id ON landed_cost_items(organization_id);

-- ===========================================
-- 32. LANDED_COST_TAXES_AND_CHARGES
-- ===========================================
CREATE TABLE IF NOT EXISTS landed_cost_taxes_and_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    landed_cost_voucher_id UUID NOT NULL,
    expense_account_id UUID,
    description TEXT,
    amount NUMERIC(15,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_landed_cost_taxes_and_charges_voucher FOREIGN KEY (landed_cost_voucher_id) 
        REFERENCES landed_cost_vouchers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_landed_cost_taxes_and_charges_organization_id ON landed_cost_taxes_and_charges(organization_id);

-- ===========================================
-- BILLING TABLES
-- ===========================================

-- ===========================================
-- 33. CHART_OF_ACCOUNTS
-- ===========================================
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    parent_account_id UUID,
    level INTEGER,
    is_group BOOLEAN,
    opening_balance NUMERIC(15,2),
    current_balance NUMERIC(15,2),
    created_by UUID,
    updated_by UUID,
    tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chart_of_accounts_parent FOREIGN KEY (parent_account_id) 
        REFERENCES chart_of_accounts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_organization_id ON chart_of_accounts(organization_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_account_code ON chart_of_accounts(account_code);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_parent_account_id ON chart_of_accounts(parent_account_id);

-- ===========================================
-- 34. INVOICES
-- ===========================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    invoice_no VARCHAR(100) NOT NULL,
    invoice_date TIMESTAMP WITH TIME ZONE NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE,
    invoice_type VARCHAR(50) NOT NULL,
    status VARCHAR(50),
    customer_id UUID,
    supplier_id UUID,
    total_amount NUMERIC(15,2),
    tax_amount NUMERIC(15,2),
    discount_amount NUMERIC(15,2),
    total_paid NUMERIC(15,2),
    balance_due NUMERIC(15,2),
    currency VARCHAR(10),
    notes TEXT,
    created_by UUID,
    updated_by UUID,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoices_customer FOREIGN KEY (customer_id) 
        REFERENCES customers(id) ON DELETE SET NULL,
    CONSTRAINT fk_invoices_supplier FOREIGN KEY (supplier_id) 
        REFERENCES suppliers(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_invoices_organization_id ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS ix_invoices_invoice_no ON invoices(invoice_no);
CREATE INDEX IF NOT EXISTS ix_invoices_customer_id ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS ix_invoices_supplier_id ON invoices(supplier_id);

-- ===========================================
-- 35. INVOICE_ITEMS
-- ===========================================
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    item_id UUID,
    description VARCHAR(255),
    quantity NUMERIC(15,2) NOT NULL,
    unit_price NUMERIC(15,2) NOT NULL,
    tax_rate NUMERIC(5,2),
    tax_amount NUMERIC(15,2),
    total_amount NUMERIC(15,2) NOT NULL,
    CONSTRAINT fk_invoice_items_invoice FOREIGN KEY (invoice_id) 
        REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_invoice_items_item FOREIGN KEY (item_id) 
        REFERENCES items(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_invoice_items_organization_id ON invoice_items(organization_id);
CREATE INDEX IF NOT EXISTS ix_invoice_items_invoice_id ON invoice_items(invoice_id);

-- ===========================================
-- 36. PAYMENTS
-- ===========================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    payment_no VARCHAR(100) NOT NULL,
    payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
    payment_type VARCHAR(50) NOT NULL,
    status VARCHAR(50),
    customer_id UUID,
    supplier_id UUID,
    amount NUMERIC(15,2) NOT NULL,
    payment_method VARCHAR(50),
    bank_account_id UUID,
    reference_no VARCHAR(100),
    created_by UUID,
    updated_by UUID,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_customer FOREIGN KEY (customer_id) 
        REFERENCES customers(id) ON DELETE SET NULL,
    CONSTRAINT fk_payments_supplier FOREIGN KEY (supplier_id) 
        REFERENCES suppliers(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_payments_organization_id ON payments(organization_id);
CREATE INDEX IF NOT EXISTS ix_payments_payment_no ON payments(payment_no);
CREATE INDEX IF NOT EXISTS ix_payments_customer_id ON payments(customer_id);
CREATE INDEX IF NOT EXISTS ix_payments_supplier_id ON payments(supplier_id);

-- ===========================================
-- 37. PAYMENT_ALLOCATIONS
-- ===========================================
CREATE TABLE IF NOT EXISTS payment_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    allocated_amount NUMERIC(15,2) NOT NULL,
    CONSTRAINT fk_payment_allocations_payment FOREIGN KEY (payment_id) 
        REFERENCES payments(id) ON DELETE CASCADE,
    CONSTRAINT fk_payment_allocations_invoice FOREIGN KEY (invoice_id) 
        REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_payment_allocations_organization_id ON payment_allocations(organization_id);
CREATE INDEX IF NOT EXISTS ix_payment_allocations_payment_id ON payment_allocations(payment_id);
CREATE INDEX IF NOT EXISTS ix_payment_allocations_invoice_id ON payment_allocations(invoice_id);

-- ===========================================
-- 38. JOURNAL_ENTRIES
-- ===========================================
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    entry_no VARCHAR(100) NOT NULL,
    entry_date TIMESTAMP WITH TIME ZONE NOT NULL,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    reference_no VARCHAR(100),
    description TEXT,
    total_debit NUMERIC(15,2),
    total_credit NUMERIC(15,2),
    status VARCHAR(50),
    posted_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_journal_entries_organization_id ON journal_entries(organization_id);
CREATE INDEX IF NOT EXISTS ix_journal_entries_entry_no ON journal_entries(entry_no);
CREATE INDEX IF NOT EXISTS ix_journal_entries_posting_date ON journal_entries(posting_date);

-- ===========================================
-- 39. JOURNAL_ENTRY_LINES
-- ===========================================
CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    journal_entry_id UUID NOT NULL,
    account_id UUID NOT NULL,
    debit_amount NUMERIC(15,2),
    credit_amount NUMERIC(15,2),
    description VARCHAR(255),
    line_number INTEGER,
    CONSTRAINT fk_journal_entry_lines_journal_entry FOREIGN KEY (journal_entry_id) 
        REFERENCES journal_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_journal_entry_lines_account FOREIGN KEY (account_id) 
        REFERENCES chart_of_accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_organization_id ON journal_entry_lines(organization_id);
CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_journal_entry_id ON journal_entry_lines(journal_entry_id);
CREATE INDEX IF NOT EXISTS ix_journal_entry_lines_account_id ON journal_entry_lines(account_id);

-- ===========================================
-- COMMENTS
-- ===========================================
COMMENT ON TABLE warehouses_extended IS 'Extended warehouse information with hierarchy and capacity';
COMMENT ON TABLE item_groups IS 'Item categorization and grouping';
COMMENT ON TABLE items IS 'Core inventory items with stock management';
COMMENT ON TABLE stock_entries IS 'Stock movement entries (receipt, issue, transfer)';
COMMENT ON TABLE stock_levels IS 'Current stock levels per warehouse';
COMMENT ON TABLE customers IS 'Customer master data';
COMMENT ON TABLE suppliers IS 'Supplier master data';
COMMENT ON TABLE delivery_notes IS 'Sales delivery documentation';
COMMENT ON TABLE purchase_receipts IS 'Purchase receipt documentation';
COMMENT ON TABLE invoices IS 'Sales and purchase invoices';
COMMENT ON TABLE payments IS 'Payment transactions';
COMMENT ON TABLE chart_of_accounts IS 'Accounting chart of accounts';
