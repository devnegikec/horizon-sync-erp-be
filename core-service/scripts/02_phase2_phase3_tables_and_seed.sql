-- ===========================================
-- Core Service - Phase 2 & Phase 3 Tables and Seed
-- ===========================================
-- Creates: items (prerequisite), Phase 2 (item_prices, item_suppliers),
--          Phase 3 (batches, serial_nos, serial_no_history, stock_entries,
--          stock_entry_items, stock_levels, stock_movements, stock_reconciliations,
--          stock_reconciliation_items, stock_settings, put_away_rules)
-- Seeds sample data for all of the above.
--
-- Prerequisites: Run 00_setup_complete.sql first (enums + warehouses, item_groups,
--                customers, suppliers, chart_of_accounts must exist).
--
-- Enum types used: itemtype, itemstatus, valuationmethod, stockentrytype,
--   stockentrystatus, movementtype, batchstatus (from 01_create_enums.sql)
--
-- Usage:
--   psql -U horizon_user -d core_db -f 02_phase2_phase3_tables_and_seed.sql
--   OR
--   docker compose exec postgres psql -U horizon_user -d core_db -f /app/scripts/02_phase2_phase3_tables_and_seed.sql

\c core_db;

\echo '============================================='
\echo 'STEP 1: Creating ITEMS (prerequisite for Phase 2 & 3)'
\echo '============================================='

-- ===========================================
-- ITEMS (required by item_prices, item_suppliers, batches, serial_nos, etc.)
-- ===========================================
CREATE TABLE IF NOT EXISTS items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    item_code VARCHAR(100) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    item_group_id UUID,
    item_type itemtype,
    uom VARCHAR(50),
    maintain_stock BOOLEAN,
    valuation_method valuationmethod,
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
    status itemstatus,
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
CREATE INDEX IF NOT EXISTS ix_items_deleted_at ON items(deleted_at);

\echo '============================================='
\echo 'STEP 2: Creating Phase 2 - Item-Related Tables'
\echo '============================================='

-- ===========================================
-- ITEM_PRICES
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
-- ITEM_SUPPLIERS
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

\echo '============================================='
\echo 'STEP 3: Creating Phase 3 - Stock Management Tables'
\echo '============================================='

-- ===========================================
-- BATCHES
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
    status batchstatus,
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
-- SERIAL_NOS
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
-- SERIAL_NO_HISTORY
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
-- STOCK_ENTRIES
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    stock_entry_no VARCHAR(100) NOT NULL,
    stock_entry_type stockentrytype NOT NULL,
    from_warehouse_id UUID,
    to_warehouse_id UUID,
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    posting_time VARCHAR(10),
    status stockentrystatus,
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
-- STOCK_ENTRY_ITEMS
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
-- STOCK_LEVELS (product_id references items.id)
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    product_id UUID NOT NULL,
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
-- STOCK_MOVEMENTS (product_id references items.id)
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    product_id UUID NOT NULL,
    warehouse_id UUID NOT NULL,
    movement_type movementtype NOT NULL,
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
-- STOCK_RECONCILIATIONS
-- ===========================================
CREATE TABLE IF NOT EXISTS stock_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    reconciliation_no VARCHAR(100) NOT NULL,
    purpose VARCHAR(100),
    posting_date TIMESTAMP WITH TIME ZONE NOT NULL,
    posting_time VARCHAR(10),
    status stockentrystatus,
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
-- STOCK_RECONCILIATION_ITEMS
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
-- STOCK_SETTINGS (one per organization)
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
-- PUT_AWAY_RULES
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

\echo 'Phase 2 & Phase 3 tables created successfully!'

\echo ''
\echo '============================================='
\echo 'STEP 4: Seeding Phase 2 & Phase 3 Data'
\echo '============================================='

DO $$
DECLARE
    v_org_id UUID := 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
    v_user_id UUID := 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22';

    v_fg_id UUID;
    v_raw_id UUID;
    v_cons_id UUID;
    v_main_wh_id UUID;
    v_raw_wh_id UUID;
    v_supp1_id UUID;
    v_supp2_id UUID;

    v_item_steel_id UUID;
    v_item_board_id UUID;
    v_item_glue_id UUID;

    v_batch1_id UUID;
    v_serial1_id UUID;
    v_stock_entry1_id UUID;
    v_recon1_id UUID;

