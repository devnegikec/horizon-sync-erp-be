-- =============================================================================
-- Phase 1: Verification Queries
-- Run against identity_db after import to confirm data integrity
-- Usage: psql $NEW_IDENTITY_DB -f scripts/migration/phase1_verify.sql
-- =============================================================================

\echo '============================================================'
\echo 'Phase 1 Migration Verification'
\echo '============================================================'

-- 1. Row counts
\echo ''
\echo '--- Row Counts ---'
SELECT 'organizations'         AS table_name, COUNT(*) AS rows FROM organizations
UNION ALL
SELECT 'users'                 AS table_name, COUNT(*) AS rows FROM users
UNION ALL
SELECT 'roles'                 AS table_name, COUNT(*) AS rows FROM roles
UNION ALL
SELECT 'user_organization_roles' AS table_name, COUNT(*) AS rows FROM user_organization_roles;

-- 2. Check for duplicate slugs
\echo ''
\echo '--- Duplicate Slugs (should be 0 rows) ---'
SELECT slug, COUNT(*) AS count
FROM organizations
GROUP BY slug
HAVING COUNT(*) > 1;

-- 3. Check for duplicate emails
\echo ''
\echo '--- Duplicate Emails (should be 0 rows) ---'
SELECT email, COUNT(*) AS count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- 4. Orphaned user_organization_roles (no matching user)
\echo ''
\echo '--- Orphaned user_org_roles - missing user (should be 0 rows) ---'
SELECT COUNT(*) AS orphaned_user_refs
FROM user_organization_roles uor
LEFT JOIN users u ON u.id = uor.user_id
WHERE u.id IS NULL;

-- 5. Orphaned user_organization_roles (no matching org)
\echo ''
\echo '--- Orphaned user_org_roles - missing org (should be 0 rows) ---'
SELECT COUNT(*) AS orphaned_org_refs
FROM user_organization_roles uor
LEFT JOIN organizations o ON o.id = uor.organization_id
WHERE o.id IS NULL;

-- 6. Orphaned user_organization_roles (no matching role)
\echo ''
\echo '--- Orphaned user_org_roles - missing role (should be 0 rows) ---'
SELECT COUNT(*) AS orphaned_role_refs
FROM user_organization_roles uor
LEFT JOIN roles r ON r.id = uor.role_id
WHERE r.id IS NULL;

-- 7. Users without any org assignment
\echo ''
\echo '--- Users with no org assignment (investigate these) ---'
SELECT u.email, u.status, u.created_at
FROM users u
LEFT JOIN user_organization_roles uor ON uor.user_id = u.id
WHERE uor.id IS NULL
ORDER BY u.created_at;

-- 8. Organizations without an owner
\echo ''
\echo '--- Organizations without an owner ---'
SELECT name, slug, status
FROM organizations
WHERE owner_id IS NULL;

-- 9. Role distribution
\echo ''
\echo '--- Role distribution across users ---'
SELECT r.code AS role, COUNT(uor.id) AS user_count
FROM roles r
LEFT JOIN user_organization_roles uor ON uor.role_id = r.id
GROUP BY r.code
ORDER BY user_count DESC;

-- 10. Password migration status
\echo ''
\echo '--- Password migration status ---'
SELECT
  COUNT(*) FILTER (WHERE extra_data::jsonb->>'password_migration' = 'pending_reset') AS needs_password_reset,
  COUNT(*) FILTER (WHERE extra_data::jsonb->>'password_migration' IS NULL)           AS already_has_bcrypt,
  COUNT(*)                                                                            AS total_users
FROM users;

-- 11. Sample of migrated orgs (spot check)
\echo ''
\echo '--- Sample organizations (first 5) ---'
SELECT id, name, slug, status, is_active,
       extra_data::jsonb->>'old_id' AS old_id,
       created_at
FROM organizations
ORDER BY created_at
LIMIT 5;

-- 12. Sample of migrated users (spot check)
\echo ''
\echo '--- Sample users (first 5) ---'
SELECT id, email, first_name, last_name, status, is_active,
       extra_data::jsonb->>'old_id' AS old_id,
       created_at
FROM users
ORDER BY created_at
LIMIT 5;

\echo ''
\echo '============================================================'
\echo 'Verification complete. Review any issues above.'
\echo '============================================================'
