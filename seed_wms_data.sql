-- =============================================================================
-- WMS SEED DATA — Warehouse QR Inbound/Outbound Module
-- Organization : Default Organization (bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150)
-- Warehouse    : Main Warehouse      (cbf290a6-91cb-4c93-b9a6-db408bb3c274)
-- Worker       : negi.yaten@gmail.com (386f1db2-caf1-40aa-aaec-bcf9a531356a)
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- CONSTANTS (referenced throughout)
-- ─────────────────────────────────────────────────────────────────────────────
-- org_id      : bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150
-- warehouse   : cbf290a6-91cb-4c93-b9a6-db408bb3c274
-- worker_id   : 386f1db2-caf1-40aa-aaec-bcf9a531356a
-- item 1      : f47ac10b-58cc-4372-a567-0e02b2c3d471  HZN-LP-01  Horizon Pro Laptop
-- item 2      : f47ac10b-58cc-4372-a567-0e02b2c3d472  HZN-MO-05  Optical Gaming Mouse
-- item 3      : f47ac10b-58cc-4372-a567-0e02b2c3d473  HZN-KB-09  Mechanical Keyboard
-- item 4      : f47ac10b-58cc-4372-a567-0e02b2c3d478  HZN-MN-27  27-inch 4K Monitor
-- item 5      : 44e948b1-47a4-44b8-930d-87ab3bdb7fe6  RAMBO-09   Rambo Mix
-- item 6      : 84e6f7bd-06d1-443f-b81d-676cae252f63  IEO-908    Red Tonic
-- item_group  : d3478470-32a3-4db2-b665-195920b44a7e  Finished Goods
-- item_group2 : 76fb273a-70cd-45a1-bbc7-fbb370f09b2b  Raw Materials
-- =============================================================================

-- =============================================================================
-- 1. WAREHOUSE LOCATIONS  (Zone → Aisle → Bay → Level → Bin)
-- =============================================================================

-- ── ZONES ────────────────────────────────────────────────────────────────────
INSERT INTO warehouse_locations
  (id, organization_id, warehouse_id, parent_location_id, location_type,
   code, full_path, name, capacity, total_capacity, available_capacity,
   capacity_uom, position_x, position_y, is_active, version)
VALUES
  ('a0000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   NULL, 'zone', 'Z01', 'Z01', 'Bulk Storage',
   0, 2400, 1650, 'units', 0, 0, true, 1),

  ('a0000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   NULL, 'zone', 'Z02', 'Z02', 'Cold Storage',
   0, 800, 600, 'units', 50, 0, true, 1),

  ('a0000001-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   NULL, 'zone', 'Z03', 'Z03', 'Receiving Dock',
   0, 400, 400, 'units', 100, 0, true, 1);

-- ── AISLES ───────────────────────────────────────────────────────────────────
INSERT INTO warehouse_locations
  (id, organization_id, warehouse_id, parent_location_id, location_type,
   code, full_path, name, capacity, total_capacity, available_capacity,
   capacity_uom, position_x, position_y, is_active, version)
VALUES
  -- Z01 aisles
  ('a0000002-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000001-0000-0000-0000-000000000001', 'aisle', 'A01', 'Z01-A01', 'Aisle 01',
   0, 1200, 800, 'units', 5, 0, true, 1),

  ('a0000002-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000001-0000-0000-0000-000000000001', 'aisle', 'A02', 'Z01-A02', 'Aisle 02',
   0, 1200, 850, 'units', 15, 0, true, 1),

  -- Z02 aisle
  ('a0000002-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000001-0000-0000-0000-000000000002', 'aisle', 'A01', 'Z02-A01', 'Cold Aisle 01',
   0, 800, 600, 'units', 55, 0, true, 1);

-- ── BAYS ─────────────────────────────────────────────────────────────────────
INSERT INTO warehouse_locations
  (id, organization_id, warehouse_id, parent_location_id, location_type,
   code, full_path, name, capacity, total_capacity, available_capacity,
   capacity_uom, position_x, position_y, is_active, version)
