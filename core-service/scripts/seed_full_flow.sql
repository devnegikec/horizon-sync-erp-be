-- =============================================================================
-- FULL SEED SCRIPT: Procure-to-Pay + Order-to-Cash Flows
-- =============================================================================
-- This script seeds realistic, logically linked data across all tables to
-- support two complete business flows:
--
--   FLOW 1 (Sales):  Quotation → Sales Order → Pick List → Delivery Note → Invoice → Payment
--   FLOW 2 (Procurement): Material Request → RFQ → Purchase Order → Purchase Receipt → Invoice → Payment
--
-- EXECUTION ORDER (respects FK constraints):
--   Step 1: Suppliers (need more than 1)
--   Step 2: Item Prices (Standard + Member pricing)
--   Step 3: Item Suppliers (link items to suppliers)
--   Step 4: Stock Settings
--   Step 5: Stock Levels (initial state for 5 items × 2 warehouses)
--   Step 6: Stock Entries + Stock Entry Items (purchase receipts for initial intake)
--   Step 7: Stock Movements (transfer 5 units Main → Retail)
--   Step 8: Stock Reconciliation (1 missing Wireless Mouse)
--   Step 9: FLOW 1 - Quotation → Sales Order → Pick List → Delivery Note → Sales Invoice → Payment
--   Step 10: FLOW 2 - Material Request → RFQ → Purchase Order → Purchase Receipt → Purchase Invoice → Payment
--
-- EXISTING DATA USED:
--   Organization: bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150 (Default Organization)
--   User:         8d509f22-5fe5-4765-9496-3a236cae2af1 (dnegi@gmail.com)
--   Warehouses:   WH-MAIN (cbf290a6-...) and WH-STORE (3c7956f3-...)
--   Customer:     Acme Corporation (60b23cd6-...)
--   Supplier:     Steel India Ltd (f68137ef-...)
-- =============================================================================

BEGIN;

-- =============================================
-- CONSTANTS (reusable references)
-- =============================================
-- Organization
\set org_id   '''bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'''
-- User
\set user_id  '''8d509f22-5fe5-4765-9496-3a236cae2af1'''
-- Warehouses
\set wh_main  '''cbf290a6-91cb-4c93-b9a6-db408bb3c274'''
\set wh_store '''3c7956f3-d57a-4a01-936b-6d6cf98de665'''
-- Customer
\set cust_acme '''60b23cd6-744b-495f-98e7-4730a6c1c1f9'''
-- Existing Supplier
\set sup_steel '''f68137ef-49df-4ea5-8a57-fe22a0f446d2'''

-- 5 Items we'll use (existing in DB)
\set item_laptop    '''f47ac10b-58cc-4372-a567-0e02b2c3d471'''
\set item_mouse     '''f47ac10b-58cc-4372-a567-0e02b2c3d472'''
\set item_keyboard  '''f47ac10b-58cc-4372-a567-0e02b2c3d473'''
\set item_monitor   '''f47ac10b-58cc-4372-a567-0e02b2c3d478'''
\set item_headphone '''f47ac10b-58cc-4372-a567-0e02b2c3d479'''

-- New Supplier IDs
\set sup_techworld  '''a1b2c3d4-1111-4aaa-bbbb-000000000001'''
\set sup_globalelec '''a1b2c3d4-1111-4aaa-bbbb-000000000002'''

-- =============================================================================
-- STEP 1: CREATE 2 MORE SUPPLIERS
-- =============================================================================
-- We already have Steel India Ltd. Adding TechWorld Supplies and Global Electronics.

INSERT INTO suppliers (id, organization_id, supplier_name, supplier_code, email, phone, address_line1, city, state, country, tax_number, status, payment_terms, created_by, created_at, updated_at)
VALUES
  (:sup_techworld, :org_id, 'TechWorld Supplies', 'SUPP-002', 'orders@techworld.com', '+91-9876543210', '42 Electronics Park', 'Bangalore', 'Karnataka', 'India', 'GSTIN29AABCT1234F', 'active', 30, :user_id, '2025-12-01T09:00:00+05:30', '2025-12-01T09:00:00+05:30'),
  (:sup_globalelec, :org_id, 'Global Electronics Co', 'SUPP-003', 'sales@globalelec.com', '+91-8765432109', '88 Industrial Zone', 'Chennai', 'Tamil Nadu', 'India', 'GSTIN33AABCG5678K', 'active', 45, :user_id, '2025-12-05T10:00:00+05:30', '2025-12-05T10:00:00+05:30')
ON CONFLICT DO NOTHING;

-- Verification: SELECT COUNT(*) FROM suppliers WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
-- Expected: 3


-- =============================================================================
-- STEP 2: ITEM PRICES (Standard + Member for each of 5 items)
-- =============================================================================
-- price_list_id is nullable; we use a convention: NULL = Standard, a fixed UUID = Member

\set pl_standard '''00000000-0000-0000-0000-000000000001'''
\set pl_member   '''00000000-0000-0000-0000-000000000002'''

