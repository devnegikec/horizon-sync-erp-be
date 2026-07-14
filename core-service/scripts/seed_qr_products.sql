-- =============================================================================
-- QR Products Module - Seed Data
-- Compatible with TablePlus, DBeaver, pgAdmin, and psql
-- =============================================================================
-- Replace the two UUIDs below with your actual values, then run the whole script.
-- =============================================================================

DO $$
DECLARE
    -- ── CONFIGURE THESE TWO VALUES ───────────────────────────────────────────
    org_id   UUID := 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
    admin_id UUID := '8d509f22-5fe5-4765-9496-3a236cae2af1';
    -- ─────────────────────────────────────────────────────────────────────────

    p_pharma_id      UUID := gen_random_uuid();
    p_fmcg_id        UUID := gen_random_uuid();
    p_electronics_id UUID := gen_random_uuid();

    b_pharma_id      UUID := gen_random_uuid();
    b_fmcg_id        UUID := gen_random_uuid();
    b_electronics_id UUID := gen_random_uuid();

    ap_pharma_id     UUID := gen_random_uuid();
    ap_fmcg_id       UUID := gen_random_uuid();

    track_pallet_id  UUID := gen_random_uuid();
    track_box_id     UUID := gen_random_uuid();
    track_unit_id    UUID := gen_random_uuid();

    i      INT;
    serial TEXT;
BEGIN

-- =============================================================================
-- 1. QR Products
-- =============================================================================
INSERT INTO qr_products (
    id, organization_id, name, generic_name, gtin, industry,
    landing_page, email, phone_number,
    activation_method, sr_number_type,
    redirect_to_client, warranty_period_months, qr_type,
    is_active, created_by, updated_by, created_at, updated_at
) VALUES
(
    p_pharma_id, org_id,
    'Paracetamol 500mg Tablets', 'Paracetamol',
    '8901234567890', 'Pharmaceuticals',
    'https://verify.example.com/pharma', 'pharma@example.com', '+911234567890',
    'pre', 'numeric',
    false, 24, 'standard',
    true, admin_id, admin_id, NOW(), NOW()
),
(
    p_fmcg_id, org_id,
    'Premium Basmati Rice 5kg', 'Basmati Rice',
    '8902345678901', 'FMCG',
    'https://verify.example.com/rice', 'fmcg@example.com', '+911234567891',
    'pre', 'alphanumeric',
    false, 6, 'standard',
    true, admin_id, admin_id, NOW(), NOW()
),
(
    p_electronics_id, org_id,
    'Wireless Bluetooth Earbuds', 'TWS Earbuds',
    '8903456789012', 'Electronics',
    'https://verify.example.com/earbuds', 'electronics@example.com', '+911234567892',
    'post', 'alphanumeric',
    true, 12, 'cascade',
    true, admin_id, admin_id, NOW(), NOW()
);

RAISE NOTICE 'Created 3 QR products';

-- =============================================================================
-- 2. QR Blocks
-- =============================================================================
INSERT INTO qr_blocks (
    id, organization_id, product_id,
    batch, serial_prefix, sr_number_type,
    quantity, cert_type, size, colour_desc, price,
    task_status, qr_image,
    manufacture_date, expiry_date,
    created_by, updated_by, created_at, updated_at
) VALUES
(
    b_pharma_id, org_id, p_pharma_id,
    'BATCH-PHARMA-2025-001', 'PH', 'numeric',
    500, 'A', 'A4', 'White', 1200,
    'completed', true,
    '2025-01-15', '2027-01-14',
    admin_id, admin_id, NOW(), NOW()
),
(
    b_fmcg_id, org_id, p_fmcg_id,
    'BATCH-FMCG-2025-001', 'RC', 'alphanumeric',
    1000, 'B', 'A5', 'Gold', 850,
    'completed', true,
    '2025-02-01', '2026-01-31',
    admin_id, admin_id, NOW(), NOW()
),
(
    b_electronics_id, org_id, p_electronics_id,
    'BATCH-ELEC-2025-001', 'EB', 'alphanumeric',
    200, 'A', 'A6', 'Black', 4500,
    'completed', false,
    '2025-03-01', '2028-02-28',
    admin_id, admin_id, NOW(), NOW()
);