BEGIN
    -- Resolve IDs from 00_setup_complete seed (same org)
    SELECT id INTO v_fg_id       FROM item_groups WHERE organization_id = v_org_id AND code = 'FG'       AND (deleted_at IS NULL) LIMIT 1;
    SELECT id INTO v_raw_id      FROM item_groups WHERE organization_id = v_org_id AND code = 'RAW'      AND (deleted_at IS NULL) LIMIT 1;
    SELECT id INTO v_cons_id     FROM item_groups WHERE organization_id = v_org_id AND code = 'CONS'    AND (deleted_at IS NULL) LIMIT 1;
    SELECT id INTO v_main_wh_id  FROM warehouses_extended WHERE organization_id = v_org_id AND code = 'WH-MAIN' AND (deleted_at IS NULL) LIMIT 1;
    SELECT id INTO v_raw_wh_id   FROM warehouses_extended WHERE organization_id = v_org_id AND code = 'WH-RAW'  AND (deleted_at IS NULL) LIMIT 1;
    SELECT id INTO v_supp1_id    FROM suppliers WHERE organization_id = v_org_id AND supplier_code = 'SUPP-001' AND (deleted_at IS NULL) LIMIT 1;
    SELECT id INTO v_supp2_id    FROM suppliers WHERE organization_id = v_org_id AND supplier_code = 'SUPP-002' AND (deleted_at IS NULL) LIMIT 1;

    IF v_fg_id IS NULL OR v_raw_id IS NULL OR v_main_wh_id IS NULL OR v_supp1_id IS NULL THEN
        RAISE EXCEPTION 'Prerequisite data missing. Run 00_setup_complete.sql first. (fg=%, raw=%, main_wh=%, supp1=%)', v_fg_id, v_raw_id, v_main_wh_id, v_supp1_id;
    END IF;

    -- Use RAW warehouse if present, else main
    IF v_raw_wh_id IS NULL THEN v_raw_wh_id := v_main_wh_id; END IF;
    IF v_cons_id IS NULL THEN v_cons_id := v_fg_id; END IF;
    IF v_supp2_id IS NULL THEN v_supp2_id := v_supp1_id; END IF;

    RAISE NOTICE 'Seeding items...';

    INSERT INTO items (organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, status, standard_rate, valuation_rate, has_batch_no, has_serial_no, created_by, updated_by)
    VALUES (v_org_id, 'ITEM-RAW-001', 'Cold Rolled Steel Sheet', 'CR sheet for fabrication', v_raw_id, 'stock', 'Kg', TRUE, 'fifo', 'active', 85.00, 80.00, TRUE, FALSE, v_user_id, v_user_id)
    RETURNING id INTO v_item_steel_id;

    INSERT INTO items (organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, status, standard_rate, valuation_rate, has_batch_no, has_serial_no, created_by, updated_by)
    VALUES (v_org_id, 'ITEM-FG-001', 'Control Board Assembly', 'PCB assembly', v_fg_id, 'stock', 'Nos', TRUE, 'fifo', 'active', 1200.00, 1100.00, FALSE, TRUE, v_user_id, v_user_id)
    RETURNING id INTO v_item_board_id;

    INSERT INTO items (organization_id, item_code, item_name, description, item_group_id, item_type, uom, maintain_stock, valuation_method, status, standard_rate, valuation_rate, has_batch_no, has_serial_no, created_by, updated_by)
    VALUES (v_org_id, 'ITEM-CONS-001', 'Industrial Adhesive', 'Epoxy adhesive 1L', v_cons_id, 'stock', 'L', TRUE, 'moving_average', 'active', 450.00, 420.00, TRUE, FALSE, v_user_id, v_user_id)
    RETURNING id INTO v_item_glue_id;

    RAISE NOTICE 'Seeding item_prices...';

    INSERT INTO item_prices (organization_id, item_id, price, currency, valid_from, min_qty)
    VALUES (v_org_id, v_item_steel_id, 90.00, 'INR', CURRENT_TIMESTAMP - INTERVAL '1 day', 100);
    INSERT INTO item_prices (organization_id, item_id, price, currency, min_qty)
    VALUES (v_org_id, v_item_board_id, 1250.00, 'INR', 1);
    INSERT INTO item_prices (organization_id, item_id, price, currency)
    VALUES (v_org_id, v_item_glue_id, 460.00, 'INR');

    RAISE NOTICE 'Seeding item_suppliers...';

    INSERT INTO item_suppliers (organization_id, item_id, supplier_id, supplier_part_no, lead_time_days, is_default)
    VALUES (v_org_id, v_item_steel_id, v_supp1_id, 'CRS-100', 14, TRUE);
    INSERT INTO item_suppliers (organization_id, item_id, supplier_id, supplier_part_no, lead_time_days, is_default)
    VALUES (v_org_id, v_item_board_id, v_supp2_id, 'CBA-200', 21, TRUE);
    INSERT INTO item_suppliers (organization_id, item_id, supplier_id, supplier_part_no, lead_time_days, is_default)
    VALUES (v_org_id, v_item_glue_id, v_supp2_id, 'ADH-EP1', 7, TRUE);

    RAISE NOTICE 'Seeding batches...';

    INSERT INTO batches (organization_id, batch_no, item_id, manufacturing_date, expiry_date, supplier_id, supplier_batch_no, status)
    VALUES (v_org_id, 'BATCH-STEEL-001', v_item_steel_id, CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '335 days', v_supp1_id, 'SB-2024-001', 'active')
    RETURNING id INTO v_batch1_id;

    INSERT INTO batches (organization_id, batch_no, item_id, manufacturing_date, expiry_date, status)
    VALUES (v_org_id, 'BATCH-ADH-001', v_item_glue_id, CURRENT_DATE - INTERVAL '15 days', CURRENT_DATE + INTERVAL '350 days', 'active');

    RAISE NOTICE 'Seeding serial_nos...';

    INSERT INTO serial_nos (organization_id, serial_no, item_id, warehouse_id, status, purchase_rate)
    VALUES (v_org_id, 'SN-PCB-0001', v_item_board_id, v_main_wh_id, 'Available', 1100.00)
    RETURNING id INTO v_serial1_id;

    INSERT INTO serial_nos (organization_id, serial_no, item_id, warehouse_id, status, purchase_rate)
    VALUES (v_org_id, 'SN-PCB-0002', v_item_board_id, v_main_wh_id, 'Available', 1100.00);

    RAISE NOTICE 'Seeding serial_no_history...';

    INSERT INTO serial_no_history (organization_id, serial_no_id, transaction_type, transaction_id, from_warehouse_id, to_warehouse_id, transaction_date, remarks)
    VALUES (v_org_id, v_serial1_id, 'Inbound', NULL, NULL, v_main_wh_id, CURRENT_TIMESTAMP - INTERVAL '5 days', 'Initial receipt');

    RAISE NOTICE 'Seeding stock_entries and stock_entry_items...';

    INSERT INTO stock_entries (organization_id, stock_entry_no, stock_entry_type, to_warehouse_id, posting_date, status, remarks, created_by, updated_by)
    VALUES (v_org_id, 'SE-2024-001', 'material_receipt', v_main_wh_id, CURRENT_DATE, 'draft', 'Sample material receipt', v_user_id, v_user_id)
    RETURNING id INTO v_stock_entry1_id;

    INSERT INTO stock_entry_items (organization_id, stock_entry_id, item_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate)
    VALUES (v_org_id, v_stock_entry1_id, v_item_steel_id, v_main_wh_id, 500.000, 'Kg', 85.00, 42500.00, 85.00);
    INSERT INTO stock_entry_items (organization_id, stock_entry_id, item_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate)
    VALUES (v_org_id, v_stock_entry1_id, v_item_glue_id, v_main_wh_id, 10.000, 'L', 450.00, 4500.00, 450.00);

    RAISE NOTICE 'Seeding stock_levels...';

    INSERT INTO stock_levels (organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available)
    VALUES (v_org_id, v_item_steel_id, v_main_wh_id, 500, 0, 500);
    INSERT INTO stock_levels (organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available)
    VALUES (v_org_id, v_item_glue_id, v_main_wh_id, 10, 0, 10);
    INSERT INTO stock_levels (organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available)
    VALUES (v_org_id, v_item_board_id, v_main_wh_id, 2, 0, 2);

    RAISE NOTICE 'Seeding stock_movements...';

    INSERT INTO stock_movements (organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, notes, performed_by, performed_at)
    VALUES (v_org_id, v_item_steel_id, v_main_wh_id, 'in', 500, 85.00, 'Initial receipt SE-2024-001', v_user_id, CURRENT_TIMESTAMP - INTERVAL '1 day');
    INSERT INTO stock_movements (organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, notes, performed_by, performed_at)
    VALUES (v_org_id, v_item_glue_id, v_main_wh_id, 'in', 10, 450.00, 'Initial receipt', v_user_id, CURRENT_TIMESTAMP - INTERVAL '1 day');

    RAISE NOTICE 'Seeding stock_reconciliations and stock_reconciliation_items...';

    INSERT INTO stock_reconciliations (organization_id, reconciliation_no, purpose, posting_date, status, remarks, created_by, updated_by)
    VALUES (v_org_id, 'RECON-2024-001', 'Monthly count', CURRENT_DATE, 'draft', 'Sample draft reconciliation', v_user_id, v_user_id)
    RETURNING id INTO v_recon1_id;

    INSERT INTO stock_reconciliation_items (organization_id, reconciliation_id, item_id, warehouse_id, current_qty, qty, qty_difference, current_valuation_rate, valuation_rate)
    VALUES (v_org_id, v_recon1_id, v_item_steel_id, v_main_wh_id, 500.000, 500.000, 0.000, 85.00, 85.00);
    INSERT INTO stock_reconciliation_items (organization_id, reconciliation_id, item_id, warehouse_id, current_qty, qty, qty_difference, current_valuation_rate, valuation_rate)
    VALUES (v_org_id, v_recon1_id, v_item_glue_id, v_main_wh_id, 10.000, 10.000, 0.000, 450.00, 450.00);

    RAISE NOTICE 'Seeding stock_settings...';

    INSERT INTO stock_settings (organization_id, default_warehouse_id, item_naming_by, stock_entry_naming_series, allow_negative_stock, default_valuation_method, created_by, updated_by)
    VALUES (v_org_id, v_main_wh_id, 'Item Code', 'SE-.YYYY.-', FALSE, 'fifo', v_user_id, v_user_id)
    ON CONFLICT (organization_id) DO UPDATE SET
        default_warehouse_id = EXCLUDED.default_warehouse_id,
        item_naming_by = EXCLUDED.item_naming_by,
        stock_entry_naming_series = EXCLUDED.stock_entry_naming_series,
        allow_negative_stock = EXCLUDED.allow_negative_stock,
        default_valuation_method = EXCLUDED.default_valuation_method,
        updated_by = EXCLUDED.updated_by,
        updated_at = CURRENT_TIMESTAMP;

    RAISE NOTICE 'Seeding put_away_rules...';

    INSERT INTO put_away_rules (organization_id, name, item_group_id, warehouse_id, priority, min_qty, max_qty, is_active, created_by, updated_by)
    VALUES (v_org_id, 'Raw materials to WH-RAW', v_raw_id, v_raw_wh_id, 10, 0, 10000, TRUE, v_user_id, v_user_id);

    INSERT INTO put_away_rules (organization_id, name, item_id, warehouse_id, priority, is_active, created_by, updated_by)
    VALUES (v_org_id, 'Control boards to Main', v_item_board_id, v_main_wh_id, 20, TRUE, v_user_id, v_user_id);

    RAISE NOTICE 'Phase 2 & Phase 3 seed data inserted successfully!';

