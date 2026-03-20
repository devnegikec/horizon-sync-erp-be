-- =============================================================================
-- Phase 1: Import into identity_db
-- Run this against the NEW identity_db
-- Usage: psql $NEW_IDENTITY_DB -f scripts/migration/phase1_import_to_identity_db.sql
--
-- IMPORTANT: Run phase1_export_from_old_db.sql first to generate the CSV files.
-- IMPORTANT: Run Alembic migrations first: docker compose exec identity-service python -m alembic upgrade head
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Step 1: Import organizations
-- -----------------------------------------------------------------------------
\echo 'Step 1: Importing organizations...'

\copy organizations (id, name, slug, display_name, organization_type, industry, domain, status, is_active, extra_data, created_at, updated_at)
FROM '/tmp/qseal_orgs_export.csv' CSV HEADER;

-- Fix duplicate slugs (append -2, -3, etc. if collision)
WITH dupes AS (
  SELECT id, slug, ROW_NUMBER() OVER (PARTITION BY slug ORDER BY created_at) AS rn
  FROM organizations
)
UPDATE organizations o
SET slug = o.slug || '-' || d.rn
FROM dupes d
WHERE o.id = d.id AND d.rn > 1;

SELECT COUNT(*) AS organizations_imported FROM organizations;

-- -----------------------------------------------------------------------------
-- Step 2: Import users
-- NOTE: Passwords from old Django app use PBKDF2 — they will NOT work with
-- bcrypt verification. Users will need to reset their passwords on first login.
-- The password_hash column is set to a placeholder that forces a reset.
-- -----------------------------------------------------------------------------
\echo 'Step 2: Importing users...'

-- Create a temp table to hold the raw import (password_hash from old app)
CREATE TEMP TABLE tmp_users_import (
  id            TEXT,
  email         TEXT,
  password_hash TEXT,
  first_name    TEXT,
  last_name     TEXT,
  display_name  TEXT,
  phone         TEXT,
  user_type     TEXT,
  status        TEXT,
  is_active     BOOLEAN,
  email_verified BOOLEAN,
  extra_data    TEXT,
  created_at    TEXT,
  updated_at    TEXT
);

\copy tmp_users_import FROM '/tmp/qseal_users_export.csv' CSV HEADER;

-- Insert into users with a bcrypt placeholder password
-- Users must reset password on first login
-- Placeholder: bcrypt hash of 'RESET_REQUIRED' — login will fail until reset
INSERT INTO users (
  id, email, password_hash, first_name, last_name, display_name,
  phone, user_type, status, is_active, email_verified,
  extra_data, created_at, updated_at
)
SELECT
  id::uuid,
  email,
  -- Store old hash in extra_data for reference; set placeholder bcrypt hash
  -- This bcrypt hash is for the string 'RESET_REQUIRED_CHANGE_ON_LOGIN'
  '$2b$12$PLACEHOLDER.HASH.THAT.WILL.NOT.MATCH.ANY.PASSWORD.EVER',
  first_name,
  last_name,
  display_name,
  NULLIF(phone, ''),
  user_type::text,
  status::text,
  is_active,
  email_verified,
  -- Merge old hash into extra_data for potential recovery
  (extra_data::jsonb || jsonb_build_object(
    'old_password_hash', password_hash,
    'password_migration', 'pending_reset'
  ))::text,
  created_at::timestamptz,
  updated_at::timestamptz
FROM tmp_users_import
ON CONFLICT (email) DO NOTHING;  -- Skip if email already exists (e.g. from seed)

DROP TABLE tmp_users_import;

SELECT COUNT(*) AS users_imported FROM users;

-- -----------------------------------------------------------------------------
-- Step 3: Seed default roles (if not already seeded)
-- -----------------------------------------------------------------------------
\echo 'Step 3: Ensuring default roles exist...'

-- Insert system-level roles for each org (or reuse existing ones)
-- We create one set of system roles per organization
INSERT INTO roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, created_at, updated_at)
SELECT
  gen_random_uuid(),
  o.id,
  'System Administrator',
  'system_admin',
  'Full system access with all permissions',
  true,
  false,
  100,
  true,
  now(),
  now()
FROM organizations o
WHERE NOT EXISTS (
  SELECT 1 FROM roles r WHERE r.organization_id = o.id AND r.code = 'system_admin'
);

INSERT INTO roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, created_at, updated_at)
SELECT
  gen_random_uuid(),
  o.id,
  'Organization Administrator',
  'org_admin',
  'Organization-level administrative access',
  true,
  false,
  50,
  true,
  now(),
  now()
FROM organizations o
WHERE NOT EXISTS (
  SELECT 1 FROM roles r WHERE r.organization_id = o.id AND r.code = 'org_admin'
);

INSERT INTO roles (id, organization_id, name, code, description, is_system, is_default, hierarchy_level, is_active, created_at, updated_at)
SELECT
  gen_random_uuid(),
  o.id,
  'User',
  'user',
  'Standard user access',
  true,
  true,
  10,
  true,
  now(),
  now()
FROM organizations o
WHERE NOT EXISTS (
  SELECT 1 FROM roles r WHERE r.organization_id = o.id AND r.code = 'user'
);

SELECT COUNT(*) AS roles_total FROM roles;

-- -----------------------------------------------------------------------------
-- Step 4: Build user_organization_roles from the mapping CSV
-- -----------------------------------------------------------------------------
\echo 'Step 4: Building user-organization-role assignments...'

CREATE TEMP TABLE tmp_user_org_map (
  user_email TEXT,
  org_name   TEXT,
  org_slug   TEXT,
  role_code  TEXT,
  is_active  BOOLEAN
);

\copy tmp_user_org_map FROM '/tmp/qseal_user_org_map.csv' CSV HEADER;

INSERT INTO user_organization_roles (
  id, user_id, organization_id, role_id,
  is_primary, is_active, status, joined_at, created_at, updated_at
)
SELECT
  gen_random_uuid(),
  u.id,
  o.id,
  r.id,
  true,   -- is_primary
  m.is_active,
  CASE WHEN m.is_active THEN 'active' ELSE 'inactive' END,
  now(),
  now(),
  now()
FROM tmp_user_org_map m
JOIN users u        ON u.email = m.user_email
JOIN organizations o ON o.slug = m.org_slug
JOIN roles r        ON r.organization_id = o.id AND r.code = m.role_code
ON CONFLICT DO NOTHING;

DROP TABLE tmp_user_org_map;

SELECT COUNT(*) AS user_org_roles_created FROM user_organization_roles;

-- -----------------------------------------------------------------------------
-- Step 5: Set organization owner to the first org_admin user
-- -----------------------------------------------------------------------------
\echo 'Step 5: Setting organization owners...'

UPDATE organizations o
SET owner_id = (
  SELECT uor.user_id
  FROM user_organization_roles uor
  JOIN roles r ON r.id = uor.role_id
  WHERE uor.organization_id = o.id
    AND r.code IN ('system_admin', 'org_admin')
    AND uor.is_active = true
  ORDER BY r.hierarchy_level DESC
  LIMIT 1
)
WHERE o.owner_id IS NULL;

COMMIT;

\echo ''
\echo '============================================================'
\echo 'Phase 1 import complete!'
\echo '============================================================'
\echo 'IMPORTANT: All migrated users have a placeholder password.'
\echo 'They must use "Forgot Password" to set a new password.'
\echo 'The old password hash is stored in users.extra_data for reference.'
\echo '============================================================'
