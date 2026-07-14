# Database Migration Guide: Old Django QSeal App → New FastAPI Services

## Overview

This guide covers migrating data from the old Django-based QSeal app to the new
FastAPI microservices architecture:

- **identity-service** → `identity_db` (Auth, Users, Organizations)
- **core-service** → `core_db` (Inventory, Orders, Billing, Sourcing)

The old Django app used a schema-per-tenant model. The new system uses a flat
`organization_id` column on every table for multi-tenancy.

---

## Architecture Mapping

```
Old Django App (single DB, schema-per-tenant)
    ├── dashboard app  → Client model
    ├── integration app → Brand, Product, Order, Campaign, Lead, etc.
    ├── certgen app    → Coupon, ExternalCoupon, etc.
    └── users app      → User model

New FastAPI Services (separate DBs)
    ├── identity_db    → organizations, users, roles, permissions
    └── core_db        → items, warehouses, customers, suppliers,
                         invoices, payments, orders, stock, etc.
```

> **Important**: The new core-service is an ERP system (inventory, orders, billing).
> It does NOT map 1:1 to the old QSeal app. The old app was a QR/campaign platform.
> Only `Client → organizations` and `User → users` have direct equivalents.
> All other old-app tables (campaigns, coupons, QR blocks, etc.) are **not yet
> implemented** in the new services and would need new modules if required.

---

## Part 1: Identity Service Migration (identity_db)

### 1.1 Old → New Table Mapping

| Old Django Model | Old Table (approx.)        | New Table           | Notes                                                 |
| ---------------- | -------------------------- | ------------------- | ----------------------------------------------------- |
| `Client`         | `dashboard_client`         | `organizations`     | Merge Brand fields in                                 |
| `Brand`          | `integration_brand`        | `organizations`     | `public_key`, `private_key`, `short_code` move to org |
| `User`           | `auth_user` / `users_user` | `users`             | Schema changes (see below)                            |
| `OTP`            | `integration_otp`          | `otp_verifications` | **Not yet in identity-service**                       |

### 1.2 organizations Table

**Old `Client` fields → New `organizations` columns:**

| Old Field                  | New Column                       | Notes                                        |
| -------------------------- | -------------------------------- | -------------------------------------------- |
| `id`                       | `id` (UUID)                      | Old likely integer PK — generate new UUIDs   |
| `name`                     | `name`                           | Direct map                                   |
| `short_code` (from Brand)  | `extra_data->>'short_code'`      | Store in JSONB or add column                 |
| `public_key` (from Brand)  | `extra_data->>'public_key'`      | Store in JSONB                               |
| `private_key` (from Brand) | `extra_data->>'private_key'`     | Store in JSONB (encrypted)                   |
| `schema_name`              | `extra_data->>'schema_name'`     | Store in JSONB                               |
| `domain_url`               | `domain`                         | Direct map                                   |
| `industry`                 | `industry`                       | Direct map                                   |
| `paid_until`               | `extra_data->>'paid_until'`      | Store in JSONB                               |
| `on_trial`                 | `extra_data->>'on_trial'`        | Store in JSONB                               |
| `trial_expiry`             | `extra_data->>'trial_expiry'`    | Store in JSONB                               |
| `status`                   | `status`                         | Map `'ACTIVE'` → `'active'` (lowercase enum) |
| `timezone`                 | `extra_data->>'timezone'`        | Store in JSONB                               |
| `qr_credit_limit`          | `extra_data->>'qr_credit_limit'` | Store in JSONB                               |
| `qr_credit_used`           | `extra_data->>'qr_credit_used'`  | Store in JSONB                               |

**New required columns with no old equivalent (set defaults):**

- `slug` — generate from `name` (e.g., `slugify(name)`)
- `organization_type` — default `'business'`
- `base_currency` — default `'USD'` or map from old data
- `is_active` — default `true`

### 1.3 users Table

**Old `User` fields → New `users` columns:**

| Old Field           | New Column                                    | Notes                                      |
| ------------------- | --------------------------------------------- | ------------------------------------------ |
| `id`                | `id` (UUID)                                   | Old likely integer PK — generate new UUIDs |
| `email`             | `email`                                       | Direct map                                 |
| `password` (hashed) | `password_hash`                               | Direct map (same bcrypt format)            |
| `first_name`        | `first_name`                                  | Direct map                                 |
| `last_name`         | `last_name`                                   | Direct map                                 |
| `mobile`            | `phone`                                       | Direct map                                 |
| `is_active`         | `is_active`                                   | Direct map                                 |
| `roles` (TEXT[])    | via `user_organization_roles`                 | Normalize into role junction table         |
| `tenant_id`         | via `user_organization_roles.organization_id` | Link user to org via junction              |

