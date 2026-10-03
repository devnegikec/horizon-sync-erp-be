-- =============================================================================
-- Seed test users for role & permission testing  --  BW-dev (EMPTY database)
--
-- SQL port of identity-service/scripts/seed_test_users.py, EXTENDED so it can
-- bootstrap a fresh identity database that has no organizations/roles yet.
--
-- Why a second file? scripts/seed_test_users.sql was written for the STAGING
-- database, where `master-org`, `ciphercode-tech` and the preloaded org roles
-- already exist. On a fresh DB (BW-dev) every user would be created WITHOUT a
-- role because those orgs/roles are missing.
--
-- This script:
--   1. requires the master org (`master-org`) + system-admin roles, which the
--      service creates on startup (scripts/seed_system_admin_roles.py).
--      If they are missing, start identity-service once and re-run.
--   2. creates the tenant org `ciphercode-tech` if missing
--   3. creates the 12 preloaded org roles for it with the EXACT permission sets
--      from app/core/modules.py -> PRELOADED_ORG_ROLES (single source of truth)
--   4. upserts the 8 test users and re-creates their org/role assignments
--
-- Password for every account:  Test@123
-- Idempotent: safe to run repeatedly.
--
-- Usage (the guard below requires the explicit opt-in):
--   PGOPTIONS="-c app.allow_test_seed=true" psql "$IDENTITY_DATABASE_URL" \
--       -v ON_ERROR_STOP=1 -f seed_test_users_bw_dev.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Safety guard — this script resets the credentials of well-known test
--    accounts to a public password. Refuse to run unless the caller explicitly
--    opts in, so an accidental run against a non-test database cannot hand out
--    known passwords to those e-mail addresses (CodeAnt PR #275).
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF coalesce(current_setting('app.allow_test_seed', true), '') <> 'true' THEN
        RAISE EXCEPTION
            'Refusing to seed test users: this resets known accounts to a public password. Re-run with PGOPTIONS=''-c app.allow_test_seed=true'' (or SET app.allow_test_seed = ''true''; in the same session) if this is a disposable test database.';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. Tenant organization
-- ---------------------------------------------------------------------------
INSERT INTO organizations (
    id, name, slug, display_name, description, organization_type,
    base_currency, status, is_active, created_at, updated_at
)
SELECT
    gen_random_uuid(), 'Ciphercode Tech', 'ciphercode-tech', 'Ciphercode Tech',
    'Tenant organization seeded for role/permission testing',
    'enterprise', 'USD', 'active', true, now(), now()
WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE slug = 'ciphercode-tech');

-- ---------------------------------------------------------------------------
-- 2. Preloaded org roles for the tenant org
--    (generated from app/core/modules.py PRELOADED_ORG_ROLES)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _seed_roles (
    name text, code text, description text, is_system boolean, hierarchy_level int
) ON COMMIT DROP;

INSERT INTO _seed_roles (name, code, description, is_system, hierarchy_level) VALUES
    ('Organization Owner', 'owner', 'Full access to all features. Automatically assigned to the user who created the organization.', true, 100),
    ('Administrator', 'org_admin', 'Full access to identity management plus read-only access to all business modules.', true, 80),
    ('Sales Agent', 'sales_agent', 'Full access to Sales & Orders module plus read-only Inventory.', true, 40),
    ('Procurement Officer', 'procurement_officer', 'Full access to Procurement module plus read-only Inventory.', true, 40),
    ('Accountant', 'accountant', 'Full access to Accounting module plus read-only access to Sales invoices.', true, 40),
    ('Warehouse Staff', 'warehouse_staff', 'Full access to Inventory module only.', true, 20),
    ('Viewer', 'viewer', 'Read-only access across all modules. Cannot create, edit, or delete anything.', true, 10),
    ('WMS Admin', 'wms_admin', 'Full warehouse administration — global access to all warehouses, layout, inbound, put-away, outbound, gate, ASN, dispatches, and worker/device management', false, 75),
    ('WMS Manager', 'wms_manager', 'Warehouse manager for assigned warehouse(s) — inbound, put-away, outbound, picking, and ASN coordination', false, 70),
    ('WMS Operator', 'wms_operator', 'Floor worker — dock scanning, put-away execution, picking, and gate verification', false, 50),
    ('ASN Coordinator', 'asn_coordinator', 'Manages advance stock notices (ASN) and inter-warehouse transfers — create, confirm, and track fulfillment', false, 65),
    ('Warehouse Work User', 'warehouse_work_user', 'Limited warehouse worker — QR login only. Can scan, create/read/update receiving slips, and read/update pick lists.', true, 5);