END $$;

\echo ''
\echo '============================================='
\echo 'SETUP COMPLETE - Summary (Phase 2 & Phase 3)'
\echo '============================================='

SELECT 'items' AS table_name, COUNT(*) AS record_count FROM items WHERE deleted_at IS NULL
UNION ALL SELECT 'item_prices', COUNT(*) FROM item_prices
UNION ALL SELECT 'item_suppliers', COUNT(*) FROM item_suppliers
UNION ALL SELECT 'batches', COUNT(*) FROM batches
UNION ALL SELECT 'serial_nos', COUNT(*) FROM serial_nos
UNION ALL SELECT 'serial_no_history', COUNT(*) FROM serial_no_history
UNION ALL SELECT 'stock_entries', COUNT(*) FROM stock_entries
UNION ALL SELECT 'stock_entry_items', COUNT(*) FROM stock_entry_items
UNION ALL SELECT 'stock_levels', COUNT(*) FROM stock_levels
UNION ALL SELECT 'stock_movements', COUNT(*) FROM stock_movements
UNION ALL SELECT 'stock_reconciliations', COUNT(*) FROM stock_reconciliations
UNION ALL SELECT 'stock_reconciliation_items', COUNT(*) FROM stock_reconciliation_items
UNION ALL SELECT 'stock_settings', COUNT(*) FROM stock_settings
UNION ALL SELECT 'put_away_rules', COUNT(*) FROM put_away_rules
ORDER BY table_name;

\echo ''
\echo 'Phase 2 & Phase 3 tables and seed completed successfully!'
