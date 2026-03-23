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