RAISE NOTICE 'Created 3 QR blocks';

-- =============================================================================
-- 3. Product Items (5 per block = 15 total)
-- =============================================================================

-- Pharma items
FOR i IN 1..5 LOOP
    serial := 'PH' || LPAD(i::TEXT, 8, '0');
    INSERT INTO product_items (
        id, organization_id, product_id, block_id,
        serial_number, secrete_code, token_id,
        is_unit, is_suspicious, is_verify, is_auth,
        qr_deactive, qr_deactive_unit,
        scan_date, scans, destination_market,
        created_by, updated_by, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), org_id, p_pharma_id, b_pharma_id,
        serial,
        md5(serial || 'pharma-secret'),
        'TOK-' || serial,
        true,
        (i = 3),
        (i <= 3),
        (i <= 2),
        (i > 2),
        (i > 2),
        CASE WHEN i <= 2 THEN NOW() - INTERVAL '5 days' ELSE NULL END,
        CASE WHEN i <= 2 THEN i * 3 ELSE 0 END,
        'India',
        admin_id, admin_id, NOW(), NOW()
    );
END LOOP;

-- FMCG items
FOR i IN 1..5 LOOP
    serial := 'RC' || LPAD(i::TEXT, 8, '0');
    INSERT INTO product_items (
        id, organization_id, product_id, block_id,
        serial_number, secrete_code, token_id,
        is_unit, is_suspicious, is_verify, is_auth,
        qr_deactive, qr_deactive_unit,
        scan_date, scans, destination_market,
        created_by, updated_by, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), org_id, p_fmcg_id, b_fmcg_id,
        serial,
        md5(serial || 'fmcg-secret'),
        'TOK-' || serial,
        true, false,
        (i <= 4),
        (i <= 3),
        (i > 3),
        (i > 3),
        CASE WHEN i <= 3 THEN NOW() - INTERVAL '2 days' ELSE NULL END,
        CASE WHEN i <= 3 THEN i * 2 ELSE 0 END,
        CASE WHEN i <= 2 THEN 'India' ELSE 'UAE' END,
        admin_id, admin_id, NOW(), NOW()
    );
END LOOP;

-- Electronics items
FOR i IN 1..5 LOOP
    serial := 'EB' || LPAD(i::TEXT, 8, '0');
    INSERT INTO product_items (
        id, organization_id, product_id, block_id,
        serial_number, secrete_code, token_id,
        is_unit, is_suspicious, is_verify, is_auth,
        qr_deactive, qr_deactive_unit,
        scan_date, scans, destination_market,
        created_by, updated_by, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), org_id, p_electronics_id, b_electronics_id,
        serial,
        md5(serial || 'elec-secret'),
        'TOK-' || serial,
        true, false,
        (i = 1),
        (i = 1),
        (i != 1),
        (i != 1),
        CASE WHEN i = 1 THEN NOW() - INTERVAL '1 day' ELSE NULL END,
        CASE WHEN i = 1 THEN 7 ELSE 0 END,
        'India',
        admin_id, admin_id, NOW(), NOW()
    );
END LOOP;

RAISE NOTICE 'Created 15 product items';

-- =============================================================================
-- 4. QR Activation Parameters
-- =============================================================================
INSERT INTO qr_activation_parameters (
    id, organization_id, product_id, block_id,
    manufacturing_date, expiry_date, manufacturing_unit,
    dispatch_batch, destination_market,
    mrp, currency, batch_size,
    qr_settings, qr_cascade,
    created_by, created_at
) VALUES
(
    ap_pharma_id, org_id, p_pharma_id, b_pharma_id,
    '2025-01-15', '2027-01-14', 'Mumbai Plant Unit-3',
    'DISP-2025-PH-001', 'India',
    120.00, 'INR', 500,
    true, false,
    admin_id, NOW()
),
(
    ap_fmcg_id, org_id, p_fmcg_id, b_fmcg_id,
    '2025-02-01', '2026-01-31', 'Haryana Plant Unit-1',
    'DISP-2025-RC-001', 'India',
    450.00, 'INR', 1000,
    true, false,
    admin_id, NOW()
),
(
    gen_random_uuid(), org_id, p_electronics_id, b_electronics_id,
    '2025-03-01', '2028-02-28', 'Bengaluru Plant Unit-2',
    'DISP-2025-EB-001', 'India',
    3999.00, 'INR', 200,
    true, true,
    admin_id, NOW()
);

