-- =============================================================================
-- QR Product Settings - Seed Data
-- Run after seed_qr_products.sql
-- =============================================================================

DO $$
DECLARE
    org_id   UUID := 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
    admin_id UUID := '8d509f22-5fe5-4765-9496-3a236cae2af1';
BEGIN

-- ── Serial Prefixes ──────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, created_by, updated_by)
VALUES
(gen_random_uuid(), org_id, 'serial_prefix', 'PH', 'Pharma (PH)',        'Pharmaceutical products',   1, admin_id, admin_id),
(gen_random_uuid(), org_id, 'serial_prefix', 'RC', 'Rice / FMCG (RC)',   'FMCG food products',        2, admin_id, admin_id),
(gen_random_uuid(), org_id, 'serial_prefix', 'EB', 'Electronics (EB)',   'Consumer electronics',      3, admin_id, admin_id),
(gen_random_uuid(), org_id, 'serial_prefix', 'TX', 'Textiles (TX)',      'Textile & apparel',         4, admin_id, admin_id),
(gen_random_uuid(), org_id, 'serial_prefix', 'AU', 'Auto Parts (AU)',    'Automotive components',     5, admin_id, admin_id);

-- ── Channels ─────────────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, created_by, updated_by)
VALUES
(gen_random_uuid(), org_id, 'channel', 'retail',       'Retail',       'Direct retail stores',          1, admin_id, admin_id),
(gen_random_uuid(), org_id, 'channel', 'wholesale',    'Wholesale',    'Bulk wholesale distribution',   2, admin_id, admin_id),
(gen_random_uuid(), org_id, 'channel', 'online',       'Online',       'E-commerce / marketplace',      3, admin_id, admin_id),
(gen_random_uuid(), org_id, 'channel', 'distributor',  'Distributor',  'Third-party distributors',      4, admin_id, admin_id),
(gen_random_uuid(), org_id, 'channel', 'export',       'Export',       'International export',          5, admin_id, admin_id);

-- ── Destinations ─────────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, created_by, updated_by)
VALUES
(gen_random_uuid(), org_id, 'destination', 'IN',      'India',              'Domestic Indian market',    1, admin_id, admin_id),
(gen_random_uuid(), org_id, 'destination', 'UAE',     'UAE',                'United Arab Emirates',      2, admin_id, admin_id),
(gen_random_uuid(), org_id, 'destination', 'US',      'United States',      'North America',             3, admin_id, admin_id),
(gen_random_uuid(), org_id, 'destination', 'EU',      'European Union',     'EU member states',          4, admin_id, admin_id),
(gen_random_uuid(), org_id, 'destination', 'SEA',     'Southeast Asia',     'ASEAN region',              5, admin_id, admin_id);

-- ── Shelf Life ───────────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, extra_data, created_by, updated_by)
VALUES
(gen_random_uuid(), org_id, 'shelf_life', '3',   '3 Months',   'Short shelf life',    1, '{"months": 3}',  admin_id, admin_id),
(gen_random_uuid(), org_id, 'shelf_life', '6',   '6 Months',   'Medium shelf life',   2, '{"months": 6}',  admin_id, admin_id),
(gen_random_uuid(), org_id, 'shelf_life', '12',  '12 Months',  'Standard shelf life', 3, '{"months": 12}', admin_id, admin_id),
(gen_random_uuid(), org_id, 'shelf_life', '24',  '24 Months',  'Extended shelf life', 4, '{"months": 24}', admin_id, admin_id),
(gen_random_uuid(), org_id, 'shelf_life', '36',  '36 Months',  'Long shelf life',     5, '{"months": 36}', admin_id, admin_id);

RAISE NOTICE '=== QR Product Settings seed complete (20 rows) ===';

END $$;

-- Verify
SELECT setting_type, COUNT(*) AS count
FROM qr_product_settings
WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
  AND deleted_at IS NULL
GROUP BY setting_type
ORDER BY setting_type;