VALUES
  -- Z01-A01 bays
  ('a0000003-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000002-0000-0000-0000-000000000001', 'bay', 'B01', 'Z01-A01-B01', 'Bay 01',
   0, 600, 400, 'units', 5, 2, true, 1),

  ('a0000003-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000002-0000-0000-0000-000000000001', 'bay', 'B02', 'Z01-A01-B02', 'Bay 02',
   0, 600, 400, 'units', 5, 8, true, 1),

  -- Z01-A02 bay
  ('a0000003-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000002-0000-0000-0000-000000000002', 'bay', 'B01', 'Z01-A02-B01', 'Bay 01',
   0, 600, 425, 'units', 15, 2, true, 1),

  -- Z02-A01 bay
  ('a0000003-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000002-0000-0000-0000-000000000003', 'bay', 'B01', 'Z02-A01-B01', 'Cold Bay 01',
   0, 800, 600, 'units', 55, 2, true, 1);

-- ── LEVELS ───────────────────────────────────────────────────────────────────
INSERT INTO warehouse_locations
  (id, organization_id, warehouse_id, parent_location_id, location_type,
   code, full_path, name, capacity, total_capacity, available_capacity,
   capacity_uom, position_x, position_y, is_active, version)
VALUES
  -- Z01-A01-B01 levels
  ('a0000004-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000003-0000-0000-0000-000000000001', 'level', 'L01', 'Z01-A01-B01-L01', 'Level 01 (Ground)',
   0, 300, 200, 'units', 5, 1, true, 1),

  ('a0000004-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000003-0000-0000-0000-000000000001', 'level', 'L02', 'Z01-A01-B01-L02', 'Level 02',
   0, 300, 200, 'units', 5, 3, true, 1),

  -- Z01-A01-B02 level
  ('a0000004-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000003-0000-0000-0000-000000000002', 'level', 'L01', 'Z01-A01-B02-L01', 'Level 01 (Ground)',
   0, 300, 200, 'units', 5, 7, true, 1),

  -- Z01-A02-B01 level
  ('a0000004-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000003-0000-0000-0000-000000000003', 'level', 'L01', 'Z01-A02-B01-L01', 'Level 01 (Ground)',
   0, 300, 213, 'units', 15, 1, true, 1),

  -- Z02-A01-B01 level
  ('a0000004-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000003-0000-0000-0000-000000000004', 'level', 'L01', 'Z02-A01-B01-L01', 'Cold Level 01',
   0, 400, 300, 'units', 55, 1, true, 1);

-- ── BINS ─────────────────────────────────────────────────────────────────────
INSERT INTO warehouse_locations
  (id, organization_id, warehouse_id, parent_location_id, location_type,
   code, full_path, name, capacity, total_capacity, available_capacity,
   capacity_uom, position_x, position_y, is_active, version)
VALUES
  -- Z01-A01-B01-L01 bins
  ('a0000005-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000001', 'bin', 'BN01', 'Z01-A01-B01-L01-BN01', 'Bin 01',
   150, 150, 80, 'units', 5, 1, true, 1),

  ('a0000005-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000001', 'bin', 'BN02', 'Z01-A01-B01-L01-BN02', 'Bin 02',
   150, 150, 120, 'units', 5, 2, true, 1),

  -- Z01-A01-B01-L02 bins
  ('a0000005-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000002', 'bin', 'BN01', 'Z01-A01-B01-L02-BN01', 'Bin 01',
   150, 150, 100, 'units', 5, 3, true, 1),

  ('a0000005-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000002', 'bin', 'BN02', 'Z01-A01-B01-L02-BN02', 'Bin 02',
   150, 150, 100, 'units', 5, 4, true, 1),

  -- Z01-A01-B02-L01 bins
  ('a0000005-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000003', 'bin', 'BN01', 'Z01-A01-B02-L01-BN01', 'Bin 01',
   150, 150, 100, 'units', 5, 7, true, 1),

  ('a0000005-0000-0000-0000-000000000006',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000003', 'bin', 'BN02', 'Z01-A01-B02-L01-BN02', 'Bin 02',
   150, 150, 100, 'units', 5, 8, true, 1),

  -- Z01-A02-B01-L01 bins
  ('a0000005-0000-0000-0000-000000000007',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000004', 'bin', 'BN01', 'Z01-A02-B01-L01-BN01', 'Bin 01',
   150, 150, 87, 'units', 15, 1, true, 1),

  ('a0000005-0000-0000-0000-000000000008',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000004', 'bin', 'BN02', 'Z01-A02-B01-L01-BN02', 'Bin 02',
   150, 150, 126, 'units', 15, 2, true, 1),

  -- Z02-A01-B01-L01 bins (cold storage)
  ('a0000005-0000-0000-0000-000000000009',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000005', 'bin', 'BN01', 'Z02-A01-B01-L01-BN01', 'Cold Bin 01',
   200, 200, 150, 'units', 55, 1, true, 1),

  ('a0000005-0000-0000-0000-000000000010',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'a0000004-0000-0000-0000-000000000005', 'bin', 'BN02', 'Z02-A01-B01-L01-BN02', 'Cold Bin 02',
   200, 200, 150, 'units', 55, 3, true, 1);