RAISE NOTICE 'Created 3 activation parameter records';

-- =============================================================================
-- 5. QR Activation Tracks (pallet → box → unit hierarchy)
-- =============================================================================
INSERT INTO qr_activation_tracks (
    id, organization_id, qr_type, name, capacity,
    serial_number, qr_code_link, app_cascade_map,
    parent_id, parent_app_id, created_at
) VALUES
(
    track_pallet_id, org_id,
    'pallet', 'PLT1', 50,
    'PLT001', 'https://verify.example.com/track/PLT001',
    true, NULL, NULL, NOW()
),
(
    track_box_id, org_id,
    'box', 'BOX1', 10,
    'BOX001', 'https://verify.example.com/track/BOX001',
    true, track_pallet_id, NULL, NOW()
),
(
    track_unit_id, org_id,
    'unit', 'UNIT1', 1,
    'EB00000001', 'https://verify.example.com/track/EB00000001',
    false, track_box_id, track_pallet_id, NOW()
);

RAISE NOTICE 'Created 3 activation track records (pallet -> box -> unit)';

-- =============================================================================
-- 6. QR Credit Usage
-- =============================================================================
INSERT INTO qr_credit_usage (
    id, organization_id, block_id, quantity, used_at
) VALUES
(gen_random_uuid(), org_id, b_pharma_id,      500,  NOW() - INTERVAL '45 days'),
(gen_random_uuid(), org_id, b_fmcg_id,        1000, NOW() - INTERVAL '30 days'),
(gen_random_uuid(), org_id, b_electronics_id, 200,  NOW() - INTERVAL '15 days');

RAISE NOTICE 'Created 3 credit usage records';

-- =============================================================================
-- 7. QR Scan Events (one per scanned product item)
-- =============================================================================
INSERT INTO qr_scan_events (
    id, organization_id, product_item_id, serial_number,
    scan_timestamp, device_type, os, browser,
    ip_address, latitude, longitude,
    city, state, country, extra_data
)
SELECT
    gen_random_uuid(),
    org_id,
    pi.id,
    pi.serial_number,
    NOW() - (random() * INTERVAL '30 days'),
    (ARRAY['mobile', 'tablet', 'desktop'])[floor(random()*3+1)::int],
    (ARRAY['Android', 'iOS', 'Windows', 'macOS'])[floor(random()*4+1)::int],
    (ARRAY['Chrome', 'Safari', 'Firefox'])[floor(random()*3+1)::int],
    '103.21.' || floor(random()*255)::text || '.' || floor(random()*255)::text,
    18.9 + (random() * 10),
    72.8 + (random() * 10),
    (ARRAY['Mumbai', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad'])[floor(random()*5+1)::int],
    (ARRAY['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Telangana'])[floor(random()*5+1)::int],
    'India',
    '{"source": "qr_scan", "app_version": "2.1.0"}'::jsonb
FROM product_items pi
WHERE pi.organization_id = org_id
  AND pi.scans > 0;

RAISE NOTICE 'Created scan events for scanned items';
RAISE NOTICE '=== QR Products seed complete ===';

END $$;

-- =============================================================================
-- Verify row counts
-- =============================================================================
SELECT 'qr_products'               AS table_name, COUNT(*) AS rows FROM qr_products               WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'qr_blocks',                               COUNT(*)          FROM qr_blocks                 WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'product_items',                           COUNT(*)          FROM product_items              WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'qr_activation_parameters',               COUNT(*)          FROM qr_activation_parameters  WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'qr_activation_tracks',                   COUNT(*)          FROM qr_activation_tracks      WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'qr_credit_usage',                        COUNT(*)          FROM qr_credit_usage            WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
UNION ALL
SELECT 'qr_scan_events',                         COUNT(*)          FROM qr_scan_events             WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
