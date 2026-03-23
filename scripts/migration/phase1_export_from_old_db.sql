-- =============================================================================
-- Phase 1: Export from Old Django QSeal DB
-- Run this against the OLD Django database
-- Usage: psql $OLD_DB -f scripts/migration/phase1_export_from_old_db.sql
-- =============================================================================

-- Export organizations (Client + Brand merged)
\copy (
  SELECT
    gen_random_uuid()::text                                          AS id,
    c.name                                                           AS name,
    lower(regexp_replace(
      regexp_replace(c.name, '[^a-zA-Z0-9\s]', '', 'g'),
      '\s+', '-', 'g'
    ))                                                               AS slug,
    c.name                                                           AS display_name,
    'business'                                                       AS organization_type,
    COALESCE(c.industry, 'general')                                  AS industry,
    COALESCE(c.domain_url, '')                                       AS domain,
    'active'                                                         AS status,
    true                                                             AS is_active,
    jsonb_build_object(
      'old_id',          c.id::text,
      'short_code',      b.short_code,
      'public_key',      b.public_key,
      'schema_name',     c.schema_name,
      'qr_credit_limit', c.qr_credit_limit,
      'qr_credit_used',  c.qr_credit_used,
      'timezone',        COALESCE(c.timezone, 'UTC'),
      'paid_until',      c.paid_until::text,
      'on_trial',        c.on_trial,
      'trial_expiry',    c.trial_expiry::text
    )::text                                                          AS extra_data,
    now()::text                                                      AS created_at,
    now()::text                                                      AS updated_at
  FROM dashboard_client c
  LEFT JOIN integration_brand b ON b.client_id = c.id
  ORDER BY c.id
) TO '/tmp/qseal_orgs_export.csv' CSV HEADER;

\echo 'Organizations exported to /tmp/qseal_orgs_export.csv'

-- Export users
\copy (
  SELECT
    gen_random_uuid()::text                                          AS id,
    u.email                                                          AS email,
    u.password                                                       AS password_hash,
    COALESCE(NULLIF(u.first_name, ''), 'Unknown')                   AS first_name,
    COALESCE(NULLIF(u.last_name, ''), 'User')                       AS last_name,
    COALESCE(u.first_name, 'Unknown') || ' ' ||
      COALESCE(u.last_name, 'User')                                  AS display_name,
    COALESCE(u.mobile, '')                                           AS phone,
    'user'                                                           AS user_type,
    CASE WHEN u.is_active THEN 'active' ELSE 'inactive' END         AS status,
    u.is_active                                                      AS is_active,
    false                                                            AS email_verified,
    jsonb_build_object(
      'old_id',    u.id::text,
      'tenant_id', u.tenant_id::text
    )::text                                                          AS extra_data,
    now()::text                                                      AS created_at,
    now()::text                                                      AS updated_at
  FROM users_user u
  WHERE u.email IS NOT NULL AND u.email != ''
  ORDER BY u.id
) TO '/tmp/qseal_users_export.csv' CSV HEADER;

\echo 'Users exported to /tmp/qseal_users_export.csv'

-- Export user-to-org mapping (needed to build user_organization_roles)
\copy (
  SELECT
    u.email                                                          AS user_email,
    c.name                                                           AS org_name,
    lower(regexp_replace(
      regexp_replace(c.name, '[^a-zA-Z0-9\s]', '', 'g'),
      '\s+', '-', 'g'
    ))                                                               AS org_slug,
    -- Map old role arrays to new role codes
    CASE
      WHEN u.is_superuser = true THEN 'system_admin'
      WHEN u.is_staff = true     THEN 'org_admin'
      ELSE                            'user'
    END                                                              AS role_code,
    u.is_active                                                      AS is_active
  FROM users_user u
  JOIN dashboard_client c ON c.id = u.tenant_id
  WHERE u.email IS NOT NULL AND u.email != ''
  ORDER BY u.id
) TO '/tmp/qseal_user_org_map.csv' CSV HEADER;

\echo 'User-org mapping exported to /tmp/qseal_user_org_map.csv'
\echo ''
\echo 'All exports complete. Files written to /tmp/'
\echo '  - /tmp/qseal_orgs_export.csv'
\echo '  - /tmp/qseal_users_export.csv'
\echo '  - /tmp/qseal_user_org_map.csv'