INSERT INTO roles (
    id, organization_id, name, code, description, is_system, is_default,
    hierarchy_level, is_active, created_at, updated_at
)
SELECT
    gen_random_uuid(), o.id, r.name, r.code, r.description, r.is_system, false,
    r.hierarchy_level, true, now(), now()
FROM _seed_roles r
CROSS JOIN organizations o
WHERE o.slug = 'ciphercode-tech'
  AND NOT EXISTS (
      SELECT 1 FROM roles x WHERE x.organization_id = o.id AND x.code = r.code
  );

-- ---------------------------------------------------------------------------
-- 3. Role -> permission links
-- ---------------------------------------------------------------------------
-- `owner` carries the wildcard "*.*", which is not a permission row, so it is
-- granted every permission in the catalogue instead.
INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), r.id, p.id
FROM roles r
JOIN organizations o ON o.id = r.organization_id AND o.slug = 'ciphercode-tech'
CROSS JOIN permissions p
WHERE r.code = 'owner'
  AND NOT EXISTS (
      SELECT 1 FROM role_permissions rp
      WHERE rp.role_id = r.id AND rp.permission_id = p.id
  );

CREATE TEMP TABLE _seed_role_perms (role_code text, perm_code text) ON COMMIT DROP;

INSERT INTO _seed_role_perms (role_code, perm_code) VALUES
    ('org_admin', 'asn_order.read'),
    ('org_admin', 'batch.read'),
    ('org_admin', 'charge_template.read'),
    ('org_admin', 'chart_of_account.read'),
    ('org_admin', 'currency.read'),
    ('org_admin', 'customer.read'),
    ('org_admin', 'exchange_rate.read'),
    ('org_admin', 'inbound_exception.read'),
    ('org_admin', 'invitation.create'),
    ('org_admin', 'invoice.read'),
    ('org_admin', 'item.read'),
    ('org_admin', 'item_group.read'),
    ('org_admin', 'journal_entry.read'),
    ('org_admin', 'org.read'),
    ('org_admin', 'org.update'),
    ('org_admin', 'payment.read'),
    ('org_admin', 'pick_list.read'),
    ('org_admin', 'purchase_order.read'),
    ('org_admin', 'put_away_rule.read'),
    ('org_admin', 'qseal.read'),
    ('org_admin', 'receiving_slip.read'),
    ('org_admin', 'return.read'),
    ('org_admin', 'role.create'),
    ('org_admin', 'role.delete'),
    ('org_admin', 'role.manage'),
    ('org_admin', 'role.read'),
    ('org_admin', 'role.update'),
    ('org_admin', 'sales_order.read'),
    ('org_admin', 'serial.read'),
    ('org_admin', 'stock_entry.read'),
    ('org_admin', 'stock_level.read'),
    ('org_admin', 'stock_reconciliation.read'),
    ('org_admin', 'stock_settings.read'),
    ('org_admin', 'supplier.read'),
    ('org_admin', 'user.create'),
    ('org_admin', 'user.delete'),
    ('org_admin', 'user.invite'),
    ('org_admin', 'user.manage'),
    ('org_admin', 'user.read'),
    ('org_admin', 'user.update'),
    ('org_admin', 'warehouse.read'),
    ('sales_agent', 'asn_order.read'),
    ('sales_agent', 'batch.read'),
    ('sales_agent', 'customer.create'),
    ('sales_agent', 'customer.delete'),
    ('sales_agent', 'customer.read'),
    ('sales_agent', 'customer.update'),
    ('sales_agent', 'inbound_exception.read'),
    ('sales_agent', 'invoice.create'),
    ('sales_agent', 'invoice.read'),
    ('sales_agent', 'invoice.update'),
    ('sales_agent', 'item.read'),
    ('sales_agent', 'item_group.read'),
    ('sales_agent', 'pick_list.read'),
    ('sales_agent', 'put_away_rule.read'),
    ('sales_agent', 'qseal.read'),
    ('sales_agent', 'receiving_slip.read'),
    ('sales_agent', 'return.read'),
    ('sales_agent', 'sales_order.create'),
    ('sales_agent', 'sales_order.delete'),
    ('sales_agent', 'sales_order.read'),
    ('sales_agent', 'sales_order.update'),
    ('sales_agent', 'serial.read'),
    ('sales_agent', 'stock_entry.read'),
    ('sales_agent', 'stock_level.read'),
    ('sales_agent', 'stock_reconciliation.read'),
    ('sales_agent', 'stock_settings.read'),
    ('sales_agent', 'warehouse.read'),
    ('procurement_officer', 'asn_order.read'),
    ('procurement_officer', 'batch.read'),
    ('procurement_officer', 'inbound_exception.read'),
    ('procurement_officer', 'item.read'),
    ('procurement_officer', 'item_group.read'),
    ('procurement_officer', 'pick_list.read'),
    ('procurement_officer', 'purchase_order.create'),
    ('procurement_officer', 'purchase_order.delete'),
    ('procurement_officer', 'purchase_order.read'),
    ('procurement_officer', 'purchase_order.update'),
    ('procurement_officer', 'put_away_rule.read'),
    ('procurement_officer', 'qseal.read'),
    ('procurement_officer', 'receiving_slip.read'),
    ('procurement_officer', 'return.read'),
    ('procurement_officer', 'serial.read'),
    ('procurement_officer', 'stock_entry.read'),
    ('procurement_officer', 'stock_level.read'),
    ('procurement_officer', 'stock_reconciliation.read'),
    ('procurement_officer', 'stock_settings.read'),
    ('procurement_officer', 'supplier.create'),
    ('procurement_officer', 'supplier.delete'),
    ('procurement_officer', 'supplier.read'),
    ('procurement_officer', 'supplier.update'),
    ('procurement_officer', 'warehouse.read'),
    ('accountant', 'charge_template.create'),
    ('accountant', 'charge_template.delete'),
    ('accountant', 'charge_template.read'),
    ('accountant', 'charge_template.update'),
    ('accountant', 'chart_of_account.create'),
    ('accountant', 'chart_of_account.delete'),
    ('accountant', 'chart_of_account.manage'),
    ('accountant', 'chart_of_account.read'),
    ('accountant', 'chart_of_account.update'),
    ('accountant', 'currency.create'),
    ('accountant', 'currency.delete'),
    ('accountant', 'currency.read'),
    ('accountant', 'currency.update'),
    ('accountant', 'exchange_rate.create'),
    ('accountant', 'exchange_rate.delete'),
    ('accountant', 'exchange_rate.read'),
    ('accountant', 'exchange_rate.update'),
    ('accountant', 'invoice.read'),
    ('accountant', 'journal_entry.create'),
    ('accountant', 'journal_entry.read'),
    ('accountant', 'journal_entry.update'),
    ('accountant', 'payment.create'),
    ('accountant', 'payment.read'),
    ('accountant', 'payment.update'),
    ('warehouse_staff', 'asn_order.create'),
    ('warehouse_staff', 'asn_order.delete'),
    ('warehouse_staff', 'asn_order.manage'),
    ('warehouse_staff', 'asn_order.read'),
    ('warehouse_staff', 'asn_order.update'),
    ('warehouse_staff', 'batch.delete'),
    ('warehouse_staff', 'batch.manage'),
    ('warehouse_staff', 'batch.read'),
    ('warehouse_staff', 'batch.update'),
    ('warehouse_staff', 'inbound_exception.create'),
    ('warehouse_staff', 'inbound_exception.dispose'),
    ('warehouse_staff', 'inbound_exception.read'),
    ('warehouse_staff', 'item.create'),
    ('warehouse_staff', 'item.delete'),
    ('warehouse_staff', 'item.read'),
    ('warehouse_staff', 'item.update'),
    ('warehouse_staff', 'item_group.create'),
    ('warehouse_staff', 'item_group.delete'),
    ('warehouse_staff', 'item_group.manage'),
    ('warehouse_staff', 'item_group.read'),
    ('warehouse_staff', 'item_group.update'),
    ('warehouse_staff', 'pick_list.create'),
    ('warehouse_staff', 'pick_list.delete'),
    ('warehouse_staff', 'pick_list.manage'),
    ('warehouse_staff', 'pick_list.read'),
    ('warehouse_staff', 'pick_list.update'),
    ('warehouse_staff', 'put_away_rule.create'),
    ('warehouse_staff', 'put_away_rule.delete'),
    ('warehouse_staff', 'put_away_rule.read'),
    ('warehouse_staff', 'put_away_rule.update'),
    ('warehouse_staff', 'qseal.create'),
    ('warehouse_staff', 'qseal.delete'),
    ('warehouse_staff', 'qseal.manage'),
    ('warehouse_staff', 'qseal.read'),
    ('warehouse_staff', 'qseal.update'),
    ('warehouse_staff', 'receiving_slip.create'),
    ('warehouse_staff', 'receiving_slip.read'),
    ('warehouse_staff', 'receiving_slip.update'),
    ('warehouse_staff', 'return.approve'),
    ('warehouse_staff', 'return.classify'),
    ('warehouse_staff', 'return.dispose'),
    ('warehouse_staff', 'return.read'),
    ('warehouse_staff', 'return.receive'),
    ('warehouse_staff', 'return.register'),
    ('warehouse_staff', 'serial.create'),
    ('warehouse_staff', 'serial.delete'),
    ('warehouse_staff', 'serial.manage'),
    ('warehouse_staff', 'serial.read'),
    ('warehouse_staff', 'serial.update'),
    ('warehouse_staff', 'stock_entry.create'),
    ('warehouse_staff', 'stock_entry.delete'),
    ('warehouse_staff', 'stock_entry.manage'),
    ('warehouse_staff', 'stock_entry.read'),
    ('warehouse_staff', 'stock_entry.update'),
    ('warehouse_staff', 'stock_level.create'),
    ('warehouse_staff', 'stock_level.read'),
    ('warehouse_staff', 'stock_level.update'),
    ('warehouse_staff', 'stock_reconciliation.create'),
    ('warehouse_staff', 'stock_reconciliation.delete'),
    ('warehouse_staff', 'stock_reconciliation.read'),
    ('warehouse_staff', 'stock_reconciliation.update'),
    ('warehouse_staff', 'stock_settings.read'),
    ('warehouse_staff', 'stock_settings.update'),
    ('warehouse_staff', 'warehouse.create'),
    ('warehouse_staff', 'warehouse.delete'),
    ('warehouse_staff', 'warehouse.manage'),
    ('warehouse_staff', 'warehouse.read'),
    ('warehouse_staff', 'warehouse.update'),
    ('warehouse_staff', 'wms.scan'),
    ('viewer', 'asn_order.read'),
    ('viewer', 'batch.read'),
    ('viewer', 'charge_template.read'),
    ('viewer', 'chart_of_account.read'),
    ('viewer', 'currency.read'),
    ('viewer', 'customer.read'),
    ('viewer', 'exchange_rate.read'),
    ('viewer', 'inbound_exception.read'),
    ('viewer', 'invoice.read'),
    ('viewer', 'item.read'),
    ('viewer', 'item_group.read'),
    ('viewer', 'journal_entry.read'),
    ('viewer', 'payment.read'),
    ('viewer', 'pick_list.read'),
    ('viewer', 'purchase_order.read'),
    ('viewer', 'put_away_rule.read'),
    ('viewer', 'qseal.read'),
    ('viewer', 'receiving_slip.read'),
    ('viewer', 'return.read'),
    ('viewer', 'sales_order.read'),
    ('viewer', 'serial.read'),
    ('viewer', 'stock_entry.read'),
    ('viewer', 'stock_level.read'),
    ('viewer', 'stock_reconciliation.read'),
    ('viewer', 'stock_settings.read'),
    ('viewer', 'supplier.read'),
    ('viewer', 'warehouse.read'),
    ('wms_admin', 'asn_order.create'),
    ('wms_admin', 'asn_order.delete'),
    ('wms_admin', 'asn_order.manage'),
    ('wms_admin', 'asn_order.read'),
    ('wms_admin', 'asn_order.update'),
    ('wms_admin', 'batch.read'),
    ('wms_admin', 'inbound_exception.create'),
    ('wms_admin', 'inbound_exception.dispose'),
    ('wms_admin', 'inbound_exception.read'),
    ('wms_admin', 'item.read'),
    ('wms_admin', 'pick_list.create'),
    ('wms_admin', 'pick_list.delete'),
    ('wms_admin', 'pick_list.manage'),
    ('wms_admin', 'pick_list.read'),
    ('wms_admin', 'pick_list.update'),
    ('wms_admin', 'serial.read'),
    ('wms_admin', 'stock_entry.create'),
    ('wms_admin', 'stock_entry.delete'),
    ('wms_admin', 'stock_entry.manage'),
    ('wms_admin', 'stock_entry.read'),
    ('wms_admin', 'stock_entry.update'),
    ('wms_admin', 'warehouse.create'),
    ('wms_admin', 'warehouse.delete'),
    ('wms_admin', 'warehouse.manage'),
    ('wms_admin', 'warehouse.read'),
    ('wms_admin', 'warehouse.update'),
    ('wms_manager', 'asn_order.create'),
    ('wms_manager', 'asn_order.delete'),
    ('wms_manager', 'asn_order.manage'),
    ('wms_manager', 'asn_order.read'),
    ('wms_manager', 'asn_order.update'),
    ('wms_manager', 'batch.read'),
    ('wms_manager', 'inbound_exception.create'),
    ('wms_manager', 'inbound_exception.dispose'),
    ('wms_manager', 'inbound_exception.read'),
    ('wms_manager', 'item.read'),
    ('wms_manager', 'pick_list.create'),
    ('wms_manager', 'pick_list.delete'),
    ('wms_manager', 'pick_list.manage'),
    ('wms_manager', 'pick_list.read'),
    ('wms_manager', 'pick_list.update'),
    ('wms_manager', 'serial.read'),
    ('wms_manager', 'stock_entry.create'),
    ('wms_manager', 'stock_entry.delete'),
    ('wms_manager', 'stock_entry.manage'),
    ('wms_manager', 'stock_entry.read'),
    ('wms_manager', 'stock_entry.update'),
    ('wms_manager', 'warehouse.manage'),
    ('wms_manager', 'warehouse.read'),
    ('wms_manager', 'warehouse.update'),
    ('wms_operator', 'asn_order.read'),
    ('wms_operator', 'batch.read'),
    ('wms_operator', 'inbound_exception.create'),
    ('wms_operator', 'inbound_exception.read'),
    ('wms_operator', 'item.read'),
    ('wms_operator', 'pick_list.read'),
    ('wms_operator', 'pick_list.update'),
    ('wms_operator', 'receiving_slip.create'),
    ('wms_operator', 'receiving_slip.read'),
    ('wms_operator', 'receiving_slip.update'),
    ('wms_operator', 'serial.read'),
    ('wms_operator', 'stock_entry.create'),
    ('wms_operator', 'stock_entry.read'),
    ('wms_operator', 'warehouse.read'),
    ('wms_operator', 'warehouse.update'),
    ('wms_operator', 'wms.scan'),
    ('asn_coordinator', 'asn_order.create'),
    ('asn_coordinator', 'asn_order.delete'),
    ('asn_coordinator', 'asn_order.manage'),
    ('asn_coordinator', 'asn_order.read'),
    ('asn_coordinator', 'asn_order.update'),
    ('asn_coordinator', 'item.read'),
    ('asn_coordinator', 'pick_list.read'),
    ('asn_coordinator', 'stock_entry.read'),
    ('asn_coordinator', 'warehouse.read'),
    ('warehouse_work_user', 'asn_order.read'),
    ('warehouse_work_user', 'inbound_exception.create'),
    ('warehouse_work_user', 'inbound_exception.read'),
    ('warehouse_work_user', 'pick_list.read'),
    ('warehouse_work_user', 'pick_list.update'),
    ('warehouse_work_user', 'receiving_slip.create'),
    ('warehouse_work_user', 'receiving_slip.read'),
    ('warehouse_work_user', 'receiving_slip.update'),
    ('warehouse_work_user', 'stock_entry.create'),
    ('warehouse_work_user', 'stock_entry.read'),
    ('warehouse_work_user', 'warehouse.read'),
    ('warehouse_work_user', 'wms.scan');

