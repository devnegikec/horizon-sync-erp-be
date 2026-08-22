# Railway ↔ Local Database Sync Guide

For a dev workflow where **remote (Railway) is the source of truth** and local is just your working copy, the best approach is a **snapshot dump + restore**, not continuous two-way sync (two-way sync is overkill and risky for dev).

## Recommended approach

### 1. Keep schema in sync with migrations, not dumps

The project uses Alembic. Always run this locally:

```bash
alembic upgrade head
```

This keeps your schema correct. Only _data_ needs to come from remote.

### 2. Pull a data snapshot from Railway

```bash
# Open a local tunnel to Railway Postgres (copy the local proxy URL it prints)
railway connect Postgres

# Dump in custom format (fast, compressible)
pg_dump -Fc --no-owner --no-acl "$RAILWAY_PROXY_URL" > prod.dump

# Restore into local Postgres
pg_restore --no-owner --no-acl -d "$LOCAL_DATABASE_URL" --clean --if-exists prod.dump
```

Notes:

- `--no-owner --no-acl` prevents ownership/permission errors from different roles.
- `-Fc` (custom format) + `pg_restore` is faster and can restore in parallel: `pg_restore -j 4`.
- If the dump is large, `--data-only` + `--disable-triggers` lets you refresh only data against a schema you created via migrations:
  ```bash
  pg_dump --data-only -Fc --no-owner --no-acl "$RAILWAY_PROXY_URL" > data.dump
  pg_restore --data-only --no-owner --no-acl --disable-triggers -d "$LOCAL_DATABASE_URL" data.dump
  ```

### 3. Wrap it in a script

Create a `sync_local_db.sh` so it's one command:

```bash
#!/usr/bin/env bash
set -euo pipefail
railway connect Postgres &   # or run in background and capture the URL
sleep 3
pg_dump -Fc --no-owner --no-acl "$RAILWAY_PROXY_URL" > prod.dump
pg_restore --no-owner --no-acl -d "$LOCAL_DATABASE_URL" --clean --if-exists prod.dump
```

## When you need it near-real-time: logical replication

PostgreSQL native logical replication gives you continuous one-way sync (remote → local):

```sql
-- on remote
CREATE PUBLICATION prod_pub FOR ALL TABLES;
-- on local
CREATE SUBSCRIPTION local_sub
  CONNECTION 'host=... dbname=...'
  PUBLICATION prod_pub;
```

Caveats:

- Requires `wal_level = logical` on the source — **Railway's managed Postgres may not expose this**.
- One-way only; local changes can break the subscription.
- Schema must match exactly (which is why migrations-first is important).

## What to avoid

- Don't try to keep two-way sync running continuously for dev — conflict resolution isn't worth it.
- Don't copy production schema via dump when you have migrations; it will drift.
- **Anonymize sensitive data** after restore if this is a shared/dev environment (a simple `UPDATE ... SET email = ...` script or a tool like `postgresql-anonymizer`).

**TL;DR:** `alembic upgrade head` for schema + `pg_dump -Fc`/`pg_restore` through `railway connect Postgres` for data, wrapped in one script. That's the cleanest and fastest for local development.
