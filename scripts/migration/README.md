# Migration Scripts

## Phase 1: Identity Migration (Old Django QSeal → identity_db)

### Prerequisites

1. Old Django DB must be accessible
2. New identity_db must be running with Alembic migrations applied
3. `/tmp/` must be writable on the machine running the export

### Step-by-step

**Step 1 — Apply Alembic migrations on identity-service (if not done)**

```bash
docker compose exec identity-service python -m alembic upgrade head
```

**Step 2 — Backup both databases**

```bash
# Backup old DB
pg_dump -h <OLD_HOST> -U <OLD_USER> -d <OLD_DB> -F c -f /tmp/old_qseal_backup.dump

# Backup new identity_db
pg_dump -h localhost -U horizon_user -d identity_db -F c -f /tmp/identity_db_backup_pre_migration.dump
```

**Step 3 — Export from old DB**

```bash
OLD_DB="postgresql://OLD_USER:OLD_PASS@OLD_HOST:5432/OLD_DB_NAME"
psql $OLD_DB -f scripts/migration/phase1_export_from_old_db.sql
```

This writes 3 CSV files to `/tmp/`:

- `qseal_orgs_export.csv`
- `qseal_users_export.csv`
- `qseal_user_org_map.csv`

**Step 4 — Import into identity_db**

```bash
NEW_IDENTITY_DB="postgresql://horizon_user:horizon_pass@localhost:5432/identity_db"
psql $NEW_IDENTITY_DB -f scripts/migration/phase1_import_to_identity_db.sql
```

**Step 5 — Verify**

```bash
psql $NEW_IDENTITY_DB -f scripts/migration/phase1_verify.sql
```

### Password Strategy

The old Django app uses **PBKDF2** password hashing. The new identity-service uses **bcrypt**.
These are incompatible — you cannot verify a PBKDF2 hash with bcrypt.

**Decision: Force password reset on first login.**

- All migrated users get a placeholder `password_hash` that will never match any input
- The old PBKDF2 hash is preserved in `users.extra_data.old_password_hash` for reference
- Users must use "Forgot Password" to set a new bcrypt password
- Make sure the password reset email flow is working before announcing the migration

### Troubleshooting

**Duplicate slug error**: The import script auto-appends `-2`, `-3` etc. to duplicate slugs.
Check with: `SELECT slug, COUNT(*) FROM organizations GROUP BY slug HAVING COUNT(*) > 1;`

**Users not assigned to org**: If `users_user.tenant_id` is NULL in the old DB, those users
won't appear in `user_organization_roles`. Check the "Users with no org assignment" section
in the verify output and manually assign them.

**Old DB table names differ**: The export SQL assumes `dashboard_client`, `integration_brand`,
and `users_user`. Adjust if your old app uses different table names.
Check with: `\dt` in psql against the old DB.

---

## Phase 2: QSeal Domain Migration (`elemage`/elemaze → core_db)

Script: `phase2_migrate_elemage_qseal.py`

Migrates the **elemaze** client (old tenant schema `elemage`, AWS EC2) into the new
ERP core-service database. Run it **after** Phase 1 so the organization exists.

### What gets migrated

| Old (`elemage.*`) | New (`core_db`) |
|---|---|
| `integration_brand` | `brands` |
| `integration_product` | `products` + `qr_products` |
| `integration_serialnumformat` / `channel` / `destinationmarket` / `warrantyperiod` | `qr_product_settings` (+ `destination_markets`, `warranty_periods`) |
| *(derived, one per product)* | `product_skus` (`ELEMAGE-<id>`) |
| `integration_order` (old model name: "Block") | `qr_blocks` |
| `integration_productitem` | `product_items` |
| `integration_qractivationparameters` | `qr_activation_parameters` (+ `qseal_parameters` with `--mirror-qseal`) |
| `integration_productcertificate` | `qr_scan_events` |
| `integration_lead` | `campaign_leads` (campaign_id NULL — old campaigns table is empty) |
| `integration_warranty` | `warranties` (empty in this tenant) |

**Not migrated** (no target equivalent / not QSeal): POS tables
(`integration_store*`), pallets, `skuqr`/`qr`, analytics events, messaging/report
tables, NFTs, OTPs. Phase 1 handled users/organisations.

### How the source is read

The script shells out to:

```
ssh -i <key> <host> "docker exec -i <container> psql -U <user> -d <db> --csv -q -f -"
```

SQL is piped over stdin, so **no AWS credentials or open DB ports are needed**.
Defaults match production (`3.6.154.21`, `postgres_db`, `adminportal`, `elemage`).

### Run it

```bash
cd /path/to/horizon-sync-be

export TARGET_DATABASE_URL='postgresql://postgres:PASS@<railway-proxy>:<port>/railway'
export IDENTITY_DATABASE_URL='postgresql://postgres:PASS@<railway-identity-proxy>:<port>/railway'
export BRAND_KEY_ENCRYPTION_SECRET='<same Fernet key the core-service uses>'

# 1. Preview (rolls back at the end)
python scripts/migration/phase2_migrate_elemage_qseal.py --dry-run --mirror-qseal

# 2. Apply
python scripts/migration/phase2_migrate_elemage_qseal.py --org-slug elemage --mirror-qseal
```

If you already have a tunnel to the AWS database:

```bash
python scripts/migration/phase2_migrate_elemage_qseal.py \
  --source-mode direct --source-url 'postgresql://adminportal_user:PASS@localhost:15432/adminportal' \
  --org-slug elemage --mirror-qseal
```

### Properties

- **Idempotent** — every ID is `uuid5(...)`; inserts use `ON CONFLICT (id) DO UPDATE`.
  Re-running updates instead of duplicating.
- **Atomic** — one transaction; any failure rolls back the whole run.
- **Safe on shared serials** — `product_items.serial_number` has a *global* unique
  index. Pre-existing serials under another id are skipped and reported, and child
  scan events are re-pointed at the existing row.
- `--purge-org` deletes this org's QSeal rows first (destructive; use with care).

### Known gaps / manual follow-ups

1. **Brand keys** — the old brand key pair is legacy RSA; the ERP signs QR codes with
   ECDSA P-256 + Fernet. Pass `BRAND_KEY_ENCRYPTION_SECRET` so a compatible,
   deterministic pair is generated. Without it `private_key_encrypted` stays NULL and
   cascade signing will not work for this brand.
2. **Old printed QR payloads** were signed with the old scheme — signature
   verification of already-printed labels will not pass against the new keys. Serial
   lookup (`product_items` + `qr_activation_parameters`) still works.
3. **Images** — `image`/`banner_image` were Django-relative media paths, copied
   verbatim. They need rewriting to real URLs (S3/GCS) if the frontend uses them.
4. **No SKU variants** — legacy products had none, so one SKU per product is created.
   Split into real variants later if needed.
5. `qr_activation_parameters.parent_id/parent_app_id` are NULL because the old
   `integration_qractivationtrack` table is empty.
6. **POS module data** (stores, bills, payments, purchase items) is not migrated.