INSERT INTO role_permissions (id, role_id, permission_id)
SELECT gen_random_uuid(), r.id, p.id
FROM _seed_role_perms m
JOIN organizations o ON o.slug = 'ciphercode-tech'
JOIN roles r ON r.organization_id = o.id AND r.code = m.role_code
JOIN permissions p ON p.code = m.perm_code
WHERE NOT EXISTS (
    SELECT 1 FROM role_permissions rp
    WHERE rp.role_id = r.id AND rp.permission_id = p.id
);

-- ---------------------------------------------------------------------------
-- 4. The test users
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _seed_users (
    email text, login_username text, first_name text, last_name text,
    user_type usertype, org_slug text, role_code text
) ON COMMIT DROP;

INSERT INTO _seed_users
    (email, login_username, first_name, last_name, user_type, org_slug, role_code)
VALUES
    ('test.sysadmin@horizonsync.com', NULL, 'Test', 'SysAdmin', 'system_admin', 'master-org', 'super_admin'),
    ('test.orgadmin@horizonsync.com', NULL, 'Test', 'OrgAdmin', 'organization_admin', 'ciphercode-tech', 'owner'),
    ('test.user@horizonsync.com', NULL, 'Test', 'User', 'user', 'ciphercode-tech', 'sales_agent'),
    ('test.viewer@horizonsync.com', NULL, 'Test', 'Viewer', 'user', 'ciphercode-tech', 'viewer'),
    ('test.accountant@horizonsync.com', NULL, 'Test', 'Accountant', 'user', 'ciphercode-tech', 'accountant'),
    ('test.wmsmanager@horizonsync.com', NULL, 'Test', 'WmsManager', 'user', 'ciphercode-tech', 'wms_manager'),
    ('test.guest@horizonsync.com', NULL, 'Test', 'Guest', 'guest', 'ciphercode-tech', 'viewer'),
    ('test.worker@horizonsync.com', 'test.worker', 'Test', 'Worker', 'warehouse_worker', 'ciphercode-tech', 'warehouse_work_user');

