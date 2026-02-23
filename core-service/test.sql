-- 1. The Pick List Header
INSERT INTO pick_lists (
    id, organization_id, pick_list_no, warehouse_id, status,
    pick_date, reference_type, remarks, created_at, updated_at
) VALUES (
    'e5555555-5555-5555-5555-555555555555',
    'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
    'PICK-2026-001',
    'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
    'draft', -- Ensure this matches your USER-DEFINED status enum
    CURRENT_TIMESTAMP,
    'Sales Order',
    'Priority shipment for Horizon Tech',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
);

-- 2. The Pick List Items (What needs to be grabbed)
INSERT INTO pick_list_items (
    id, organization_id, pick_list_id, item_id, warehouse_id,
    qty, picked_qty, uom, sort_order, created_at, updated_at
) VALUES
-- Item 1: Laptop (Qty 2, but only 1 picked so far to test partial picking UI)
(gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'e5555555-5555-5555-5555-555555555555',
 'f47ac10b-58cc-4372-a567-0e02b2c3d472', 'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
 2.0, 1.0, 'Unit', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),

-- Item 2: Mouse (Qty 5, 0 picked yet)
(gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'e5555555-5555-5555-5555-555555555555',
 '44e948b1-47a4-44b8-930d-87ab3bdb7fe6', 'cbf290a6-91cb-4c93-b9a6-db408bb3c274',
 5.0, 0.0, 'Piece', 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
