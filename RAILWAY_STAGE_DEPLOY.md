Railway Stage Deploy — Horizon Sync (BW-staging)
=================================================

Purpose
-------
Quick reference for deploying the `stage` branch of `bworigin` (`github.com/devciphercode/brandwise-2.0`)
to the dedicated **BW-staging** Railway project, with automatic deploys on every push/merge to `stage`.

> This doc is the staging counterpart of `RAILWAY_FAST_DEPLOY.md`. Read that file
> first for general Railway CLI setup, token creation, and troubleshooting.

Resource map (IDs)
------------------
| Resource | Name | ID |
|---|---|---|
| Project | BW-staging | `fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090` |
| Environment (target) | staging | `42a3b024-6059-47e2-a977-0e4377ef6e13` |
| Environment (unused for now) | production | `5fd250b5-ddf5-429c-9b2b-3274c3d5a2d7` |
| Service — core app | brandwise-2.0 | `02cf8da9-0b6f-4070-93da-92c9cc3ab43e` |
| Service — auth app | identity-service | `2db54fde-c125-41ba-98e4-613e4d54eadb` |
| Service — database | Postgres | `c8cfd9dc-7458-45d2-b8b8-e0790ed3f9cc` |
| Service — cache | Redis | `9c672285-0dca-4e96-b93d-22b1a902d5e4` |

| Item | Value |
|---|---|
| GitHub repo (remote `bworigin`) | `devciphercode/brandwise-2.0` |
| Deploy branch | `stage` |
| Build | `Dockerfile.core` (builds `core-service/`) |
| App | `uvicorn app.main:app` on port **8001** |

How this environment is wired
-----------------------------
- The `brandwise-2.0` service is connected to the GitHub repo and its source
  branch is set to `stage`, so **any push or merge to `stage` triggers an
  automatic build + deploy** to the `staging` environment. No manual step needed.
- It builds with `Dockerfile.core` (builds `core-service/`).
- Its `startCommand` is overridden to:
  `python -m alembic upgrade heads && uvicorn app.main:app --host 0.0.0.0 --port 8001`
  (`heads` is required because the migration graph has multiple heads; the
  Dockerfile's default `alembic upgrade head` fails on that).
- The Postgres database has the `uuid-ossp` extension enabled (migration `060`
  uses `uuid_generate_v4()`). This was enabled once against the staging Postgres;
  it is persisted in the database, so no per-boot step is needed.
- It has its own `Postgres` and `Redis` services inside the BW-staging project
  (no shared production data).
- **`identity-service`** is connected to the same repo (`stage` branch), builds
  from `identity-service/` with RAILPACK (mirrors production), listens on
  port **8080**, and shares the **same** Postgres as core via a separate
  `alembic_version_identity` table (core uses `core_alembic_version`).
- `identity-service` startCommand runs migrations in **two phases**
  (`alembic upgrade 019` then `alembic upgrade head`) because migration `020`
  opens its own AUTOCOMMIT connection to `ALTER TYPE resourcetype`, which is
  only visible after `001`–`019` commit. This mirrors how production was
  migrated incrementally.

Auto-deploy (push-to-stage → deploy)
------------------------------------
Already configured. Railway watches the `stage` branch of
`devciphercode/brandwise-2.0` and redeploys **both** `brandwise-2.0` and
`identity-service` on new commits.

To confirm or change it later:

```bash
railway environment edit \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service-config brandwise-2.0 source.branch stage \
  --message "Point staging at stage branch"
```

> Note: Railway also has a `production` environment inside BW-staging. It is
> currently unused. Do **not** point its branch to `stage` unless you
> intentionally want a separate production environment in this project.

Manual deploy commands
----------------------
### Preferred: redeploy from the configured source (pulls latest `stage`)
```bash
railway redeploy \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 \
  --from-source --yes
```

### Alternative: deploy from a local checkout of `stage`
```bash
cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be
git checkout stage
railway up \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 \
  --detach -m "deploy stage"
```

### Verify deploy status
```bash
railway deployment list \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 --json
```

Environment variables
---------------------
The staging service variables were seeded from the production `core-service`
and then overridden for staging:

| Variable | Staging value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (auto-resolves to BW-staging Postgres) |
| `IDENTITY_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (same staging Postgres) |
| `REDIS_URL` | `${{Redis.REDIS_URL}}/0` |
| `REDIS_WAREHOUSE_URL` | `${{Redis.REDIS_URL}}/1` |
| `ENVIRONMENT` | `staging` |
| `PORT` | `8001` |

All other variables (`SECRET_KEY`, AWS/S3 keys, `QR_BASE_URL`, `CORS_ORIGINS`,
`PYTHONPATH`, `UPLOAD_DIR`, etc.) are copied from production `core-service`.

`identity-service` variables were seeded from production `identity-service` and
overridden for staging:

| Variable | Staging value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (same shared Postgres as core) |
| `CORE_SERVICE_URL` | `http://brandwise-20.railway.internal:8001` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `ENVIRONMENT` | `staging` |
| `SECRET_KEY` | same as core (required for JWT validation across services) |

Core ↔ identity wiring (both use internal Railway domains):
- core `IDENTITY_SERVICE_URL` → `http://identity-service.railway.internal:8080`
- identity `CORE_SERVICE_URL` → `http://brandwise-20.railway.internal:8001`

To review/change them:

```bash
railway variable list \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 --json
```

Known caveats / TODOs
---------------------
1. **Fresh empty database.** Both services share one Postgres; migrations run
   automatically on boot (core runs `alembic upgrade heads`, identity runs the
   two-phase migration above). Seed data (orgs, admin user, chart of accounts,
   permissions, etc.) still needs to be loaded for a fully usable staging
   environment.
2. **Redis is Railway-managed (plaintext, internal)** rather than the production
   external Valkey (`rediss://`). Fine for staging; do not use staging Redis for
   production workloads.
3. **No public domain yet** on `brandwise-2.0` or `identity-service`. Add a
   Railway domain (`railway domain`) when you need public URLs.

Quick health checks after deploy
--------------------------------
```bash
railway status
# or fetch runtime logs:
railway logs \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 --lines 100
```
Once a public domain is added to `brandwise-2.0`, hit `https://<service-url>/health`.
