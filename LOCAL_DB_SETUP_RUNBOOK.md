# Local DB Setup & Railway Data Sync — Runbook

A step-by-step runbook for running a **local Postgres container** and pulling a
**data snapshot from Railway** so you can debug/test against fast local storage
instead of the remote cloud DB.

> Companion docs:
>
> - `RAILWAY_LOCAL_DB_SYNC_GUIDE.md` — the conceptual approach (snapshot + restore)
> - `railway-db-sync.md` — workflow options & scheduling notes

---

## 0. What this runbook assumes

Current state of this repo:

- Both `identity-service/.env` and `core-service/.env` point **directly at Railway**:
  ```
  postgresql://postgres:***@roundhouse.proxy.rlwy.net:12893/railway
  ```
  → local uvicorn processes are doing slow round-trips to the cloud DB.
- Railway uses **one database named `railway`** containing all tables
  (identity + core + search together).
- The local `docker-compose.yml` splits into `identity_db` / `core_db` / `search_db`.

Because production is a single shared DB, this runbook mirrors that: we use
**one local database named `railway`** (same name as remote) for everything.

---

## 1. Prerequisites

| Tool               | Status     | Notes                                                  |
| ------------------ | ---------- | ------------------------------------------------------ |
| Docker Desktop     | Required   | Must be **running** (daemon up)                        |
| `psql` / `pg_dump` | Not needed | All dump/restore runs inside the Postgres container    |
| Railway CLI        | Optional   | Only needed for the private tunnel (`railway connect`) |

> **Version match is mandatory:** local Postgres must be the same major version
> as Railway (currently **18.x**). A 15.x `pg_dump` cannot dump a 18.x server —
> it aborts with "server version mismatch".

---

## 2. Step 0 — Start Docker Desktop

Start **Docker Desktop** and wait for the whale icon to stop animating, then verify:

```bash
docker info
```

If this errors with "daemon is not running", Docker Desktop has not finished booting.

---

## 3. Step 1 — Get the Railway connection string

Pick one option:

**Option A — no CLI (recommended to start):**
Railway dashboard → your project → **Postgres** → **Connect** → copy the
**Public Network** `postgresql://...` string.

> Shortcut: your existing `core-service/.env` already contains this exact URL
> (the `roundhouse.proxy.rlwy.net:12893/railway` one).

**Option B — Railway CLI (optional, enables a private tunnel):**

```bash
npm i -g @railway/cli
railway login
```

---

## 4. Step 2 — Create the secrets file

```bash
cd /d/Code/CRM_NEW/horizon-sync-erp-be
cp .sync.env.example .sync.env
```

Edit `.sync.env` and set:

```ini
SOURCE_DATABASE_URL=remoteDB_URL
```

- Leave `SOURCE_DATABASE_URL` **empty** if you installed the Railway CLI —
  the script auto-opens a `railway connect Postgres` tunnel instead.
- `.sync.env` is gitignored (never committed).

---

## 5. Step 3 — Start the local Postgres container

```bash
cd /d/Code/CRM_NEW/horizon-sync-erp-be
docker compose up -d postgres
```

This starts `horizon_postgres` (Postgres 18) on `localhost:5432`. The init script
auto-creates `identity_db`, `core_db`, `search_db`.

> If you previously ran the old `postgres:15-alpine` container, you must recreate
> it (Postgres cannot upgrade its data directory across major versions in place):
>
> ```bash
> docker compose down -v
> docker compose up -d postgres
> ```

The `railway` database is created automatically by the sync script in Step 4.
To create it manually instead:

```bash
docker exec -it horizon_postgres psql -U horizon_user -d postgres -c "CREATE DATABASE railway;"
```

---

## 6. Step 4 — First-time full sync (schema + data)

Stop any running uvicorn processes first (a full restore drops/recreates tables):

```bash
./sync_local_db.sh railway --full
```

Dumps everything from Railway and restores it into local `railway`.

---

## 7. Step 5 — Point services at localhost

**`identity-service/.env`:**

```ini
DATABASE_URL=localDB_url
```

**`core-service/.env`:**

```ini
DATABASE_URL=localDB_url
IDENTITY_DATABASE_URL=localDB_url
```

(If `search-service` runs locally too, point it at `railway` the same way.)

Keep the old Railway URLs commented out so you can switch back. Then restart the
uvicorn terminals.

---

## 8. Step 6 — Verify

```bash
docker exec -it horizon_postgres psql -U horizon_user -d railway -c "\dt"
```

You should see the tables, and the services should feel noticeably faster.

---

## 9. Step 7 — Ongoing data refresh

Whenever you want fresh data (schema already matches):

```bash
./sync_local_db.sh railway
```

Defaults to **data-only** mode — faster, does not touch schema.

---

## 10. Scheduling (optional)

**Windows Task Scheduler:**

```bash
schtasks /create /tn "SyncRailwayDB" /tr "\"C:\Program Files\Git\bin\bash.exe\" -lc \"D:/Code/CRM_NEW/horizon-sync-erp-be/sync_local_db.sh railway\"" /sc daily /st 08:00
```

**WSL cron:**

```bash
0 8 * * * /mnt/d/Code/CRM_NEW/horizon-sync-erp-be/sync_local_db.sh railway >> /tmp/db_sync.log 2>&1
```

---

## 11. Script reference

`sync_local_db.sh <database> [--full]`

| Argument     | Meaning                  | Default           |
| ------------ | ------------------------ | ----------------- |
| `<database>` | Target local DB          | `railway`         |
| `--full`     | Full schema+data replace | (off → data-only) |

| Env var (in `.sync.env`) | Purpose                         | Default            |
| ------------------------ | ------------------------------- | ------------------ |
| `SOURCE_DATABASE_URL`    | Railway URL (or use CLI tunnel) | —                  |
| `LOCAL_DB_USER`          | Local DB user                   | `db_user`          |
| `LOCAL_DB_PASSWORD`      | Local DB password               | `db_password`      |
| `LOCAL_DB_PORT`          | Local DB port                   | `5432`             |
| `LOCAL_CONTAINER`        | Postgres container name         | `horizon_postgres` |
| `RAILWAY_SERVICE`        | Railway plugin name for tunnel  | `Postgres`         |

Dumps are archived to `horizon-sync-erp-be/.db_dumps/` with timestamps for rollback.