**New required columns with no old equivalent:**

- `user_type` — default `'user'`
- `status` — default `'active'`
- `email_verified` — default `false` (or `true` if old app verified emails)

### 1.4 Migration SQL for identity_db

```sql
-- Step 1: Migrate organizations (from old Client + Brand tables)
-- Run on old DB first to export, then import to identity_db

-- Export from old DB:
-- COPY (
--   SELECT
--     gen_random_uuid() as id,
--     c.name,
--     lower(regexp_replace(c.name, '[^a-zA-Z0-9]', '-', 'g')) as slug,
--     c.name as display_name,
--     'business' as organization_type,
--     c.industry,
--     c.domain_url as domain,
--     'active' as status,
--     true as is_active,
--     jsonb_build_object(
--       'short_code', b.short_code,
--       'public_key', b.public_key,
--       'schema_name', c.schema_name,
--       'qr_credit_limit', c.qr_credit_limit,
--       'timezone', c.timezone
--     ) as extra_data,
--     now() as created_at,
--     now() as updated_at
--   FROM dashboard_client c
--   LEFT JOIN integration_brand b ON b.client_id = c.id
-- ) TO '/tmp/organizations.csv' CSV HEADER;

-- Step 2: Migrate users
-- COPY (
--   SELECT
--     gen_random_uuid() as id,
--     u.email,
--     u.password as password_hash,
--     u.first_name,
--     u.last_name,
--     u.mobile as phone,
--     'user' as user_type,
--     CASE WHEN u.is_active THEN 'active' ELSE 'inactive' END as status,
--     u.is_active,
--     false as email_verified,
--     now() as created_at,
--     now() as updated_at
--   FROM users_user u
-- ) TO '/tmp/users.csv' CSV HEADER;
```

---

## Part 2: Core Service Migration (core_db)

### 2.1 What Maps to core_db

The new core-service is an **ERP system** — not a QR/campaign platform. The tables
that exist in core_db are:

**Already implemented in core-service:**

- `accounts` (Chart of Accounts)
- `currency_masters`, `exchange_rates`
- `uoms`, `uom_conversions`
- `payment_entries`, `payments`
- `items`, `item_groups`, `item_prices`, `item_suppliers`
- `warehouses`
- `stock_levels`, `stock_movements`, `stock_entries`, `stock_reconciliations`
- `customers`, `suppliers`
- `quotations`, `sales_orders`
- `purchase_orders`, `rfqs`, `material_requests`
- `invoices`, `invoice_items`
- `delivery_notes`, `purchase_receipts`
- `pick_lists`
- `journal_entries`
- `communications`
- `bank_accounts`, `bank_transactions`, `bank_reconciliations`
- `tax_templates`, `charge_templates`
- `batches`, `serial_nos`
- `quality_inspections`
- `put_away_rules`
- `landed_cost` tables
- `document_numbering`
- `bulk_import_jobs`, `bulk_export_jobs`

### 2.2 Old QSeal Tables NOT in core_db (Need New Modules)

These old Django app tables have **no equivalent** in the current core-service.
If you need them, they require new modules:

| Old Table                                           | Status                     | Action Needed                  |
| --------------------------------------------------- | -------------------------- | ------------------------------ |
| `products` / `qr_blocks` / `product_items`          | ❌ Not in core-service     | Build QR Product module        |
| `qr_activation_parameters` / `qr_activation_tracks` | ❌ Not in core-service     | Build QR Activation module     |
| `qr_credit_usage`                                   | ❌ Not in core-service     | Build Credit Tracking module   |
| `campaigns` / `web_campaigns`                       | ❌ Not in core-service     | Build Campaign module          |
| `leads` / `coupons` / `external_coupons`            | ❌ Not in core-service     | Build Lead/Coupon module       |
| `tags` / `lead_tags`                                | ❌ Not in core-service     | Build Tagging module           |
| `message_templates` / `bulk_message_jobs`           | ❌ Not in core-service     | Build Messaging module         |
| `sms_reports` / `whatsapp_reports` / `rcs_*`        | ❌ Not in core-service     | Build Messaging Reports module |
| `message_credits`                                   | ❌ Not in core-service     | Build Credit module            |
| `warranties` / `warranty_periods`                   | ❌ Not in core-service     | Build Warranty module          |
| `qr_scan_events` / `meta_campaigns`                 | ❌ Not in core-service     | Build Analytics module         |
| `otp_verifications`                                 | ❌ Not in identity-service | Add to identity-service        |
| `shopify_configs`                                   | ❌ Not in core-service     | Build Integration module       |

