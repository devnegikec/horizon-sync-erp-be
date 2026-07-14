-- 1. Insert Warehouses
INSERT INTO warehouses_extended (
    id, organization_id, created_by, updated_by, name, code, description,
    warehouse_type, address_line1, city, state, postal_code, country,
    is_active, is_default, created_at, updated_at
) VALUES
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Main Warehouse', 'WH-MAIN', 'Primary storage', 'warehouse', '123 Industrial Ave', 'Mumbai', 'Maharashtra', '400001', 'India', true, true, NOW(), NOW()),
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Retail Store', 'WH-STORE', 'Retail outlet', 'store', '456 Market Street', 'Mumbai', 'Maharashtra', '400002', 'India', true, false, NOW(), NOW()),
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Transit Warehouse', 'WH-TRANSIT', 'Temporary storage', 'transit', null, null, null, null, null, true, false, NOW(), NOW());

-- 2. Insert Groups and Items (Aligned Column Lengths)
WITH inserted_groups AS (
    INSERT INTO item_groups (id, organization_id, created_by, updated_by, name, code, description, default_valuation_method, default_uom, is_active, created_at, updated_at)
    VALUES
    (gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Raw Materials', 'RM', 'Raw materials', 'fifo', 'Kg', true, NOW(), NOW()),
    (gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Finished Goods', 'FG', 'Finished products', 'moving_average', 'Nos', true, NOW(), NOW()),
    (gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Consumables', 'CON', 'Consumable items', 'fifo', 'Nos', true, NOW(), NOW()),
    (gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'Services', 'SRV', 'Service items', 'fifo', 'Hrs', true, NOW(), NOW())
    RETURNING code, id
)
INSERT INTO items (
    id, organization_id, created_by, updated_by, item_code,
    item_name, description, item_group_id, item_type, uom,
    maintain_stock, valuation_method, standard_rate, valuation_rate, status,
    created_at, updated_at
)
VALUES
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'RM-STEEL-001', 'Steel Sheet (2mm)', 'Steel sheet', (SELECT id FROM inserted_groups WHERE code = 'RM'), 'stock', 'Kg', true, 'fifo', 85.00, 75.00, 'active', NOW(), NOW()),
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'FG-WIDGET-001', 'Widget Pro', 'Premium widget', (SELECT id FROM inserted_groups WHERE code = 'FG'), 'stock', 'Nos', true, 'moving_average', 599.00, 350.00, 'active', NOW(), NOW()),
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'CON-PACK-001', 'Packaging Box', 'Medium box', (SELECT id FROM inserted_groups WHERE code = 'CON'), 'stock', 'Nos', true, 'fifo', 25.00, 18.00, 'active', NOW(), NOW()),
(gen_random_uuid(), '68ad4197-97ec-4333-a0fb-6b3589dec124', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'ec413f2c-b2f9-4965-8cf2-f2ef2f3dda7d', 'SRV-INSTALL-001', 'Installation', 'Service', (SELECT id FROM inserted_groups WHERE code = 'SRV'), 'service', 'Hrs', false, 'fifo', 500.00, 0.00, 'active', NOW(), NOW());
