-- =============================================================================
-- Seed test users for role & permission testing
--
-- SQL port of identity-service/scripts/seed_test_users.py
--
-- Creates one active user per `usertype` value, plus extra `user`-type accounts
-- with distinct roles. Every account shares the password:  Test@123
--
-- Idempotent: users are upserted by email, and their organization/role
-- assignments are deleted and re-created on every run.
--
-- Usage:
--   psql "$IDENTITY_DATABASE_URL" -v ON_ERROR_STOP=1 -f seed_test_users.sql
--
-- -----------------------------------------------------------------------------
-- PREREQUISITES -- read before running
-- -----------------------------------------------------------------------------
-- 1. Each `org_slug` below must exist in `organizations`.
-- 2. Each `role_code` must exist in `roles` FOR THAT SAME ORGANIZATION. Roles in
--    this schema are ORG-SCOPED (`roles.organization_id`), not global -- e.g.
--    `super_admin` belongs to master-org, NOT to a tenant org.
-- 3. A user whose org or role cannot be resolved is STILL CREATED, but gets no
--    role assignment (a WARNING is raised). Run the PRE-FLIGHT query at the
--    bottom first if you want to check up front.
--
-- The org slugs below are the STAGING identity DB's real values:
--     master-org       -> system roles (super_admin, system_*)
--     ciphercode-tech  -> tenant roles (owner, viewer, sales_agent, ...)
--
-- NOTE: the original Python script used `master-organization` / `ttk-prestige` /
-- `testorg1`, none of which exist in the staging DB. If you run this against a
-- different database, change the `org_slug` column values in the _seed_users
-- INSERT below to match that database's organizations.slug values.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. The user list  (email, login_username, first, last, user_type, org, role)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _seed_users (
    email          text,
    login_username text,
    first_name     text,
    last_name      text,
    user_type      usertype,
    org_slug       text,
    role_code      text
) ON COMMIT DROP;

INSERT INTO _seed_users
    (email, login_username, first_name, last_name, user_type, org_slug, role_code)
VALUES
    -- Platform admin (cross-organization)
    ('test.sysadmin@horizonsync.com',   NULL,          'Test', 'SysAdmin',   'system_admin',       'master-org',      'super_admin'),
    -- Organization owner (tenant-scoped)
    ('test.orgadmin@horizonsync.com',   NULL,          'Test', 'OrgAdmin',   'organization_admin', 'ciphercode-tech', 'owner'),
    -- Regular users with distinct roles (role/permission testing)
    ('test.user@horizonsync.com',       NULL,          'Test', 'User',       'user',               'ciphercode-tech', 'sales_agent'),
    ('test.viewer@horizonsync.com',     NULL,          'Test', 'Viewer',     'user',               'ciphercode-tech', 'viewer'),
    ('test.accountant@horizonsync.com', NULL,          'Test', 'Accountant', 'user',               'ciphercode-tech', 'accountant'),
    ('test.wmsmanager@horizonsync.com', NULL,          'Test', 'WmsManager', 'user',               'ciphercode-tech', 'wms_manager'),
    -- Guest
    ('test.guest@horizonsync.com',      NULL,          'Test', 'Guest',      'guest',              'ciphercode-tech', 'viewer'),
    -- Warehouse worker (handheld / PDA login)
    ('test.worker@horizonsync.com',     'test.worker', 'Test', 'Worker',     'warehouse_worker',   'ciphercode-tech', 'warehouse_work_user');

-- ---------------------------------------------------------------------------
-- 2. Upsert the users
-- ---------------------------------------------------------------------------
-- password_hash is a bcrypt hash of 'Test@123' (cost 12). The original Python
-- seed computed ONE hash with bcrypt.gensalt() and reused it for every user, so
-- a single literal here is a faithful port. Regenerate it with:
--   python3 -c "import bcrypt;print(bcrypt.hashpw(b'Test@123',bcrypt.gensalt()).decode())"
-- (or, if you install pgcrypto: crypt('Test@123', gen_salt('bf', 12)))
--
-- login_password is intentionally PLAINTEXT: the worker/handheld credential
-- login compares it directly. Only worker rows get it, matching the original.
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
    'active'::userstatus,
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
    status            = 'active'::userstatus,
    is_active         = true,
    email_verified    = true,
    email_verified_at = EXCLUDED.email_verified_at,
    login_username    = EXCLUDED.login_username,
    login_password    = EXCLUDED.login_password,
    updated_at        = now();

