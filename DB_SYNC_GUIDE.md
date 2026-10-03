# Local DB Sync Guide (Railway → local dev)

This guide covers replicating the Railway Postgres data into your local
Postgres container and keeping it refreshed for dev work.

**Golden rule:** schema changes are applied by **migrations in CI/CD** when a PR
merges. Your local DB is a **data replica only** — do **not** run `alembic
upgrade` against it.

> The root `docker-compose.yml` services (`identity-service`, `core-service`)
> run `alembic upgrade` in their startup command. For syncing, start **only**
> the `postgres` service (`docker compose up -d postgres`) — never the full
> stack — or those migrations will rewrite your replica and may fail on
> revision drift.

---

## 1. How it works

The helper script `sync_local_db.sh`:

1. Ensures Docker + the local `postgres` container are running.
2. Ensures the target database exists locally.
3. Dumps the source (Railway) DB using `pg_dump` — **inside** the Postgres
   container (no local `psql`/`pg_dump` install required).
4. Restores the dump into the local database with `pg_restore`.
5. Archives every dump under `.db_dumps/` (gitignored).

Two modes:

| Mode | What it syncs | Use when |
|---|---|---|
| `--full` (recommended) | schema **and** data | you don't run Alembic locally (CI/CD migrates remote) |
| default (data-only) | data only | you build schema locally via `alembic upgrade` first |

> Prefer `--full` — it makes local an exact replica of remote, which sidesteps
> any `core_alembic_version` drift (e.g. the `133_item_group_default_fields`
> issue) because you never run Alembic locally.

---

## 2. Prerequisites

- Docker Desktop running.
- The root `docker-compose.yml` `postgres` service — start **only** this service
  (`docker compose up -d postgres`); the script does this automatically.
- Source URLs for each DB — `CORE_SOURCE_DATABASE_URL` and
  `IDENTITY_SOURCE_DATABASE_URL` (Railway → Postgres → **Connect** → *Public Network*).

---

## 3. Configuration — `.sync.env`

Copy `.sync.env.example` → `.sync.env` (gitignored) and set:

```bash
# One profile per remote database
CORE_SOURCE_DATABASE_URL=postgresql://postgres:PASSWORD@iriguchi.proxy.rlwy.net:39497/railway
CORE_TARGET_DB=core_db

IDENTITY_SOURCE_DATABASE_URL=postgresql://postgres:PASSWORD@iriguchi.proxy.rlwy.net:15540/railway
IDENTITY_TARGET_DB=identity_db

# Local target container
LOCAL_DB_USER=horizon_user
LOCAL_DB_PASSWORD=horizon_pass
LOCAL_DB_PORT=5432
LOCAL_CONTAINER=horizon_postgres   # must match `container_name` in docker-compose.yml
```

---

## 4. Usage

```bash
# Sync core only (→ local core_db)
./sync_local_db.sh core --full

# Sync identity only (→ local identity_db)
./sync_local_db.sh identity --full

# Sync both (default)
./sync_local_db.sh all --full

# Data-only refresh
./sync_local_db.sh core
```

Then point your local `.env` files at the replicas:

```bash
# core-service/.env
DATABASE_URL=postgresql://horizon_user:horizon_pass@localhost:5432/core_db
IDENTITY_DATABASE_URL=postgresql://horizon_user:horizon_pass@localhost:5432/identity_db

# identity-service/.env
DATABASE_URL=postgresql://horizon_user:horizon_pass@localhost:5432/identity_db
```

---

## 5. Scheduling (Windows)

```bash
schtasks /create /tn "SyncRailwayDB" \
  /tr "\"C:\Program Files\Git\bin\bash.exe\" -lc \"D:/Code/CRM_NEW/horizon-sync-erp-be/sync_local_db.sh all --full\"" \
  /sc daily /st 08:00
```

WSL cron:

```cron
0 8 * * * /mnt/d/Code/CRM_NEW/horizon-sync-erp-be/sync_local_db.sh all --full >> /tmp/db_sync.log 2>&1
```

(`all` syncs both core and identity in one run.)

---

## 6. Caveats & troubleshooting

- **Don't run Alembic locally.** The replica carries remote's
  `core_alembic_version` marker. Local Alembic will fail if remote has a
  revision missing from your checkout. Schema arrives via CI/CD → Railway →
  your next sync.
- **`LOCAL_CONTAINER` must be the actual container name** (`horizon_postgres` in
  the root `docker-compose.yml`). The script and `.sync.env` already default to
  `horizon_postgres` — only change it if your local container is named
  differently.
- **Stop local services before a `--full` sync** so `pg_restore --clean` doesn't
  conflict with active connections (or `dropdb --force`).
- **Parallel restore** is already enabled (`-j 4`) for speed.
- **Private access**: sync uses the Public Network URLs in `.sync.env`. For a
  private tunnel instead, run `railway connect Postgres` yourself and paste the
  resulting `postgresql://...` URL into the relevant
  `<PROFILE>_SOURCE_DATABASE_URL`.
- **Git Bash path mangling** is handled by the script (`MSYS_NO_PATHCONV` +
  `cygpath`); if dumps mis-copy on Windows, verify the script is run from Git
  Bash.
- Dumps are archived in `.db_dumps/` (gitignored) — clean them up periodically.