### 2.3 Partial Overlaps (Old → New Mapping)

Some old tables have partial equivalents in core-service:

| Old Table   | New Table   | Overlap                     |
| ----------- | ----------- | --------------------------- |
| `leads`     | `customers` | Name, email, phone, address |
| `coupons`   | —           | No direct equivalent        |
| `products`  | `items`     | Name, description only      |
| `campaigns` | —           | No direct equivalent        |

---

## Part 3: Step-by-Step Migration Plan

### Phase 1: Backup Everything

```bash
# Backup old Django app database
pg_dump -h <old-host> -U <old-user> -d <old-db> -F c -f old_app_backup.dump

# Backup current new service databases (if they have data)
pg_dump -h localhost -U horizon_user -d identity_db -F c -f identity_db_backup.dump
pg_dump -h localhost -U horizon_user -d core_db -F c -f core_db_backup.dump
```

### Phase 2: Migrate identity_db

```bash
# 1. Connect to old DB and export organizations
psql -h <old-host> -U <old-user> -d <old-db> -c "
COPY (
  SELECT
    gen_random_uuid()::text as id,
    c.name,
    lower(regexp_replace(c.name, '[^a-zA-Z0-9]+', '-', 'g')) as slug,
    c.name as display_name,
    'business' as organization_type,
    COALESCE(c.industry, 'general') as industry,
    c.domain_url as domain,
    lower(c.status) as status,
    true as is_active,
    jsonb_build_object(
      'short_code', b.short_code,
      'public_key', b.public_key,
      'schema_name', c.schema_name,
      'qr_credit_limit', c.qr_credit_limit,
      'timezone', c.timezone,
      'old_id', c.id
    )::text as extra_data,
    now()::text as created_at,
    now()::text as updated_at
  FROM dashboard_client c
  LEFT JOIN integration_brand b ON b.client_id = c.id
) TO '/tmp/orgs_export.csv' CSV HEADER;
"

# 2. Import into identity_db
psql -h localhost -U horizon_user -d identity_db -c "
\COPY organizations (id, name, slug, display_name, organization_type, industry, domain, status, is_active, extra_data, created_at, updated_at)
FROM '/tmp/orgs_export.csv' CSV HEADER;
"

# 3. Export users from old DB
psql -h <old-host> -U <old-user> -d <old-db> -c "
COPY (
  SELECT
    gen_random_uuid()::text as id,
    u.email,
    u.password as password_hash,
    COALESCE(u.first_name, '') as first_name,
    COALESCE(u.last_name, '') as last_name,
    u.mobile as phone,
    'user' as user_type,
    CASE WHEN u.is_active THEN 'active' ELSE 'inactive' END as status,
    u.is_active,
    false as email_verified,
    now()::text as created_at,
    now()::text as updated_at
  FROM users_user u
) TO '/tmp/users_export.csv' CSV HEADER;
"

# 4. Import users into identity_db
psql -h localhost -U horizon_user -d identity_db -c "
\COPY users (id, email, password_hash, first_name, last_name, phone, user_type, status, is_active, email_verified, created_at, updated_at)
FROM '/tmp/users_export.csv' CSV HEADER;
"

# 5. Link users to organizations via user_organization_roles
# You'll need to know which user belongs to which org.
# In the old app, users had a tenant_id FK to Client.
psql -h <old-host> -U <old-user> -d <old-db> -c "
COPY (
  SELECT
    gen_random_uuid()::text as id,
    -- Map old user UUID to new user UUID using email as key
    -- Map old org UUID to new org UUID using name/slug as key
    -- This requires a lookup table built from the exports above
    u.email as user_email,
    c.name as org_name,
    'member' as role_code,
    true as is_active,
    now()::text as created_at
  FROM users_user u
  JOIN dashboard_client c ON c.id = u.tenant_id
) TO '/tmp/user_org_export.csv' CSV HEADER;
"
# Then run a script to resolve emails/names to new UUIDs and insert into user_organization_roles
```