-- =============================================================================
-- 2. LOCATION ALLOCATIONS
-- =============================================================================
-- Z01-A01 (Aisle 01) → Finished Goods (exclusive, fast movers near dock)
-- Z01-A02 (Aisle 02) → Raw Materials (preferred)

INSERT INTO location_allocations
  (id, organization_id, location_id, item_group_id, priority, allocation_type, is_active)
VALUES
  ('b0000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000002-0000-0000-0000-000000000001',   -- Z01-A01
   'd3478470-32a3-4db2-b665-195920b44a7e',   -- Finished Goods
   10, 'exclusive', true),

  ('b0000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000002-0000-0000-0000-000000000002',   -- Z01-A02
   '76fb273a-70cd-45a1-bbc7-fbb370f09b2b',   -- Raw Materials
   5, 'preferred', true);

-- =============================================================================
-- 3. BIN STOCK LEVELS  (pre-existing stock for FIFO pick list resolution)
-- =============================================================================

INSERT INTO bin_stock_levels
  (id, organization_id, bin_location_id, item_id, quantity_on_hand, batch_number, created_at)
VALUES
  -- BN01 (Z01-A01-B01-L01-BN01): 70 Horizon Pro Laptops, batch JAN-2025
  ('c0000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000001',
   'f47ac10b-58cc-4372-a567-0e02b2c3d471',
   70, 'BATCH-JAN-2025', NOW() - INTERVAL '30 days'),

  -- BN02 (Z01-A01-B01-L01-BN02): 30 Optical Gaming Mouse, batch JAN-2025
  ('c0000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000002',
   'f47ac10b-58cc-4372-a567-0e02b2c3d472',
   30, 'BATCH-JAN-2025', NOW() - INTERVAL '28 days'),

  -- BN01 (Z01-A01-B01-L02-BN01): 50 Mechanical Keyboards, batch FEB-2025
  ('c0000001-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000003',
   'f47ac10b-58cc-4372-a567-0e02b2c3d473',
   50, 'BATCH-FEB-2025', NOW() - INTERVAL '15 days'),

  -- BN02 (Z01-A01-B01-L02-BN02): 50 Mechanical Keyboards, batch MAR-2025
  ('c0000001-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000004',
   'f47ac10b-58cc-4372-a567-0e02b2c3d473',
   50, 'BATCH-MAR-2025', NOW() - INTERVAL '5 days'),

  -- BN01 (Z01-A01-B02-L01-BN01): 50 27-inch 4K Monitors, batch JAN-2025
  ('c0000001-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000005',
   'f47ac10b-58cc-4372-a567-0e02b2c3d478',
   50, 'BATCH-JAN-2025', NOW() - INTERVAL '25 days'),

  -- BN01 (Z01-A02-B01-L01-BN01): 63 Rambo Mix, batch FEB-2025
  ('c0000001-0000-0000-0000-000000000006',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000007',
   '44e948b1-47a4-44b8-930d-87ab3bdb7fe6',
   63, 'BATCH-FEB-2025', NOW() - INTERVAL '20 days'),

  -- BN02 (Z01-A02-B01-L01-BN02): 24 Red Tonic, batch FEB-2025
  ('c0000001-0000-0000-0000-000000000007',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000008',
   '84e6f7bd-06d1-443f-b81d-676cae252f63',
   24, 'BATCH-FEB-2025', NOW() - INTERVAL '18 days'),

  -- Cold BN01 (Z02-A01-B01-L01-BN01): 50 Red Tonic, batch JAN-2025
  ('c0000001-0000-0000-0000-000000000008',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a0000005-0000-0000-0000-000000000009',
   '84e6f7bd-06d1-443f-b81d-676cae252f63',
   50, 'BATCH-JAN-2025', NOW() - INTERVAL '35 days');


