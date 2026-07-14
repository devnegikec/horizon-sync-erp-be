-- ===========================================
-- Seed: Warehouse Work User Role + Permissions
-- ===========================================
-- Purpose: Creates the warehouse_work_user role with limited WMS permissions
--          for QR-code-only login warehouse workers. Admins can invite workers
--          using this role from the admin UI.
--
-- IDEMPOTENT — safe to run multiple times. Uses WHERE NOT EXISTS / IF NOT EXISTS.
--
-- Usage:
--   docker compose exec postgres psql -U horizon_user -d identity_db \
--       -f /path/to/seed_warehouse_work_user.sql
--
--   Or from inside the container:
--   psql -U horizon_user -d identity_db -f scripts/seed_warehouse_work_user.sql
-- ===========================================

BEGIN;

-- ──────────────────────────────────────────────────────────────────────────
-- Step 1: Add missing enum values (safe — uses IF NOT EXISTS)
-- ──────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    -- UserType: warehouse_worker
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'warehouse_worker' AND enumtypid = 'usertype'::regtype) THEN
        ALTER TYPE usertype ADD VALUE 'warehouse_worker';
    END IF;

    -- ResourceType: receiving_slip
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'receiving_slip' AND enumtypid = 'resourcetype'::regtype) THEN
        ALTER TYPE resourcetype ADD VALUE 'receiving_slip';
    END IF;

    -- ActionType: scan
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'scan' AND enumtypid = 'actiontype'::regtype) THEN
        ALTER TYPE actiontype ADD VALUE 'scan';
    END IF;
END$$;

-- ──────────────────────────────────────────────────────────────────────────
-- Step 2: Create the warehouse_work_user role for ALL existing organizations
-- ──────────────────────────────────────────────────────────────────────────

INSERT INTO roles (id, organization_id, name, code, description, is_system, is_default, is_active, hierarchy_level, created_at, updated_at)
SELECT
    gen_random_uuid(),
    org.id,
    'Warehouse Work User',
    'warehouse_work_user',
    'Limited warehouse worker — QR login only. Can scan, create/read/update receiving slips, and read/update pick lists. Cannot create pick lists, manage workers/devices, or access admin/billing.',
    true,   -- is_system
    false,  -- is_default
    true,   -- is_active
    5,      -- hierarchy_level (lowest — most restricted)
    NOW(),
    NOW()
FROM organizations org
WHERE NOT EXISTS (
    SELECT 1 FROM roles r
    WHERE r.organization_id = org.id AND r.code = 'warehouse_work_user'
);

-- ──────────────────────────────────────────────────────────────────────────
-- Step 3: Create WMS worker permissions (idempotent)
-- ──────────────────────────────────────────────────────────────────────────

-- 3a. wms.scan — QR/barcode scanning for inbound/outbound
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'wms.scan', 'WMS Scan',
       'Scan QR codes and barcodes for inbound receiving and outbound picking operations',
       'warehouse'::resourcetype, 'scan'::actiontype, 'inventory', 'WMS', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'wms.scan');

-- 3b. receiving_slip.create — Create inbound receiving slips
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'receiving_slip.create', 'Create Receiving Slip',
       'Create inbound receiving slips when goods arrive at the warehouse',
       'receiving_slip'::resourcetype, 'create'::actiontype, 'inventory', 'WMS', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'receiving_slip.create');

-- 3c. receiving_slip.read — View receiving slips
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'receiving_slip.read', 'Read Receiving Slip',
       'View inbound receiving slips and their status',
       'receiving_slip'::resourcetype, 'read'::actiontype, 'inventory', 'WMS', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'receiving_slip.read');

-- 3d. receiving_slip.update — Update receiving slips
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'receiving_slip.update', 'Update Receiving Slip',
       'Update receiving slip details (quantities, status, put-away progress)',
       'receiving_slip'::resourcetype, 'update'::actiontype, 'inventory', 'WMS', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'receiving_slip.update');

-- ──────────────────────────────────────────────────────────────────────────
-- Step 4: Assign permissions to warehouse_work_user role (for all orgs)
-- ──────────────────────────────────────────────────────────────────────────
-- Includes pick_list.read and pick_list.update which should already exist in the DB.

INSERT INTO role_permissions (id, role_id, permission_id)
SELECT
    gen_random_uuid(),
    r.id AS role_id,
    p.id AS permission_id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'warehouse_work_user'
  AND p.code IN (
      'warehouse.read',
      'wms.scan',
      'receiving_slip.create',
      'receiving_slip.read',
      'receiving_slip.update',
      'pick_list.read',
      'pick_list.update'
  )
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id = r.id AND rp.permission_id = p.id
  );

-- ──────────────────────────────────────────────────────────────────────────
-- Summary
-- ──────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
    role_count int;
    perm_count int;
    rp_count   int;
BEGIN
    SELECT COUNT(*) INTO role_count FROM roles WHERE code = 'warehouse_work_user';
    SELECT COUNT(*) INTO perm_count FROM permissions WHERE code IN (
        'wms.scan', 'receiving_slip.create', 'receiving_slip.read', 'receiving_slip.update'
    );
    SELECT COUNT(*) INTO rp_count FROM role_permissions rp
    JOIN roles r ON r.id = rp.role_id
    WHERE r.code = 'warehouse_work_user';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Seed Complete: warehouse_work_user';
    RAISE NOTICE '  Roles created:       %', role_count;
    RAISE NOTICE '  Permissions ensured: %', perm_count;
    RAISE NOTICE '  Role-perm links:     %', rp_count;
    RAISE NOTICE '========================================';
END$$;

COMMIT;