### Phase 3: Migrate core_db (ERP Data Only)

The core-service tables are ERP-focused. If the old app had any ERP-like data
(customers, products as items, etc.), migrate those:

```bash
# Migrate leads → customers (partial overlap)
psql -h <old-host> -U <old-user> -d <old-db> -c "
COPY (
  SELECT
    gen_random_uuid()::text as id,
    '<your-org-uuid>' as organization_id,
    l.name as customer_name,
    l.email,
    l.mobilenumber as phone,
    l.address,
    l.state_name as state,
    l.country,
    now()::text as created_at,
    now()::text as updated_at
  FROM integration_lead l
  WHERE l.email IS NOT NULL
) TO '/tmp/customers_export.csv' CSV HEADER;
"

# Migrate products → items (name/description only, no QR fields)
psql -h <old-host> -U <old-user> -d <old-db> -c "
COPY (
  SELECT
    gen_random_uuid()::text as id,
    '<your-org-uuid>' as organization_id,
    p.name as item_name,
    p.generic_name as description,
    p.gtin as barcode,
    now()::text as created_at,
    now()::text as updated_at
  FROM integration_product p
) TO '/tmp/items_export.csv' CSV HEADER;
"
```

### Phase 4: Verify Migration

```sql
-- Check organization count matches
SELECT COUNT(*) FROM organizations; -- identity_db
-- vs old: SELECT COUNT(*) FROM dashboard_client;

-- Check user count matches
SELECT COUNT(*) FROM users; -- identity_db
-- vs old: SELECT COUNT(*) FROM users_user;

-- Check no duplicate slugs
SELECT slug, COUNT(*) FROM organizations GROUP BY slug HAVING COUNT(*) > 1;

-- Check no orphaned user_organization_roles
SELECT COUNT(*) FROM user_organization_roles uor
LEFT JOIN users u ON u.id = uor.user_id
WHERE u.id IS NULL;
```

---

## Part 4: Key Differences to Handle

### 4.1 Integer PKs → UUIDs

The old Django app likely uses integer auto-increment PKs. The new system uses UUIDs.

**Strategy**: Generate new UUIDs during migration. Store the old integer ID in
`extra_data->>'old_id'` for traceability during transition.

```sql
-- Example: store old_id mapping
UPDATE organizations
SET extra_data = extra_data || jsonb_build_object('old_id', '123')
WHERE name = 'Some Client';
```

### 4.2 Schema-per-Tenant → organization_id Column

Old app used PostgreSQL schemas (e.g., `tenant_abc.products`). New app uses a
single schema with `organization_id` on every row.

**Strategy**: When exporting from old DB, always include the tenant/client ID and
map it to the new `organization_id` UUID.

### 4.3 Status Enum Case

Old app uses uppercase status values (`'ACTIVE'`). New identity-service uses
lowercase (`'active'`).

```sql
-- Fix during import
UPDATE organizations SET status = lower(status);
UPDATE users SET status = lower(status);
```

### 4.4 Password Hashes

If the old app used Django's default PBKDF2 password hashing and the new app uses
bcrypt, passwords are **not directly compatible**. Options:

1. Force all users to reset passwords on first login (recommended)
2. Keep old hashes and add a migration shim in the auth service
3. Re-hash if you have access to plaintext (not recommended)

### 4.5 Roles and Permissions

The old app stored roles as a `TEXT[]` array on the user. The new system uses a
proper RBAC model with `roles`, `permissions`, `role_permissions`, and
`user_organization_roles` tables.

**Strategy**:

1. Create default roles in identity_db (admin, member, viewer)
2. Map old role strings to new role codes
3. Insert into `user_organization_roles`

```sql
-- Create default roles first (if not seeded)
INSERT INTO roles (id, name, code, is_system, is_active, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'Admin', 'admin', true, true, now(), now()),
  (gen_random_uuid(), 'Member', 'member', true, true, now(), now()),
  (gen_random_uuid(), 'Viewer', 'viewer', true, true, now(), now());
```

---

## Part 5: Tables That Need New Alembic Migrations

If you want to bring QSeal-specific features into the new services, you need to
create new Alembic migrations. Here's the priority list:

### identity-service — Add to identity_db