-- =============================================================================
-- 4. INBOUND SCAN SESSION  (status: closed — already ended)
-- =============================================================================

INSERT INTO scan_sessions
  (id, organization_id, session_type, worker_id, warehouse_id,
   dock_location, status, total_boxes_scanned, started_at, ended_at)
VALUES
  ('d0000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'inbound',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'Dock A', 'closed', 4,
   NOW() - INTERVAL '2 days',
   NOW() - INTERVAL '2 days' + INTERVAL '45 minutes'),

  -- Open session (worker currently scanning)
  ('d0000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'inbound',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'Dock B', 'open', 2,
   NOW() - INTERVAL '30 minutes',
   NULL);

-- ── SCAN SESSION ITEMS ───────────────────────────────────────────────────────
INSERT INTO scan_session_items
  (id, organization_id, session_id, qr_identifier, sku, quantity, batch_number,
   raw_qr_data, scanned_at)
VALUES
  -- Session 1 (closed) — 4 boxes
  ('d0000002-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'd0000001-0000-0000-0000-000000000001',
   'QR-BOX-001', 'HZN-LP-01', 20, 'BATCH-APR-2025',
   '{"id":"QR-BOX-001","sku":"HZN-LP-01","qty":20,"batch":"BATCH-APR-2025"}',
   NOW() - INTERVAL '2 days' + INTERVAL '5 minutes'),

  ('d0000002-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'd0000001-0000-0000-0000-000000000001',
   'QR-BOX-002', 'HZN-LP-01', 20, 'BATCH-APR-2025',
   '{"id":"QR-BOX-002","sku":"HZN-LP-01","qty":20,"batch":"BATCH-APR-2025"}',
   NOW() - INTERVAL '2 days' + INTERVAL '8 minutes'),

  ('d0000002-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'd0000001-0000-0000-0000-000000000001',
   'QR-BOX-003', 'HZN-MO-05', 50, 'BATCH-APR-2025',
   '{"id":"QR-BOX-003","sku":"HZN-MO-05","qty":50,"batch":"BATCH-APR-2025"}',
   NOW() - INTERVAL '2 days' + INTERVAL '12 minutes'),

  ('d0000002-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'd0000001-0000-0000-0000-000000000001',
   'QR-BOX-004', 'HZN-KB-09', 30, 'BATCH-APR-2025',
   '{"id":"QR-BOX-004","sku":"HZN-KB-09","qty":30,"batch":"BATCH-APR-2025"}',
   NOW() - INTERVAL '2 days' + INTERVAL '18 minutes'),

  -- Session 2 (open) — 2 boxes so far
  ('d0000002-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'd0000001-0000-0000-0000-000000000002',
   'QR-BOX-101', 'HZN-MN-27', 10, 'BATCH-APR-2025',
   '{"id":"QR-BOX-101","sku":"HZN-MN-27","qty":10,"batch":"BATCH-APR-2025"}',
   NOW() - INTERVAL '25 minutes'),

  ('d0000002-0000-0000-0000-000000000006',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'd0000001-0000-0000-0000-000000000002',
   'QR-BOX-102', 'RAMBO-09', 40, 'BATCH-APR-2025',
   '{"id":"QR-BOX-102","sku":"RAMBO-09","qty":40,"batch":"BATCH-APR-2025"}',
   NOW() - INTERVAL '20 minutes');

-- =============================================================================
-- 5. RECEIVING SLIPS
-- =============================================================================

INSERT INTO receiving_slips
  (id, organization_id, slip_number, session_id, warehouse_id,
   status, total_boxes, total_items, created_at, updated_at)
