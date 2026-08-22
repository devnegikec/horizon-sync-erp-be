# Railway Cloud + Local Postgres Dev Workflow

## Problem: slow local dev

- Local backend → remote Railway Postgres = high per-query latency (100–300ms RTT), worse with N+1 queries.
- Best fix: remove the chatty long hop.

## Options (ranked)

1. **Backend in Railway (near DB), only frontend local** — point local frontend at a Railway dev/preview env URL. Chatty hop (backend↔DB) is fast; frontend→backend is one HTTP call.
2. **Local Postgres** (when local backend breakpoints needed) — Docker Postgres seeded from Railway dump; point local `DATABASE_URL` at localhost.
3. **Tunnel**: `railway connect Postgres` (private URL via local proxy) instead of `DATABASE_PUBLIC_URL` — more secure, sometimes faster, but physical latency remains.
4. Quick wins: fix N+1 (eager loading/selectinload), use pgBouncer pooler, add indexes.

## Schema sync = migrations (not dumps)

- Always `alembic upgrade head` locally. Only DATA comes from remote.

## One-time data snapshot

```bash
railway connect Postgres   # copy local proxy URL
pg_dump -Fc --no-owner --no-acl "$RAILWAY_PROXY_URL" > prod.dump
pg_restore --no-owner --no-acl -d "$LOCAL_DATABASE_URL" --clean --if-exists prod.dump
# parallel restore: pg_restore -j 4
# data-only refresh: pg_dump --data-only -Fc ... | pg_restore --data-only --disable-triggers ...
```

## Regular/automated sync

- Script: pg_dump → `dropdb --if-exists` → `createdb` → pg_restore (clean recreate avoids drift/FK issues).
- Windows Task Scheduler:

```bash
schtasks /create /tn "SyncRailwayDB" \
  /tr "\"C:\Program Files\Git\bin\bash.exe\" -lc \"D:/Code/CRM_NEW/sync_local_db.sh\"" \
  /sc daily /st 08:00
```

- WSL cron: `0 8 * * * /mnt/d/.../sync_local_db.sh >> /tmp/db_sync.log 2>&1`
- Logical replication (continuous, set-and-forget): `CREATE PUBLICATION` remote + `CREATE SUBSCRIPTION` local. Needs `wal_level=logical` (Railway managed may not allow), one-way only, schema must match.

## Tips

- Keep `railway connect Postgres` tunnel running in background/separate terminal for scheduled jobs, or use `DATABASE_PUBLIC_URL`.
- Schedule off-hours; drop/recreate disconnects local users.
- `set -euo pipefail` + log output for failure detection.
- Anonymize sensitive data after restore (e.g., postgresql-anonymizer).