```
Migration needed: 004_add_otp_verifications.py
Table: otp_verifications
Columns: id, organization_id, otp, otp_type, email, mobile, location, order_id, is_verified, created_at
```

### core-service — Add to core_db (if QSeal features needed)

```
Migration needed: 024_add_qr_products.py
Tables: qr_products, qr_blocks, product_items, qr_activation_parameters

Migration needed: 025_add_campaigns.py
Tables: campaigns, web_campaigns, play2win_prizes

Migration needed: 026_add_leads_coupons.py
Tables: leads (extend customers), coupons, external_coupons, coupon_unlock_logs

Migration needed: 027_add_messaging.py
Tables: message_templates, bulk_message_jobs, scheduled_messages,
        sms_reports, whatsapp_reports, rcs_templates, rcs_reports, message_credits

Migration needed: 028_add_warranties.py
Tables: warranty_periods, warranties

Migration needed: 029_add_analytics.py
Tables: qr_scan_events, meta_campaigns
```

---

## Part 6: Migration Checklist

### Pre-Migration

- [ ] Take full backup of old Django app database
- [ ] Take full backup of current identity_db and core_db
- [ ] Document all old table names and row counts
- [ ] Identify which old Django app tables you actually need to migrate
- [ ] Decide on password migration strategy (reset vs. shim)

### identity_db Migration

- [ ] Export `dashboard_client` → `organizations`
- [ ] Export `integration_brand` → merge into `organizations.extra_data`
- [ ] Export `users_user` → `users`
- [ ] Create default roles in `roles` table
- [ ] Build `user_organization_roles` from old user-tenant relationships
- [ ] Verify row counts match
- [ ] Verify no duplicate slugs in `organizations`
- [ ] Verify no orphaned foreign keys

### core_db Migration (ERP data only)

- [ ] Export `integration_lead` → `customers` (if applicable)
- [ ] Export `integration_product` → `items` (name/description only)
- [ ] Verify organization_id is set correctly on all rows
- [ ] Run Alembic migrations to ensure schema is up to date

### Post-Migration

- [ ] Test login with migrated user credentials
- [ ] Test organization lookup by slug
- [ ] Test API endpoints with migrated data
- [ ] Monitor logs for FK constraint violations
- [ ] Keep old DB running in read-only mode for 2 weeks as fallback

---

## Part 7: Running the Migration

### Prerequisites

```bash
# Ensure both services are running
docker compose up -d postgres identity-service core-service

# Verify databases exist
docker compose exec postgres psql -U horizon_user -c "\l"
# Should show: identity_db, core_db, search_db
```

### Run Alembic Migrations First

```bash
# identity-service
docker compose exec identity-service python -m alembic upgrade head

# core-service
docker compose exec core-service python -m alembic upgrade head
```

### Execute Migration Scripts

```bash
# Run from project root
# 1. Export from old DB (adjust connection string)
OLD_DB="postgresql://old_user:old_pass@old_host:5432/old_db"

psql $OLD_DB -f scripts/export_organizations.sql
psql $OLD_DB -f scripts/export_users.sql

# 2. Import into new DBs
NEW_IDENTITY="postgresql://horizon_user:horizon_pass@localhost:5432/identity_db"

psql $NEW_IDENTITY -f scripts/import_organizations.sql
psql $NEW_IDENTITY -f scripts/import_users.sql
psql $NEW_IDENTITY -f scripts/create_user_org_roles.sql
```

---

## Summary

| What               | From                                     | To                                      | Complexity        |
| ------------------ | ---------------------------------------- | --------------------------------------- | ----------------- |
| Organizations      | `dashboard_client` + `integration_brand` | `identity_db.organizations`             | Medium            |
| Users              | `users_user`                             | `identity_db.users`                     | Medium            |
| Roles/Permissions  | `TEXT[]` on user                         | `roles`, `user_organization_roles`      | High              |
| OTP                | `integration_otp`                        | Needs new migration in identity-service | Low               |
| QR Products/Blocks | `integration_product`, `qr_blocks`       | Not in core-service yet                 | High (new module) |
| Campaigns/Coupons  | `campaigns`, `coupons`                   | Not in core-service yet                 | High (new module) |
| Messaging          | `message_templates`, reports             | Not in core-service yet                 | High (new module) |
| Leads → Customers  | `integration_lead`                       | `core_db.customers` (partial)           | Low               |
| Products → Items   | `integration_product`                    | `core_db.items` (name only)             | Low               |
