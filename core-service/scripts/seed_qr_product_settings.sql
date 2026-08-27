-- =============================================================================
-- QR Product Settings - Seed Data (org-agnostic, idempotent)
-- Seeds the standard lookup values for EVERY organization that does not
-- already have them. Safe to re-run.
-- Run after seed_qr_products.sql
-- =============================================================================

DO $$
DECLARE
    org RECORD;
BEGIN

FOR org IN SELECT id FROM organizations LOOP

-- ── Serial Prefixes ──────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, created_by, updated_by)
VALUES
(gen_random_uuid(), org.id, 'serial_prefix', 'PH', 'Pharma (PH)',        'Pharmaceutical products',   1, NULL, NULL),
(gen_random_uuid(), org.id, 'serial_prefix', 'RC', 'Rice / FMCG (RC)',   'FMCG food products',        2, NULL, NULL),
(gen_random_uuid(), org.id, 'serial_prefix', 'EB', 'Electronics (EB)',   'Consumer electronics',      3, NULL, NULL),
(gen_random_uuid(), org.id, 'serial_prefix', 'TX', 'Textiles (TX)',      'Textile & apparel',         4, NULL, NULL),
(gen_random_uuid(), org.id, 'serial_prefix', 'AU', 'Auto Parts (AU)',    'Automotive components',     5, NULL, NULL)
ON CONFLICT (organization_id, setting_type, value) DO NOTHING;

-- ── Channels ─────────────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, created_by, updated_by)
VALUES
(gen_random_uuid(), org.id, 'channel', 'retail',       'Retail',       'Direct retail stores',          1, NULL, NULL),
(gen_random_uuid(), org.id, 'channel', 'wholesale',    'Wholesale',    'Bulk wholesale distribution',   2, NULL, NULL),
(gen_random_uuid(), org.id, 'channel', 'online',       'Online',       'E-commerce / marketplace',      3, NULL, NULL),
(gen_random_uuid(), org.id, 'channel', 'distributor',  'Distributor',  'Third-party distributors',      4, NULL, NULL),
(gen_random_uuid(), org.id, 'channel', 'export',       'Export',       'International export',          5, NULL, NULL)
ON CONFLICT (organization_id, setting_type, value) DO NOTHING;

-- ── Destinations ─────────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, created_by, updated_by)
VALUES
(gen_random_uuid(), org.id, 'destination', 'IN',      'India',              'Domestic Indian market',    1, NULL, NULL),
(gen_random_uuid(), org.id, 'destination', 'UAE',     'UAE',                'United Arab Emirates',      2, NULL, NULL),
(gen_random_uuid(), org.id, 'destination', 'US',      'United States',      'North America',             3, NULL, NULL),
(gen_random_uuid(), org.id, 'destination', 'EU',      'European Union',     'EU member states',          4, NULL, NULL),
(gen_random_uuid(), org.id, 'destination', 'SEA',     'Southeast Asia',     'ASEAN region',              5, NULL, NULL)
ON CONFLICT (organization_id, setting_type, value) DO NOTHING;

-- ── Shelf Life ───────────────────────────────────────────────────────────────
INSERT INTO qr_product_settings (id, organization_id, setting_type, value, label, description, sort_order, extra_data, created_by, updated_by)
VALUES
(gen_random_uuid(), org.id, 'shelf_life', '3',   '3 Months',   'Short shelf life',    1, '{"months": 3}',  NULL, NULL),
(gen_random_uuid(), org.id, 'shelf_life', '6',   '6 Months',   'Medium shelf life',   2, '{"months": 6}',  NULL, NULL),
(gen_random_uuid(), org.id, 'shelf_life', '12',  '12 Months',  'Standard shelf life', 3, '{"months": 12}', NULL, NULL),
(gen_random_uuid(), org.id, 'shelf_life', '24',  '24 Months',  'Extended shelf life', 4, '{"months": 24}', NULL, NULL),
(gen_random_uuid(), org.id, 'shelf_life', '36',  '36 Months',  'Long shelf life',     5, '{"months": 36}', NULL, NULL)
ON CONFLICT (organization_id, setting_type, value) DO NOTHING;

END LOOP;

RAISE NOTICE '=== QR Product Settings seed complete (all orgs, idempotent) ===';

END $$;

-- Verify
SELECT organization_id, setting_type, COUNT(*) AS count
FROM qr_product_settings
WHERE deleted_at IS NULL
GROUP BY organization_id, setting_type
ORDER BY organization_id, setting_type;