INSERT INTO item_prices (id, organization_id, item_id, price_list_id, price, currency, valid_from, min_qty, created_at, updated_at)
VALUES
  -- Horizon Pro Laptop (standard_rate=1200)
  (gen_random_uuid(), :org_id, :item_laptop,    :pl_standard, 1200.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_laptop,    :pl_member,   1080.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  -- Optical Gaming Mouse (standard_rate=45)
  (gen_random_uuid(), :org_id, :item_mouse,     :pl_standard,   45.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :pl_member,     38.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  -- Mechanical Keyboard (standard_rate=85)
  (gen_random_uuid(), :org_id, :item_keyboard,  :pl_standard,   85.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_keyboard,  :pl_member,     72.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  -- 27-inch 4K Monitor (standard_rate=450)
  (gen_random_uuid(), :org_id, :item_monitor,   :pl_standard,  450.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_monitor,   :pl_member,    399.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  -- Noise Cancelling Headphones (standard_rate=199)
  (gen_random_uuid(), :org_id, :item_headphone, :pl_standard,  199.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :pl_member,    169.00, 'USD', '2025-01-01T00:00:00Z', 1, '2025-12-10T10:00:00Z', '2025-12-10T10:00:00Z');

-- Verification: SELECT i.item_code, ip.price, ip.price_list_id FROM item_prices ip JOIN items i ON i.id = ip.item_id ORDER BY i.item_code, ip.price_list_id;
-- Expected: 10 rows (5 items × 2 price lists)

-- =============================================================================
-- STEP 3: ITEM SUPPLIERS (link each item to 2 suppliers)
-- =============================================================================

INSERT INTO item_suppliers (id, organization_id, item_id, supplier_id, supplier_part_no, lead_time_days, is_default, created_at, updated_at)
VALUES
  -- Laptop: TechWorld (default) + Global Electronics
  (gen_random_uuid(), :org_id, :item_laptop,    :sup_techworld,  'TW-LP-PRO-15',  7, true,  '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_laptop,    :sup_globalelec, 'GE-LAPTOP-001', 10, false, '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  -- Mouse: TechWorld (default) + Steel India
  (gen_random_uuid(), :org_id, :item_mouse,     :sup_techworld,  'TW-MS-OPT-G',   5, true,  '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :sup_steel,      'SI-MOUSE-100',  14, false, '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  -- Keyboard: Global Electronics (default) + TechWorld
  (gen_random_uuid(), :org_id, :item_keyboard,  :sup_globalelec, 'GE-KB-MECH-09',  6, true,  '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_keyboard,  :sup_techworld,  'TW-KB-MK-09',    8, false, '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  -- Monitor: Global Electronics (default) + TechWorld
  (gen_random_uuid(), :org_id, :item_monitor,   :sup_globalelec, 'GE-MON-4K-27',   8, true,  '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_monitor,   :sup_techworld,  'TW-MN-27-4K',   12, false, '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  -- Headphones: TechWorld (default) + Global Electronics
  (gen_random_uuid(), :org_id, :item_headphone, :sup_techworld,  'TW-HP-NC-02',    5, true,  '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :sup_globalelec, 'GE-HDPH-NC-02',  9, false, '2025-12-15T10:00:00Z', '2025-12-15T10:00:00Z');

-- Verification: SELECT i.item_code, s.supplier_code, isup.supplier_part_no, isup.is_default
--   FROM item_suppliers isup JOIN items i ON i.id = isup.item_id JOIN suppliers s ON s.id = isup.supplier_id
--   ORDER BY i.item_code, isup.is_default DESC;
-- Expected: 10 rows (5 items × 2 suppliers each)


-- =============================================================================
-- STEP 4: STOCK SETTINGS
-- =============================================================================

INSERT INTO stock_settings (id, organization_id, allow_negative_stock, default_valuation_method, auto_create_serial_no, show_barcode_field, created_by, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, false, 'fifo', false, true, :user_id, '2025-12-01T00:00:00Z', '2025-12-01T00:00:00Z')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- STEP 5: STOCK LEVELS (current snapshot for 5 items × 2 warehouses)
-- =============================================================================
-- We'll set initial levels. These represent "right now" state.
-- Main Warehouse gets bulk stock; Retail Store gets smaller amounts.
-- We'll DELETE existing stock_levels for these 5 items first to avoid conflicts.

DELETE FROM stock_levels WHERE product_id IN (
  :item_laptop, :item_mouse, :item_keyboard, :item_monitor, :item_headphone
);

INSERT INTO stock_levels (id, organization_id, product_id, warehouse_id, quantity_on_hand, quantity_reserved, quantity_available, last_counted_at, created_at, updated_at)
VALUES
  -- Main Warehouse
  (gen_random_uuid(), :org_id, :item_laptop,    :wh_main, 50, 5, 45, '2026-01-15T10:00:00Z', '2026-01-01T00:00:00Z', '2026-01-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :wh_main, 199, 0, 199, '2026-01-15T10:00:00Z', '2026-01-01T00:00:00Z', '2026-02-10T14:00:00Z'),  -- 200 received, 1 lost in recon
  (gen_random_uuid(), :org_id, :item_keyboard,  :wh_main, 95, 0, 95, '2026-01-15T10:00:00Z', '2026-01-01T00:00:00Z', '2026-01-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_monitor,   :wh_main, 35, 2, 33, '2026-01-15T10:00:00Z', '2026-01-01T00:00:00Z', '2026-01-15T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :wh_main, 75, 0, 75, '2026-01-15T10:00:00Z', '2026-01-01T00:00:00Z', '2026-01-15T10:00:00Z'),
  -- Retail Store (received via transfer)
  (gen_random_uuid(), :org_id, :item_laptop,    :wh_store, 10, 0, 10, '2026-01-20T10:00:00Z', '2026-01-10T00:00:00Z', '2026-01-20T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :wh_store, 25, 0, 25, '2026-01-20T10:00:00Z', '2026-01-10T00:00:00Z', '2026-01-20T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_keyboard,  :wh_store, 15, 0, 15, '2026-01-20T10:00:00Z', '2026-01-10T00:00:00Z', '2026-01-20T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_monitor,   :wh_store,  5, 0,  5, '2026-01-20T10:00:00Z', '2026-01-10T00:00:00Z', '2026-01-20T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :wh_store, 10, 0, 10, '2026-01-20T10:00:00Z', '2026-01-10T00:00:00Z', '2026-01-20T10:00:00Z');

-- Verification: SELECT i.item_code, w.code, sl.quantity_on_hand, sl.quantity_reserved, sl.quantity_available
--   FROM stock_levels sl JOIN items i ON i.id = sl.product_id JOIN warehouses_extended w ON w.id = sl.warehouse_id
--   WHERE sl.product_id IN ('f47ac10b-58cc-4372-a567-0e02b2c3d471','f47ac10b-58cc-4372-a567-0e02b2c3d472','f47ac10b-58cc-4372-a567-0e02b2c3d473','f47ac10b-58cc-4372-a567-0e02b2c3d478','f47ac10b-58cc-4372-a567-0e02b2c3d479')
--   ORDER BY w.code, i.item_code;
-- Expected: 10 rows (5 items × 2 warehouses)


-- =============================================================================
-- STEP 6: STOCK ENTRIES + STOCK ENTRY ITEMS (initial purchase receipts)
-- =============================================================================
-- Two purchase receipts representing initial goods intake into Main Warehouse.

\set ste_receipt1 '''b0000001-0001-4000-a000-000000000001'''
\set ste_receipt2 '''b0000001-0001-4000-a000-000000000002'''
\set ste_transfer '''b0000001-0001-4000-a000-000000000003'''

-- Receipt 1: Laptops, Mice, Keyboards from TechWorld
INSERT INTO stock_entries (id, organization_id, stock_entry_no, stock_entry_type, to_warehouse_id, posting_date, posting_time, status, reference_type, remarks, total_value, created_by, created_at, updated_at)
VALUES
  (:ste_receipt1, :org_id, 'STE-SEED-001', 'material_receipt', :wh_main, '2026-01-02T09:00:00Z', '09:00', 'submitted', 'PURCHASE_RECEIPT', 'Initial stock intake - IT peripherals from TechWorld', 77500.00, :user_id, '2026-01-02T09:00:00Z', '2026-01-02T09:00:00Z');

INSERT INTO stock_entry_items (id, organization_id, stock_entry_id, item_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate, description, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :ste_receipt1, :item_laptop,   :wh_main, 60, 'Unit',  1050.00, 63000.00, 1050.00, 'Horizon Pro Laptop - initial stock', '2026-01-02T09:00:00Z', '2026-01-02T09:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_receipt1, :item_mouse,    :wh_main, 225, 'Piece',  38.00,  8550.00,   38.00, 'Optical Gaming Mouse - initial stock', '2026-01-02T09:00:00Z', '2026-01-02T09:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_receipt1, :item_keyboard, :wh_main, 110, 'Piece',  72.00,  7920.00,   72.00, 'Mechanical Keyboard - initial stock', '2026-01-02T09:00:00Z', '2026-01-02T09:00:00Z');

-- Receipt 2: Monitors, Headphones from Global Electronics
INSERT INTO stock_entries (id, organization_id, stock_entry_no, stock_entry_type, to_warehouse_id, posting_date, posting_time, status, reference_type, remarks, total_value, created_by, created_at, updated_at)
VALUES
  (:ste_receipt2, :org_id, 'STE-SEED-002', 'material_receipt', :wh_main, '2026-01-03T10:00:00Z', '10:00', 'submitted', 'PURCHASE_RECEIPT', 'Initial stock intake - displays & audio from Global Electronics', 33425.00, :user_id, '2026-01-03T10:00:00Z', '2026-01-03T10:00:00Z');

INSERT INTO stock_entry_items (id, organization_id, stock_entry_id, item_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate, description, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :ste_receipt2, :item_monitor,   :wh_main, 40, 'Unit',  399.00, 15960.00, 399.00, '27-inch 4K Monitor - initial stock', '2026-01-03T10:00:00Z', '2026-01-03T10:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_receipt2, :item_headphone, :wh_main, 85, 'Piece', 169.00, 14365.00, 169.00, 'Noise Cancelling Headphones - initial stock', '2026-01-03T10:00:00Z', '2026-01-03T10:00:00Z');

-- Transfer: Move 5 units of each item from Main → Retail Store
INSERT INTO stock_entries (id, organization_id, stock_entry_no, stock_entry_type, from_warehouse_id, to_warehouse_id, posting_date, posting_time, status, remarks, total_value, created_by, created_at, updated_at)
VALUES
  (:ste_transfer, :org_id, 'STE-SEED-003', 'material_transfer', :wh_main, :wh_store, '2026-01-10T14:00:00Z', '14:00', 'submitted', 'Transfer to Retail Store for display and sales', 8870.00, :user_id, '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z');

INSERT INTO stock_entry_items (id, organization_id, stock_entry_id, item_id, source_warehouse_id, target_warehouse_id, qty, uom, basic_rate, basic_amount, valuation_rate, description, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :ste_transfer, :item_laptop,    :wh_main, :wh_store, 5, 'Unit',  1050.00, 5250.00, 1050.00, 'Transfer laptops to retail', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_transfer, :item_mouse,     :wh_main, :wh_store, 5, 'Piece',   38.00,  190.00,   38.00, 'Transfer mice to retail', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_transfer, :item_keyboard,  :wh_main, :wh_store, 5, 'Piece',   72.00,  360.00,   72.00, 'Transfer keyboards to retail', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_transfer, :item_monitor,   :wh_main, :wh_store, 5, 'Unit',   399.00, 1995.00,  399.00, 'Transfer monitors to retail', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z'),
  (gen_random_uuid(), :org_id, :ste_transfer, :item_headphone, :wh_main, :wh_store, 5, 'Piece',  169.00,  845.00,  169.00, 'Transfer headphones to retail', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z');

-- Verification: SELECT se.stock_entry_no, se.stock_entry_type, se.total_value, COUNT(sei.id) as items
--   FROM stock_entries se LEFT JOIN stock_entry_items sei ON sei.stock_entry_id = se.id
--   WHERE se.stock_entry_no LIKE 'STE-SEED-%' GROUP BY se.id ORDER BY se.stock_entry_no;
-- Expected: 3 entries (2 receipts + 1 transfer), 10 line items total


-- =============================================================================
-- STEP 7: STOCK MOVEMENTS (audit trail)
-- =============================================================================
-- Record the transfer of 5 units from Main → Retail for each item.
-- Also record the initial receipt movements.

INSERT INTO stock_movements (id, organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, reference_type, reference_id, notes, performed_by, performed_at, created_at, updated_at)
VALUES
  -- Receipt 1: IN to Main Warehouse
  (gen_random_uuid(), :org_id, :item_laptop,    :wh_main, 'in', 60,  1050.00, 'STOCK_ENTRY', :ste_receipt1, 'Initial receipt - Laptops', :user_id, '2026-01-02T09:00:00Z', '2026-01-02T09:00:00Z', '2026-01-02T09:00:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :wh_main, 'in', 225,   38.00, 'STOCK_ENTRY', :ste_receipt1, 'Initial receipt - Mice', :user_id, '2026-01-02T09:05:00Z', '2026-01-02T09:05:00Z', '2026-01-02T09:05:00Z'),
  (gen_random_uuid(), :org_id, :item_keyboard,  :wh_main, 'in', 110,   72.00, 'STOCK_ENTRY', :ste_receipt1, 'Initial receipt - Keyboards', :user_id, '2026-01-02T09:10:00Z', '2026-01-02T09:10:00Z', '2026-01-02T09:10:00Z'),
  -- Receipt 2: IN to Main Warehouse
  (gen_random_uuid(), :org_id, :item_monitor,   :wh_main, 'in', 40,   399.00, 'STOCK_ENTRY', :ste_receipt2, 'Initial receipt - Monitors', :user_id, '2026-01-03T10:00:00Z', '2026-01-03T10:00:00Z', '2026-01-03T10:00:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :wh_main, 'in', 85,   169.00, 'STOCK_ENTRY', :ste_receipt2, 'Initial receipt - Headphones', :user_id, '2026-01-03T10:05:00Z', '2026-01-03T10:05:00Z', '2026-01-03T10:05:00Z'),
  -- Transfer: OUT from Main, IN to Retail (5 units each)
  (gen_random_uuid(), :org_id, :item_laptop,    :wh_main,  'out', 5, 1050.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer to Retail Store', :user_id, '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z'),
  (gen_random_uuid(), :org_id, :item_laptop,    :wh_store, 'in',  5, 1050.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer from Main Warehouse', :user_id, '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z', '2026-01-10T14:00:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :wh_main,  'out', 5,   38.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer to Retail Store', :user_id, '2026-01-10T14:05:00Z', '2026-01-10T14:05:00Z', '2026-01-10T14:05:00Z'),
  (gen_random_uuid(), :org_id, :item_mouse,     :wh_store, 'in',  5,   38.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer from Main Warehouse', :user_id, '2026-01-10T14:05:00Z', '2026-01-10T14:05:00Z', '2026-01-10T14:05:00Z'),
  (gen_random_uuid(), :org_id, :item_keyboard,  :wh_main,  'out', 5,   72.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer to Retail Store', :user_id, '2026-01-10T14:10:00Z', '2026-01-10T14:10:00Z', '2026-01-10T14:10:00Z'),
  (gen_random_uuid(), :org_id, :item_keyboard,  :wh_store, 'in',  5,   72.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer from Main Warehouse', :user_id, '2026-01-10T14:10:00Z', '2026-01-10T14:10:00Z', '2026-01-10T14:10:00Z'),
  (gen_random_uuid(), :org_id, :item_monitor,   :wh_main,  'out', 5,  399.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer to Retail Store', :user_id, '2026-01-10T14:15:00Z', '2026-01-10T14:15:00Z', '2026-01-10T14:15:00Z'),
  (gen_random_uuid(), :org_id, :item_monitor,   :wh_store, 'in',  5,  399.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer from Main Warehouse', :user_id, '2026-01-10T14:15:00Z', '2026-01-10T14:15:00Z', '2026-01-10T14:15:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :wh_main,  'out', 5,  169.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer to Retail Store', :user_id, '2026-01-10T14:20:00Z', '2026-01-10T14:20:00Z', '2026-01-10T14:20:00Z'),
  (gen_random_uuid(), :org_id, :item_headphone, :wh_store, 'in',  5,  169.00, 'STOCK_ENTRY', :ste_transfer, 'Transfer from Main Warehouse', :user_id, '2026-01-10T14:20:00Z', '2026-01-10T14:20:00Z', '2026-01-10T14:20:00Z');

-- Verification: SELECT i.item_code, w.code, sm.movement_type, sm.quantity, sm.notes
--   FROM stock_movements sm JOIN items i ON i.id = sm.product_id JOIN warehouses_extended w ON w.id = sm.warehouse_id
--   WHERE sm.reference_id IN ('b0000001-0001-4000-a000-000000000001','b0000001-0001-4000-a000-000000000002','b0000001-0001-4000-a000-000000000003')
--   ORDER BY sm.performed_at;
-- Expected: 15 rows (5 receipts + 10 transfer movements)


-- =============================================================================
-- STEP 8: STOCK RECONCILIATION (physical count found 1 missing mouse)
-- =============================================================================
-- During a physical count on Feb 10, we found 199 mice in Main Warehouse
-- instead of the expected 200 (225 received - 25 transferred to retail = 200 expected).
-- The stock_level was already updated in Step 5 to reflect 199.

\set recon_seed '''c0000001-0001-4000-a000-000000000001'''

INSERT INTO stock_reconciliations (id, organization_id, reconciliation_no, purpose, posting_date, posting_time, status, remarks, created_by, created_at, updated_at)
VALUES
  (:recon_seed, :org_id, 'RECON-SEED-001', 'Monthly Physical Count', '2026-02-10T14:00:00Z', '14:00', 'submitted', 'February monthly physical stock count. Found 1 unit discrepancy for Optical Gaming Mouse in Main Warehouse. Likely damaged during handling.', :user_id, '2026-02-10T14:00:00Z', '2026-02-10T14:30:00Z');

INSERT INTO stock_reconciliation_items (id, organization_id, reconciliation_id, item_id, warehouse_id, current_qty, qty, qty_difference, current_valuation_rate, valuation_rate, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :recon_seed, :item_mouse, :wh_main, 200, 199, -1, 38.00, 38.00, '2026-02-10T14:00:00Z', '2026-02-10T14:00:00Z');

-- Record the adjustment movement
INSERT INTO stock_movements (id, organization_id, product_id, warehouse_id, movement_type, quantity, unit_cost, reference_type, reference_id, notes, performed_by, performed_at, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :item_mouse, :wh_main, 'adjustment', -1, 38.00, 'STOCK_RECONCILIATION', :recon_seed, 'Physical count adjustment: 1 unit missing (damaged during handling)', :user_id, '2026-02-10T14:30:00Z', '2026-02-10T14:30:00Z', '2026-02-10T14:30:00Z');

-- Verification: SELECT sr.reconciliation_no, sri.current_qty, sri.qty, sri.qty_difference, i.item_code
--   FROM stock_reconciliations sr JOIN stock_reconciliation_items sri ON sri.reconciliation_id = sr.id
--   JOIN items i ON i.id = sri.item_id WHERE sr.reconciliation_no = 'RECON-SEED-001';
-- Expected: 1 row, qty_difference = -1 for HZN-MO-05


-- =============================================================================
-- STEP 9: FLOW 1 - SALES (Order-to-Cash)
-- Quotation → Sales Order → Pick List → Delivery Note → Sales Invoice → Payment
-- =============================================================================
-- Scenario: Acme Corporation wants 3 Laptops, 10 Mice, and 5 Keyboards.

\set quot_seed   '''d0000001-0001-4000-a000-000000000001'''
\set so_seed     '''d0000001-0001-4000-a000-000000000002'''
\set pl_seed     '''d0000001-0001-4000-a000-000000000003'''
\set dn_seed     '''d0000001-0001-4000-a000-000000000004'''
\set inv_sales   '''d0000001-0001-4000-a000-000000000005'''
\set pay_sales   '''d0000001-0001-4000-a000-000000000006'''

-- 9a. QUOTATION (status: accepted)
INSERT INTO quotations (id, organization_id, quotation_no, customer_id, quotation_date, valid_until, status, grand_total, currency, remarks, converted_to_sales_order, submitted_at, created_by, created_at, updated_at)
VALUES
  (:quot_seed, :org_id, 'QTN-SEED-001', :cust_acme, '2026-01-20T10:00:00Z', '2026-02-20T10:00:00Z', 'accepted', 4450.00, 'USD', 'IT equipment for Acme Corp new office setup', true, '2026-01-20T10:30:00Z', :user_id, '2026-01-20T10:00:00Z', '2026-01-22T09:00:00Z');

INSERT INTO quotation_items (id, organization_id, quotation_id, item_id, qty, uom, rate, amount, sort_order, tax_rate, tax_amount, total_amount, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :quot_seed, :item_laptop,   3,  'Unit',  1200.00, 3600.00, 1, 0, 0, 3600.00, '2026-01-20T10:00:00Z', '2026-01-20T10:00:00Z'),
  (gen_random_uuid(), :org_id, :quot_seed, :item_mouse,    10, 'Piece',   45.00,  450.00, 2, 0, 0,  450.00, '2026-01-20T10:00:00Z', '2026-01-20T10:00:00Z'),
  (gen_random_uuid(), :org_id, :quot_seed, :item_keyboard,  5, 'Piece',   85.00,  425.00, 3, 0, 0,  425.00, '2026-01-20T10:00:00Z', '2026-01-20T10:00:00Z');

-- 9b. SALES ORDER (status: delivered, converted from quotation)
INSERT INTO sales_orders (id, organization_id, sales_order_no, customer_id, order_date, delivery_date, status, grand_total, currency, reference_type, reference_id, remarks, submitted_at, created_by, created_at, updated_at)
VALUES
  (:so_seed, :org_id, 'SO-SEED-001', :cust_acme, '2026-01-22T09:00:00Z', '2026-01-30T09:00:00Z', 'delivered', 4450.00, 'USD', 'Quotation', :quot_seed, 'Converted from QTN-SEED-001', '2026-01-22T09:30:00Z', :user_id, '2026-01-22T09:00:00Z', '2026-01-30T16:00:00Z');

INSERT INTO sales_order_items (id, organization_id, sales_order_id, item_id, qty, uom, rate, amount, billed_qty, delivered_qty, sort_order, tax_rate, tax_amount, total_amount, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :so_seed, :item_laptop,    3, 'Unit',  1200.00, 3600.00,  3,  3, 1, 0, 0, 3600.00, '2026-01-22T09:00:00Z', '2026-01-30T16:00:00Z'),
  (gen_random_uuid(), :org_id, :so_seed, :item_mouse,    10, 'Piece',   45.00,  450.00, 10, 10, 2, 0, 0,  450.00, '2026-01-22T09:00:00Z', '2026-01-30T16:00:00Z'),
  (gen_random_uuid(), :org_id, :so_seed, :item_keyboard,  5, 'Piece',   85.00,  425.00,  5,  5, 3, 0, 0,  425.00, '2026-01-22T09:00:00Z', '2026-01-30T16:00:00Z');

-- 9c. PICK LIST (status: completed, from Main Warehouse)
INSERT INTO pick_lists (id, organization_id, pick_list_no, warehouse_id, status, pick_date, reference_type, reference_id, remarks, completed_at, created_by, created_at, updated_at)
VALUES
  (:pl_seed, :org_id, 'PL-SEED-001', :wh_main, 'completed', '2026-01-28T08:00:00Z', 'SALES_ORDER', :so_seed, 'Pick for SO-SEED-001 (Acme Corp)', '2026-01-28T10:30:00Z', :user_id, '2026-01-28T08:00:00Z', '2026-01-28T10:30:00Z');

INSERT INTO pick_list_items (id, organization_id, pick_list_id, item_id, warehouse_id, qty, picked_qty, uom, sort_order, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :pl_seed, :item_laptop,    :wh_main,  3,  3, 'Unit',  1, '2026-01-28T08:00:00Z', '2026-01-28T10:30:00Z'),
  (gen_random_uuid(), :org_id, :pl_seed, :item_mouse,     :wh_main, 10, 10, 'Piece', 2, '2026-01-28T08:00:00Z', '2026-01-28T10:30:00Z'),
  (gen_random_uuid(), :org_id, :pl_seed, :item_keyboard,  :wh_main,  5,  5, 'Piece', 3, '2026-01-28T08:00:00Z', '2026-01-28T10:30:00Z');

-- 9d. DELIVERY NOTE (status: submitted, from Main Warehouse)
INSERT INTO delivery_notes (id, organization_id, delivery_note_no, customer_id, delivery_date, status, warehouse_id, pick_list_id, reference_type, reference_id, remarks, submitted_at, created_by, created_at, updated_at)
VALUES
  (:dn_seed, :org_id, 'DN-SEED-001', :cust_acme, '2026-01-30T14:00:00Z', 'submitted', :wh_main, :pl_seed, 'SALES_ORDER', :so_seed, 'Delivery for SO-SEED-001', '2026-01-30T14:30:00Z', :user_id, '2026-01-30T14:00:00Z', '2026-01-30T14:30:00Z');

INSERT INTO delivery_note_items (id, organization_id, delivery_note_id, item_id, qty, uom, rate, amount, warehouse_id, sort_order, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :dn_seed, :item_laptop,    3, 'Unit',  1200.00, 3600.00, :wh_main, 1, '2026-01-30T14:00:00Z', '2026-01-30T14:00:00Z'),
  (gen_random_uuid(), :org_id, :dn_seed, :item_mouse,    10, 'Piece',   45.00,  450.00, :wh_main, 2, '2026-01-30T14:00:00Z', '2026-01-30T14:00:00Z'),
  (gen_random_uuid(), :org_id, :dn_seed, :item_keyboard,  5, 'Piece',   85.00,  425.00, :wh_main, 3, '2026-01-30T14:00:00Z', '2026-01-30T14:00:00Z');

-- 9e. SALES INVOICE (status: paid)
INSERT INTO invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, reference_type, reference_id, remarks, submitted_at, created_by, created_at, updated_at)
VALUES
  (:inv_sales, :org_id, 'INV-SEED-001', 'sales', :cust_acme, 'CUSTOMER', '2026-01-30T16:00:00Z', '2026-03-01T16:00:00Z', 'paid', 4450.00, 0.00, 'USD', 'SALES_ORDER', :so_seed, 'Invoice for SO-SEED-001 (Acme Corp)', '2026-01-30T16:30:00Z', :user_id, '2026-01-30T16:00:00Z', '2026-02-15T10:00:00Z');

INSERT INTO invoice_items (id, organization_id, invoice_id, item_id, item_code, item_name, qty, uom, rate, amount, sort_order, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :inv_sales, :item_laptop,   'HZN-LP-01', 'Horizon Pro Laptop',       3, 'Unit',  1200.00, 3600.00, 1, '2026-01-30T16:00:00Z', '2026-01-30T16:00:00Z'),
  (gen_random_uuid(), :org_id, :inv_sales, :item_mouse,    'HZN-MO-05', 'Optical Gaming Mouse',    10, 'Piece',   45.00,  450.00, 2, '2026-01-30T16:00:00Z', '2026-01-30T16:00:00Z'),
  (gen_random_uuid(), :org_id, :inv_sales, :item_keyboard, 'HZN-KB-09', 'Mechanical Keyboard',      5, 'Piece',   85.00,  425.00, 3, '2026-01-30T16:00:00Z', '2026-01-30T16:00:00Z');

-- 9f. PAYMENT RECEIVED (full payment)
INSERT INTO payments (id, organization_id, payment_no, payment_type, party_id, party_type, posting_date, amount, status, payment_method, reference_no, remarks, created_by, created_at, updated_at)
VALUES
  (:pay_sales, :org_id, 'PAY-SEED-001', 'receive', :cust_acme, 'CUSTOMER', '2026-02-15T10:00:00Z', 4450.00, 'completed', 'bank_transfer', 'NEFT-20260215-ACME', 'Full payment for INV-SEED-001', :user_id, '2026-02-15T10:00:00Z', '2026-02-15T10:00:00Z');

INSERT INTO payment_allocations (id, organization_id, payment_id, invoice_id, allocated_amount, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :pay_sales, :inv_sales, 4450.00, '2026-02-15T10:00:00Z', '2026-02-15T10:00:00Z');

-- Verification (Flow 1):
-- SELECT 'Quotation' as doc, quotation_no as doc_no, status, grand_total FROM quotations WHERE id = 'd0000001-0001-4000-a000-000000000001'
-- UNION ALL SELECT 'Sales Order', sales_order_no, status, grand_total FROM sales_orders WHERE id = 'd0000001-0001-4000-a000-000000000002'
-- UNION ALL SELECT 'Pick List', pick_list_no, status, 0 FROM pick_lists WHERE id = 'd0000001-0001-4000-a000-000000000003'
-- UNION ALL SELECT 'Delivery Note', delivery_note_no, status, 0 FROM delivery_notes WHERE id = 'd0000001-0001-4000-a000-000000000004'
-- UNION ALL SELECT 'Invoice', invoice_no, status, grand_total FROM invoices WHERE id = 'd0000001-0001-4000-a000-000000000005'
-- UNION ALL SELECT 'Payment', payment_no, status, amount FROM payments WHERE id = 'd0000001-0001-4000-a000-000000000006';


-- =============================================================================
-- STEP 10: FLOW 2 - PROCUREMENT (Procure-to-Pay)
-- Material Request → RFQ → Purchase Order → Purchase Receipt → Purchase Invoice → Payment
-- =============================================================================
-- Scenario: We need to restock 20 Monitors and 30 Headphones.
-- The material request is created, converted to RFQ sent to 2 suppliers,
-- quotes are received, best supplier is selected, PO is created, goods received,
-- invoice raised, and payment made.

\set mr_seed     '''e0000001-0001-4000-a000-000000000001'''
\set mr_line1    '''e0000001-0001-4000-a000-000000000011'''
\set mr_line2    '''e0000001-0001-4000-a000-000000000012'''
\set rfq_seed    '''e0000001-0001-4000-a000-000000000002'''
\set rfq_line1   '''e0000001-0001-4000-a000-000000000021'''
\set rfq_line2   '''e0000001-0001-4000-a000-000000000022'''
\set rfq_sup1    '''e0000001-0001-4000-a000-000000000031'''
\set rfq_sup2    '''e0000001-0001-4000-a000-000000000032'''
\set quote1a     '''e0000001-0001-4000-a000-000000000041'''
\set quote1b     '''e0000001-0001-4000-a000-000000000042'''
\set quote2a     '''e0000001-0001-4000-a000-000000000043'''
\set quote2b     '''e0000001-0001-4000-a000-000000000044'''
\set po_seed     '''e0000001-0001-4000-a000-000000000003'''
\set pr_seed     '''e0000001-0001-4000-a000-000000000004'''
\set inv_purch   '''e0000001-0001-4000-a000-000000000005'''
\set pay_purch   '''e0000001-0001-4000-a000-000000000006'''

-- 10a. MATERIAL REQUEST (status: fully_quoted)
INSERT INTO material_requests (id, organization_id, request_no, type, priority, status, target_warehouse_id, requested_by, department, notes, created_by, created_at, updated_at)
VALUES
  (:mr_seed, :org_id, 'MR-SEED-001', 'purchase', 'high', 'fully_quoted', :wh_main, :user_id, 'IT Department', 'Restock monitors and headphones for Q1 2026 demand. Current stock running low.', :user_id, '2026-01-25T09:00:00Z', '2026-02-01T11:00:00Z');

INSERT INTO material_request_lines (id, organization_id, material_request_id, item_id, quantity, uom, required_date, description, estimated_unit_cost, requested_for, requested_for_department, created_at, updated_at)
VALUES
  (:mr_line1, :org_id, :mr_seed, :item_monitor,   20.0000, 'Unit',  '2026-02-15', '27-inch 4K Monitor for new hires', 420.00, 'IT Procurement', 'IT Department', '2026-01-25T09:00:00Z', '2026-01-25T09:00:00Z'),
  (:mr_line2, :org_id, :mr_seed, :item_headphone, 30.0000, 'Piece', '2026-02-15', 'Noise Cancelling Headphones for remote workers', 175.00, 'IT Procurement', 'IT Department', '2026-01-25T09:00:00Z', '2026-01-25T09:00:00Z');

-- 10b. RFQ (status: closed, sent to TechWorld + Global Electronics)
INSERT INTO rfqs (id, organization_id, material_request_id, reference_type, reference_id, status, closing_date, created_by, created_at, updated_at)
VALUES
  (:rfq_seed, :org_id, :mr_seed, 'MATERIAL_REQUEST', :mr_seed, 'closed', '2026-02-05', :user_id, '2026-01-26T10:00:00Z', '2026-02-05T17:00:00Z');

INSERT INTO rfq_lines (id, organization_id, rfq_id, item_id, quantity, required_date, description, created_at, updated_at)
VALUES
  (:rfq_line1, :org_id, :rfq_seed, :item_monitor,   20.0000, '2026-02-15', '27-inch 4K Monitor', '2026-01-26T10:00:00Z', '2026-01-26T10:00:00Z'),
  (:rfq_line2, :org_id, :rfq_seed, :item_headphone, 30.0000, '2026-02-15', 'Noise Cancelling Headphones', '2026-01-26T10:00:00Z', '2026-01-26T10:00:00Z');

INSERT INTO rfq_suppliers (id, organization_id, rfq_id, supplier_id, created_at)
VALUES
  (:rfq_sup1, :org_id, :rfq_seed, :sup_techworld,  '2026-01-26T10:00:00Z'),
  (:rfq_sup2, :org_id, :rfq_seed, :sup_globalelec, '2026-01-26T10:00:00Z');

-- 10c. SUPPLIER QUOTES (both suppliers respond)
-- TechWorld quotes: Monitor $410, Headphones $165 (cheaper overall)
-- Global Electronics quotes: Monitor $395, Headphones $180
INSERT INTO supplier_quotes (id, organization_id, rfq_line_id, supplier_id, quoted_price, quoted_delivery_date, supplier_notes, created_at, updated_at)
VALUES
  -- TechWorld quotes
  (:quote1a, :org_id, :rfq_line1, :sup_techworld,  410.00, '2026-02-12', 'Can deliver in 7 business days. Bulk discount applied.', '2026-01-30T11:00:00Z', '2026-01-30T11:00:00Z'),
  (:quote1b, :org_id, :rfq_line2, :sup_techworld,  165.00, '2026-02-10', 'In stock, ready to ship. Latest model with ANC 3.0.', '2026-01-30T11:00:00Z', '2026-01-30T11:00:00Z'),
  -- Global Electronics quotes
  (:quote2a, :org_id, :rfq_line1, :sup_globalelec, 395.00, '2026-02-18', 'Best price for 4K monitors. 14-day lead time.', '2026-02-01T09:00:00Z', '2026-02-01T09:00:00Z'),
  (:quote2b, :org_id, :rfq_line2, :sup_globalelec, 180.00, '2026-02-20', 'Premium model. 3-year warranty included.', '2026-02-01T09:00:00Z', '2026-02-01T09:00:00Z');

-- Decision: TechWorld wins (total: 20×410 + 30×165 = 8200+4950 = $13,150)
-- vs Global (total: 20×395 + 30×180 = 7900+5400 = $13,300)
-- TechWorld is cheaper overall AND delivers faster.

-- 10d. PURCHASE ORDER (status: fully_received, from TechWorld)
INSERT INTO purchase_orders (id, organization_id, rfq_id, reference_type, reference_id, party_type, party_id, status, subtotal, tax_amount, tax_rate, discount_amount, grand_total, created_by, created_at, updated_at)
VALUES
  (:po_seed, :org_id, :rfq_seed, 'RFQ', :rfq_seed, 'SUPPLIER', :sup_techworld, 'fully_received', 13150.00, 0.00, NULL, 0.00, 13150.00, :user_id, '2026-02-05T14:00:00Z', '2026-02-14T16:00:00Z');

INSERT INTO purchase_order_lines (id, organization_id, purchase_order_id, item_id, quantity, unit_price, line_total, received_quantity, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :po_seed, :item_monitor,   20.0000, 410.00, 8200.00, 20.0000, '2026-02-05T14:00:00Z', '2026-02-14T16:00:00Z'),
  (gen_random_uuid(), :org_id, :po_seed, :item_headphone, 30.0000, 165.00, 4950.00, 30.0000, '2026-02-05T14:00:00Z', '2026-02-14T16:00:00Z');

-- 10e. PURCHASE RECEIPT (status: submitted, goods received at Main Warehouse)
INSERT INTO purchase_receipts (id, organization_id, purchase_receipt_no, supplier_id, receipt_date, status, warehouse_id, reference_type, reference_id, remarks, submitted_at, created_by, created_at, updated_at)
VALUES
  (:pr_seed, :org_id, 'PR-SEED-001', :sup_techworld, '2026-02-14T10:00:00Z', 'submitted', :wh_main, 'PURCHASE_ORDER', :po_seed, 'Received 20 monitors and 30 headphones from TechWorld. All items inspected and in good condition.', '2026-02-14T11:00:00Z', :user_id, '2026-02-14T10:00:00Z', '2026-02-14T11:00:00Z');

INSERT INTO purchase_receipt_items (id, organization_id, purchase_receipt_id, item_id, qty, uom, rate, amount, warehouse_id, sort_order, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :pr_seed, :item_monitor,   20, 'Unit',  410.00, 8200.00, :wh_main, 1, '2026-02-14T10:00:00Z', '2026-02-14T10:00:00Z'),
  (gen_random_uuid(), :org_id, :pr_seed, :item_headphone, 30, 'Piece', 165.00, 4950.00, :wh_main, 2, '2026-02-14T10:00:00Z', '2026-02-14T10:00:00Z');

-- 10f. PURCHASE INVOICE (status: paid)
INSERT INTO invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, reference_type, reference_id, remarks, submitted_at, created_by, created_at, updated_at)
VALUES
  (:inv_purch, :org_id, 'INV-SEED-002', 'purchase', :sup_techworld, 'SUPPLIER', '2026-02-14T16:00:00Z', '2026-03-16T16:00:00Z', 'paid', 13150.00, 0.00, 'USD', 'PURCHASE_ORDER', :po_seed, 'Purchase invoice from TechWorld for PO from RFQ', '2026-02-14T16:30:00Z', :user_id, '2026-02-14T16:00:00Z', '2026-02-20T10:00:00Z');

INSERT INTO invoice_items (id, organization_id, invoice_id, item_id, item_code, item_name, qty, uom, rate, amount, sort_order, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :inv_purch, :item_monitor,   'HZN-MN-27', '27-inch 4K Monitor',            20, 'Unit',  410.00, 8200.00, 1, '2026-02-14T16:00:00Z', '2026-02-14T16:00:00Z'),
  (gen_random_uuid(), :org_id, :inv_purch, :item_headphone, 'HZN-HD-02', 'Noise Cancelling Headphones',   30, 'Piece', 165.00, 4950.00, 2, '2026-02-14T16:00:00Z', '2026-02-14T16:00:00Z');

-- 10g. PAYMENT MADE (full payment to supplier)
INSERT INTO payments (id, organization_id, payment_no, payment_type, party_id, party_type, posting_date, amount, status, payment_method, reference_no, remarks, created_by, created_at, updated_at)
VALUES
  (:pay_purch, :org_id, 'PAY-SEED-002', 'pay', :sup_techworld, 'SUPPLIER', '2026-02-20T10:00:00Z', 13150.00, 'completed', 'bank_transfer', 'NEFT-20260220-TECHWORLD', 'Full payment for INV-SEED-002 (TechWorld Supplies)', :user_id, '2026-02-20T10:00:00Z', '2026-02-20T10:00:00Z');

INSERT INTO payment_allocations (id, organization_id, payment_id, invoice_id, allocated_amount, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, :pay_purch, :inv_purch, 13150.00, '2026-02-20T10:00:00Z', '2026-02-20T10:00:00Z');

-- Verification (Flow 2):
-- SELECT 'Material Request' as doc, request_no as doc_no, status, NULL::numeric as total FROM material_requests WHERE id = 'e0000001-0001-4000-a000-000000000001'
-- UNION ALL SELECT 'RFQ', 'RFQ-'||id::text, status, NULL FROM rfqs WHERE id = 'e0000001-0001-4000-a000-000000000002'
-- UNION ALL SELECT 'Purchase Order', 'PO-'||id::text, status, grand_total FROM purchase_orders WHERE id = 'e0000001-0001-4000-a000-000000000003'
-- UNION ALL SELECT 'Purchase Receipt', purchase_receipt_no, status, NULL FROM purchase_receipts WHERE id = 'e0000001-0001-4000-a000-000000000004'
-- UNION ALL SELECT 'Invoice', invoice_no, status, grand_total FROM invoices WHERE id = 'e0000001-0001-4000-a000-000000000005'
-- UNION ALL SELECT 'Payment', payment_no, status, amount FROM payments WHERE id = 'e0000001-0001-4000-a000-000000000006';


-- =============================================================================
-- COMMIT
-- =============================================================================

COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES (run these after the seed to confirm everything)
-- =============================================================================

-- V1: Table counts
-- SELECT 'suppliers' as tbl, COUNT(*) FROM suppliers WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
-- UNION ALL SELECT 'item_prices', COUNT(*) FROM item_prices WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
-- UNION ALL SELECT 'item_suppliers', COUNT(*) FROM item_suppliers WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
-- UNION ALL SELECT 'stock_levels (seed items)', COUNT(*) FROM stock_levels WHERE product_id IN ('f47ac10b-58cc-4372-a567-0e02b2c3d471','f47ac10b-58cc-4372-a567-0e02b2c3d472','f47ac10b-58cc-4372-a567-0e02b2c3d473','f47ac10b-58cc-4372-a567-0e02b2c3d478','f47ac10b-58cc-4372-a567-0e02b2c3d479')
-- UNION ALL SELECT 'stock_entries (seed)', COUNT(*) FROM stock_entries WHERE stock_entry_no LIKE 'STE-SEED-%'
-- UNION ALL SELECT 'stock_movements (seed)', COUNT(*) FROM stock_movements WHERE reference_id IN ('b0000001-0001-4000-a000-000000000001','b0000001-0001-4000-a000-000000000002','b0000001-0001-4000-a000-000000000003','c0000001-0001-4000-a000-000000000001')
-- UNION ALL SELECT 'stock_reconciliations (seed)', COUNT(*) FROM stock_reconciliations WHERE reconciliation_no = 'RECON-SEED-001'
-- UNION ALL SELECT 'quotations (seed)', COUNT(*) FROM quotations WHERE quotation_no = 'QTN-SEED-001'
-- UNION ALL SELECT 'sales_orders (seed)', COUNT(*) FROM sales_orders WHERE sales_order_no = 'SO-SEED-001'
-- UNION ALL SELECT 'pick_lists (seed)', COUNT(*) FROM pick_lists WHERE pick_list_no = 'PL-SEED-001'
-- UNION ALL SELECT 'delivery_notes (seed)', COUNT(*) FROM delivery_notes WHERE delivery_note_no = 'DN-SEED-001'
-- UNION ALL SELECT 'invoices (seed)', COUNT(*) FROM invoices WHERE invoice_no LIKE 'INV-SEED-%'
-- UNION ALL SELECT 'payments (seed)', COUNT(*) FROM payments WHERE payment_no LIKE 'PAY-SEED-%'
-- UNION ALL SELECT 'material_requests (seed)', COUNT(*) FROM material_requests WHERE request_no = 'MR-SEED-001'
-- UNION ALL SELECT 'rfqs (seed)', COUNT(*) FROM rfqs WHERE id = 'e0000001-0001-4000-a000-000000000002'
-- UNION ALL SELECT 'supplier_quotes (seed)', COUNT(*) FROM supplier_quotes WHERE rfq_line_id IN ('e0000001-0001-4000-a000-000000000021','e0000001-0001-4000-a000-000000000022')
-- UNION ALL SELECT 'purchase_orders (seed)', COUNT(*) FROM purchase_orders WHERE id = 'e0000001-0001-4000-a000-000000000003'
-- UNION ALL SELECT 'purchase_receipts (seed)', COUNT(*) FROM purchase_receipts WHERE purchase_receipt_no = 'PR-SEED-001'
-- ORDER BY tbl;

-- V2: Flow 1 trace (Sales)
-- SELECT 'Quotation' as step, 'QTN-SEED-001' as doc_no, 'accepted' as status, 4450.00 as amount
-- UNION ALL SELECT 'Sales Order', 'SO-SEED-001', 'delivered', 4450.00
-- UNION ALL SELECT 'Pick List', 'PL-SEED-001', 'completed', NULL
-- UNION ALL SELECT 'Delivery Note', 'DN-SEED-001', 'submitted', NULL
-- UNION ALL SELECT 'Sales Invoice', 'INV-SEED-001', 'paid', 4450.00
-- UNION ALL SELECT 'Payment Received', 'PAY-SEED-001', 'completed', 4450.00;

-- V3: Flow 2 trace (Procurement)
-- SELECT 'Material Request' as step, 'MR-SEED-001' as doc_no, 'fully_quoted' as status, NULL::numeric as amount
-- UNION ALL SELECT 'RFQ', 'RFQ (closed)', 'closed', NULL
-- UNION ALL SELECT 'Purchase Order', 'PO (TechWorld)', 'fully_received', 13150.00
-- UNION ALL SELECT 'Purchase Receipt', 'PR-SEED-001', 'submitted', NULL
-- UNION ALL SELECT 'Purchase Invoice', 'INV-SEED-002', 'paid', 13150.00
-- UNION ALL SELECT 'Payment Made', 'PAY-SEED-002', 'completed', 13150.00;

-- V4: Stock levels for seed items
-- SELECT i.item_code, i.item_name, w.code as warehouse, sl.quantity_on_hand, sl.quantity_reserved, sl.quantity_available
-- FROM stock_levels sl
-- JOIN items i ON i.id = sl.product_id
-- JOIN warehouses_extended w ON w.id = sl.warehouse_id
-- WHERE sl.product_id IN ('f47ac10b-58cc-4372-a567-0e02b2c3d471','f47ac10b-58cc-4372-a567-0e02b2c3d472','f47ac10b-58cc-4372-a567-0e02b2c3d473','f47ac10b-58cc-4372-a567-0e02b2c3d478','f47ac10b-58cc-4372-a567-0e02b2c3d479')
-- ORDER BY w.code, i.item_code;