-- password_hash is one bcrypt hash of 'Test@123' reused for every row (faithful
-- port of the Python seed, which hashed once with bcrypt.gensalt()).
-- login_password is intentionally PLAINTEXT: worker/handheld credential login
-- compares it directly, and only worker rows get it.
INSERT INTO users (
    id, email, password_hash, first_name, last_name, display_name,
    user_type, status, is_active, email_verified, email_verified_at,
    login_username, login_password, created_at, updated_at
)
SELECT
    gen_random_uuid(),
    s.email,
    '$2b$12$uX3z6Rfn4R8EOJuHGHCJWu5wjcmCbwrpioB5BlPd56P5yiG84sPw.',
    s.first_name,
    s.last_name,
    s.first_name || ' ' || s.last_name,
    s.user_type,
    'active',
    true,
    true,
    now(),
    s.login_username,
    CASE WHEN s.user_type = 'warehouse_worker'::usertype THEN 'Test@123' END,
    now(),
    now()
FROM _seed_users s
ON CONFLICT (email) DO UPDATE SET
    password_hash     = EXCLUDED.password_hash,
    first_name        = EXCLUDED.first_name,
    last_name         = EXCLUDED.last_name,
    display_name      = EXCLUDED.display_name,
    user_type         = EXCLUDED.user_type,
    status            = 'active',
    is_active         = true,
    email_verified    = true,
    email_verified_at = EXCLUDED.email_verified_at,
    login_username    = EXCLUDED.login_username,
    login_password    = EXCLUDED.login_password,
    updated_at        = now();