VALUES
  -- Slip 1: PENDING_REVIEW (from session 1)
  ('e0000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'RS-2025-0001',
   'd0000001-0000-0000-0000-000000000001',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'pending_review', 4, 120,
   NOW() - INTERVAL '2 days' + INTERVAL '46 minutes',
   NOW() - INTERVAL '2 days' + INTERVAL '46 minutes'),

  -- Slip 2: PENDING_PUTAWAY (approved, put-away list being generated)
  ('e0000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'RS-2025-0002',
   'd0000001-0000-0000-0000-000000000001',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'pending_putaway', 3, 90,
   NOW() - INTERVAL '5 days',
   NOW() - INTERVAL '4 days' + INTERVAL '2 hours'),

  -- Slip 3: PUTAWAY_COMPLETE
  ('e0000001-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'RS-2025-0003',
   'd0000001-0000-0000-0000-000000000001',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'putaway_complete', 2, 60,
   NOW() - INTERVAL '10 days',
   NOW() - INTERVAL '9 days');

-- ── RECEIVING SLIP ITEMS ─────────────────────────────────────────────────────
INSERT INTO receiving_slip_items
  (id, organization_id, slip_id, sku, batch_number,
   quantity, box_count, flag, notes)
VALUES
  -- Slip 1 items
  ('e0000002-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000001',
   'HZN-LP-01', 'BATCH-APR-2025', 40, 2, 'ok', NULL),

  ('e0000002-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000001',
   'HZN-MO-05', 'BATCH-APR-2025', 50, 1, 'ok', NULL),

  ('e0000002-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000001',
   'HZN-KB-09', 'BATCH-APR-2025', 30, 1, 'short', '5 units missing from box QR-BOX-004'),

  -- Slip 2 items
  ('e0000002-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000002',
   'HZN-LP-01', 'BATCH-MAR-2025', 30, 1, 'ok', NULL),

  ('e0000002-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000002',
   'HZN-MN-27', 'BATCH-MAR-2025', 40, 1, 'ok', NULL),

  ('e0000002-0000-0000-0000-000000000006',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000002',
   'RAMBO-09', 'BATCH-MAR-2025', 20, 1, 'damaged', 'Box corner crushed, items intact'),

  -- Slip 3 items
  ('e0000002-0000-0000-0000-000000000007',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000003',
   'IEO-908', 'BATCH-FEB-2025', 30, 1, 'ok', NULL),

  ('e0000002-0000-0000-0000-000000000008',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'e0000001-0000-0000-0000-000000000003',
   'HZN-KB-09', 'BATCH-FEB-2025', 30, 1, 'ok', NULL);


-- =============================================================================
-- 6. PUT-AWAY LISTS  (linked to receiving slips)
-- =============================================================================

INSERT INTO put_away_lists
  (id, organization_id, warehouse_id, put_away_list_no, status,
   reference_type, reference_id, receiving_slip_id, assigned_to, created_by)