-- ---------------------------------------------------------------------------
-- 3. Re-create the organization / role assignments
-- ---------------------------------------------------------------------------
-- Drop ALL existing assignments for these users first, so a revoked role does
-- not linger (mirrors DELETE FROM user_organization_roles WHERE user_id = ...).
DELETE FROM user_organization_roles uor
USING users u, _seed_users s
WHERE uor.user_id = u.id
  AND u.email = s.email;

INSERT INTO user_organization_roles (
    id, user_id, organization_id, role_id, is_primary, is_active, status,
    joined_at, created_at, updated_at
)
SELECT
    gen_random_uuid(),
    u.id,
    o.id,
    r.id,
    true,
    true,
    'active',
    now(),
    now(),
    now()
FROM _seed_users s
JOIN users         u ON u.email = s.email
JOIN organizations o ON o.slug  = s.org_slug
JOIN roles         r ON r.organization_id = o.id
                    AND r.code = s.role_code;

-- ---------------------------------------------------------------------------
-- 4. Report unresolved org/role references (they silently get no role)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    rec        record;
    unresolved int := 0;
BEGIN
    FOR rec IN
        SELECT s.email, s.org_slug, s.role_code,
               (o.id IS NOT NULL) AS org_ok,
               (r.id IS NOT NULL) AS role_ok
        FROM _seed_users s
        LEFT JOIN organizations o ON o.slug = s.org_slug
        LEFT JOIN roles         r ON r.organization_id = o.id
                                 AND r.code = s.role_code
        ORDER BY s.email
    LOOP
        IF rec.org_ok AND rec.role_ok THEN
            RAISE NOTICE 'OK      %  ->  % / %', rec.email, rec.org_slug, rec.role_code;
        ELSE
            unresolved := unresolved + 1;
            RAISE WARNING 'MISSING %  ->  org %  (found=%)  role %  (found=%)',
                rec.email, rec.org_slug, rec.org_ok, rec.role_code, rec.role_ok;
        END IF;
    END LOOP;

    IF unresolved > 0 THEN
        RAISE WARNING '% user(s) were created/updated WITHOUT a role assignment',
            unresolved;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 5. Summary
-- ---------------------------------------------------------------------------
SELECT u.email,
       u.user_type,
       u.status,
       o.slug AS org,
       r.code AS role
FROM _seed_users s
JOIN users u          ON u.email = s.email
LEFT JOIN user_organization_roles uor ON uor.user_id = u.id AND uor.is_active
LEFT JOIN organizations o ON o.id = uor.organization_id
LEFT JOIN roles         r ON r.id = uor.role_id
ORDER BY u.user_type::text, u.email;

COMMIT;

-- =============================================================================
-- PRE-FLIGHT (optional) -- run this FIRST if any org/role might be missing.
-- It resolves the same lookups without writing anything.
-- =============================================================================
-- \set ON_ERROR_STOP on
-- WITH seed(email, org_slug, role_code) AS (VALUES
--     ('test.sysadmin@horizonsync.com',   'master-org',      'super_admin'),
--     ('test.orgadmin@horizonsync.com',   'ciphercode-tech', 'owner'),
--     ('test.user@horizonsync.com',       'ciphercode-tech', 'sales_agent'),
--     ('test.viewer@horizonsync.com',     'ciphercode-tech', 'viewer'),
--     ('test.accountant@horizonsync.com', 'ciphercode-tech', 'accountant'),
--     ('test.wmsmanager@horizonsync.com', 'ciphercode-tech', 'wms_manager'),
--     ('test.guest@horizonsync.com',      'ciphercode-tech', 'viewer'),
--     ('test.worker@horizonsync.com',     'ciphercode-tech', 'warehouse_work_user')
-- )
-- SELECT s.email, s.org_slug, o.id AS org_id, s.role_code, r.id AS role_id
-- FROM seed s
-- LEFT JOIN organizations o ON o.slug = s.org_slug
-- LEFT JOIN roles         r ON r.organization_id = o.id AND r.code = s.role_code
-- ORDER BY s.email;
--
-- Quick reference -- which roles live in which org (staging):
--   master-org      : super_admin, system_billing_manager, system_org_manager,
--                     system_reports_viewer, system_user_manager
--   ciphercode-tech : accountant, asn_coordinator, org_admin, organization_admin,
--                     owner, procurement_officer, sales_agent, viewer,
--                     warehouse_staff, warehouse_work_user, wms_admin,
--                     wms_manager, wms_operator