-- ---------------------------------------------------------------------------
-- 5. Organization / role assignments (delete + re-create, like the Python seed)
-- ---------------------------------------------------------------------------
DELETE FROM user_organization_roles uor
USING users u, _seed_users s
WHERE uor.user_id = u.id AND u.email = s.email;

INSERT INTO user_organization_roles (
    id, user_id, organization_id, role_id, is_primary, is_active, status,
    joined_at, created_at, updated_at
)
SELECT
    gen_random_uuid(), u.id, o.id, r.id, true, true, 'active', now(), now(), now()
FROM _seed_users s
JOIN users         u ON u.email = s.email
JOIN organizations o ON o.slug  = s.org_slug
JOIN roles         r ON r.organization_id = o.id AND r.code = s.role_code;

-- ---------------------------------------------------------------------------
-- 6. Report anything unresolved (a user with no role can still be created)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    rec record;
    unresolved int := 0;
BEGIN
    FOR rec IN
        SELECT s.email, s.org_slug, s.role_code,
               (o.id IS NOT NULL) AS org_ok,
               (r.id IS NOT NULL) AS role_ok
        FROM _seed_users s
        LEFT JOIN organizations o ON o.slug = s.org_slug
        LEFT JOIN roles r ON r.organization_id = o.id AND r.code = s.role_code
        ORDER BY s.email
    LOOP
        IF rec.org_ok AND rec.role_ok THEN
            RAISE NOTICE 'OK      %  ->  % / %', rec.email, rec.org_slug, rec.role_code;
        ELSE
            unresolved := unresolved + 1;
            RAISE WARNING 'MISSING %  ->  org % (found=%) role % (found=%)',
                rec.email, rec.org_slug, rec.org_ok, rec.role_code, rec.role_ok;
        END IF;
    END LOOP;
    IF unresolved > 0 THEN
        RAISE WARNING '% user(s) have NO role assignment', unresolved;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 7. Summary
-- ---------------------------------------------------------------------------
SELECT u.email,
       u.user_type,
       u.status,
       o.slug AS org,
       r.code AS role,
       (SELECT count(*) FROM role_permissions rp WHERE rp.role_id = r.id) AS role_perms
FROM _seed_users s
JOIN users u ON u.email = s.email
LEFT JOIN user_organization_roles uor ON uor.user_id = u.id AND uor.is_active
LEFT JOIN organizations o ON o.id = uor.organization_id
LEFT JOIN roles r ON r.id = uor.role_id
ORDER BY u.user_type::text, u.email;

COMMIT;