VALUES
  -- Put-away for Slip 2 (in_progress)
  ('f0000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'PA-2025-0001', 'in_progress',
   'receiving_slip', 'e0000001-0000-0000-0000-000000000002',
   'e0000001-0000-0000-0000-000000000002',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a'),

  -- Put-away for Slip 3 (completed)
  ('f0000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'PA-2025-0002', 'completed',
   'receiving_slip', 'e0000001-0000-0000-0000-000000000003',
   'e0000001-0000-0000-0000-000000000003',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a');

-- ── PUT-AWAY LIST ITEMS ───────────────────────────────────────────────────────
INSERT INTO put_away_list_items
  (id, organization_id, put_away_list_id, item_id, sku, batch_number,
   quantity, bin_location_id, sort_order, status)
VALUES
  -- PA-2025-0001 items (in_progress)
  ('f0000002-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'f0000001-0000-0000-0000-000000000001',
   'f47ac10b-58cc-4372-a567-0e02b2c3d471', 'HZN-LP-01', 'BATCH-MAR-2025',
   30, 'a0000005-0000-0000-0000-000000000001', 1, 'completed'),

  ('f0000002-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'f0000001-0000-0000-0000-000000000001',
   'f47ac10b-58cc-4372-a567-0e02b2c3d478', 'HZN-MN-27', 'BATCH-MAR-2025',
   40, 'a0000005-0000-0000-0000-000000000005', 2, 'pending'),

  ('f0000002-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'f0000001-0000-0000-0000-000000000001',
   '44e948b1-47a4-44b8-930d-87ab3bdb7fe6', 'RAMBO-09', 'BATCH-MAR-2025',
   20, 'a0000005-0000-0000-0000-000000000007', 3, 'pending'),

  -- PA-2025-0002 items (completed)
  ('f0000002-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'f0000001-0000-0000-0000-000000000002',
   '84e6f7bd-06d1-443f-b81d-676cae252f63', 'IEO-908', 'BATCH-FEB-2025',
   30, 'a0000005-0000-0000-0000-000000000009', 1, 'completed'),

  ('f0000002-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'f0000001-0000-0000-0000-000000000002',
   'f47ac10b-58cc-4372-a567-0e02b2c3d473', 'HZN-KB-09', 'BATCH-FEB-2025',
   30, 'a0000005-0000-0000-0000-000000000003', 2, 'completed');

-- =============================================================================
-- 7. OUTBOUND PICK LISTS  (SAP invoice-triggered)
-- =============================================================================

INSERT INTO pick_lists
  (id, organization_id, warehouse_id, pick_list_no, status,
   reference_type, invoice_reference, pick_date, created_at, updated_at)
VALUES
  -- PL-001: OPEN (just created from SAP invoice)
  ('a1000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'PL-2025-0001', 'draft',
   'sap_invoice', 'SAP-INV-2025-0042',
   NOW()::date, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour'),

  -- PL-002: IN_PROGRESS (picker has started)
  ('a1000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'PL-2025-0002', 'in_progress',
   'sap_invoice', 'SAP-INV-2025-0038',
   NOW()::date, NOW() - INTERVAL '3 hours', NOW() - INTERVAL '1 hour'),

  -- PL-003: COMPLETED (all items picked)
  ('a1000001-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'PL-2025-0003', 'completed',
   'sap_invoice', 'SAP-INV-2025-0031',
   (NOW() - INTERVAL '1 day')::date,
   NOW() - INTERVAL '1 day', NOW() - INTERVAL '20 hours'),

  -- PL-004: CANCELLED
  ('a1000001-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'PL-2025-0004', 'cancelled',
   'sap_invoice', 'SAP-INV-2025-0029',
   (NOW() - INTERVAL '2 days')::date,
   NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '2 hours');

-- ── PICK LIST ITEMS ───────────────────────────────────────────────────────────
INSERT INTO pick_list_items
  (id, organization_id, pick_list_id, item_id, warehouse_id, qty, picked_qty,
   uom, batch_no, bin_location_id, sort_order)
VALUES
  -- PL-001 items (OPEN — nothing picked yet)
  ('a1000002-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000001',
   'f47ac10b-58cc-4372-a567-0e02b2c3d471',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   10, 0, 'Pcs', 'BATCH-JAN-2025',
   'a0000005-0000-0000-0000-000000000001', 1),

  ('a1000002-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000001',
   'f47ac10b-58cc-4372-a567-0e02b2c3d472',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   15, 0, 'Pcs', 'BATCH-JAN-2025',
   'a0000005-0000-0000-0000-000000000002', 2),

  ('a1000002-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000001',
   'f47ac10b-58cc-4372-a567-0e02b2c3d478',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   5, 0, 'Pcs', 'BATCH-JAN-2025',
   'a0000005-0000-0000-0000-000000000005', 3),

  -- PL-002 items (IN_PROGRESS — partially picked)
  ('a1000002-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000002',
   'f47ac10b-58cc-4372-a567-0e02b2c3d473',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   20, 20, 'Pcs', 'BATCH-FEB-2025',
   'a0000005-0000-0000-0000-000000000003', 1),

  ('a1000002-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000002',
   '44e948b1-47a4-44b8-930d-87ab3bdb7fe6',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   30, 10, 'Pcs', 'BATCH-FEB-2025',
   'a0000005-0000-0000-0000-000000000007', 2),

  -- PL-003 items (COMPLETED — all picked)
  ('a1000002-0000-0000-0000-000000000006',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000003',
   '84e6f7bd-06d1-443f-b81d-676cae252f63',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   25, 25, 'Pcs', 'BATCH-JAN-2025',
   'a0000005-0000-0000-0000-000000000009', 1),

  ('a1000002-0000-0000-0000-000000000007',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000003',
   'f47ac10b-58cc-4372-a567-0e02b2c3d471',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   5, 5, 'Pcs', 'BATCH-JAN-2025',
   'a0000005-0000-0000-0000-000000000001', 2);


-- =============================================================================
-- 8. GATE VERIFICATION SESSIONS  (linked to completed pick list PL-003)
-- =============================================================================

INSERT INTO gate_verification_sessions
  (id, organization_id, pick_list_id, warehouse_id, vehicle_number, driver_name,
   driver_contact, status, worker_id, verified_at)
VALUES
  -- Verified session (linked to PL-003)
  ('a2000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000003',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'MH-12-AB-1234', 'Rajesh Kumar', '+91-9876543210',
   'verified',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   NOW() - INTERVAL '21 hours'),

  -- Open session (linked to PL-002, gate check in progress)
  ('a2000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a1000001-0000-0000-0000-000000000002',
   'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
   'DL-01-CD-5678', 'Suresh Sharma', '+91-9123456789',
   'open',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   NULL);

-- ── GATE VERIFICATION ITEMS ───────────────────────────────────────────────────
INSERT INTO gate_verification_items
  (id, organization_id, gate_session_id, qr_identifier, sku, quantity,
   status, scanned_at)
VALUES
  -- Session 1 (verified) — all items verified
  ('a2000002-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a2000001-0000-0000-0000-000000000001',
   'QR-GATE-001', 'IEO-908', 25,
   'verified', NOW() - INTERVAL '21 hours' + INTERVAL '5 minutes'),

  ('a2000002-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a2000001-0000-0000-0000-000000000001',
   'QR-GATE-002', 'HZN-LP-01', 5,
   'verified', NOW() - INTERVAL '21 hours' + INTERVAL '8 minutes'),

  -- Session 2 (open) — partial scan, one unauthorized
  ('a2000002-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a2000001-0000-0000-0000-000000000002',
   'QR-GATE-101', 'HZN-KB-09', 20,
   'verified', NOW() - INTERVAL '25 minutes'),

  ('a2000002-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a2000001-0000-0000-0000-000000000002',
   'QR-GATE-999', 'HZN-MN-27', 5,
   'unauthorized', NOW() - INTERVAL '20 minutes');

-- =============================================================================
-- 9. DISPATCH RECORDS  (from verified gate session)
-- =============================================================================

INSERT INTO dispatch_records
  (id, organization_id, dispatch_number, pick_list_id, gate_session_id,
   invoice_reference, vehicle_number, driver_name, dispatched_at)
VALUES
  ('a3000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'DSP-2025-0001',
   'a1000001-0000-0000-0000-000000000003',
   'a2000001-0000-0000-0000-000000000001',
   'SAP-INV-2025-0031',
   'MH-12-AB-1234', 'Rajesh Kumar',
   NOW() - INTERVAL '21 hours');

-- Link dispatch back to pick list
UPDATE pick_lists
SET dispatch_record_id = 'a3000001-0000-0000-0000-000000000001'
WHERE id = 'a1000001-0000-0000-0000-000000000003';

-- =============================================================================
-- 10. WORKER TASKS
-- =============================================================================

INSERT INTO worker_tasks
  (id, organization_id, task_type, worker_id, reference_id,
   status, assigned_at, started_at, completed_at)
VALUES
  -- Put-away task for PA-2025-0001 (in_progress)
  ('a4000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'put_away',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'f0000001-0000-0000-0000-000000000001',
   'in_progress',
   NOW() - INTERVAL '4 days',
   NOW() - INTERVAL '4 days' + INTERVAL '30 minutes',
   NULL),

  -- Put-away task for PA-2025-0002 (completed)
  ('a4000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'put_away',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'f0000001-0000-0000-0000-000000000002',
   'completed',
   NOW() - INTERVAL '9 days',
   NOW() - INTERVAL '9 days' + INTERVAL '20 minutes',
   NOW() - INTERVAL '9 days' + INTERVAL '2 hours'),

  -- Pick task for PL-2025-0001 (assigned)
  ('a4000001-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'pick',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'a1000001-0000-0000-0000-000000000001',
   'assigned',
   NOW() - INTERVAL '1 hour',
   NULL, NULL),

  -- Pick task for PL-2025-0002 (in_progress)
  ('a4000001-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'pick',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'a1000001-0000-0000-0000-000000000002',
   'in_progress',
   NOW() - INTERVAL '3 hours',
   NOW() - INTERVAL '2 hours',
   NULL),

  -- Pick task for PL-2025-0003 (completed)
  ('a4000001-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'pick',
   '386f1db2-caf1-40aa-aaec-bcf9a531356a',
   'a1000001-0000-0000-0000-000000000003',
   'completed',
   NOW() - INTERVAL '1 day',
   NOW() - INTERVAL '23 hours',
   NOW() - INTERVAL '22 hours');

-- =============================================================================
-- 11. LOCATION SCANS  (time tracking — start/finish at bins)
-- =============================================================================

INSERT INTO location_scans
  (id, organization_id, worker_task_id, location_code,
   scan_type, scanned_at, elapsed_seconds)
VALUES
  -- Task a4000001-002 (put-away completed) — time tracking records
  ('a5000001-0000-0000-0000-000000000001',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a4000001-0000-0000-0000-000000000002',
   'Z02-A01-B01-L01-BN01',
   'start', NOW() - INTERVAL '9 days' + INTERVAL '25 minutes', NULL),

  ('a5000001-0000-0000-0000-000000000002',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a4000001-0000-0000-0000-000000000002',
   'Z02-A01-B01-L01-BN01',
   'finish', NOW() - INTERVAL '9 days' + INTERVAL '37 minutes', 720),

  ('a5000001-0000-0000-0000-000000000003',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a4000001-0000-0000-0000-000000000002',
   'Z01-A01-B01-L02-BN01',
   'start', NOW() - INTERVAL '9 days' + INTERVAL '45 minutes', NULL),

  ('a5000001-0000-0000-0000-000000000004',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a4000001-0000-0000-0000-000000000002',
   'Z01-A01-B01-L02-BN01',
   'finish', NOW() - INTERVAL '9 days' + INTERVAL '58 minutes', 780),

  -- Task a4000001-004 (pick in_progress) — start scan recorded, finish pending
  ('a5000001-0000-0000-0000-000000000005',
   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
   'a4000001-0000-0000-0000-000000000004',
   'Z01-A01-B01-L02-BN01',
   'start', NOW() - INTERVAL '90 minutes', NULL);

-- =============================================================================
-- 12. VERIFY COUNTS
-- =============================================================================

SELECT 'warehouse_locations' AS tbl, COUNT(*) FROM warehouse_locations WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'location_allocations', COUNT(*) FROM location_allocations WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'bin_stock_levels', COUNT(*) FROM bin_stock_levels WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'scan_sessions', COUNT(*) FROM scan_sessions WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'scan_session_items', COUNT(*) FROM scan_session_items WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'receiving_slips', COUNT(*) FROM receiving_slips WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'receiving_slip_items', COUNT(*) FROM receiving_slip_items WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'put_away_lists', COUNT(*) FROM put_away_lists WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'put_away_list_items', COUNT(*) FROM put_away_list_items WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'pick_lists (wms)', COUNT(*) FROM pick_lists WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150' AND invoice_reference IS NOT NULL
UNION ALL
SELECT 'pick_list_items (wms)', COUNT(*) FROM pick_list_items WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'gate_verification_sessions', COUNT(*) FROM gate_verification_sessions WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'gate_verification_items', COUNT(*) FROM gate_verification_items WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'dispatch_records', COUNT(*) FROM dispatch_records WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'worker_tasks', COUNT(*) FROM worker_tasks WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'location_scans', COUNT(*) FROM location_scans WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';

COMMIT;
