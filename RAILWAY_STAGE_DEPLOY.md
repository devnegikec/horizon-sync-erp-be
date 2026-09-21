# Railway Stage Deploy — Horizon Sync (BW-staging)

Quick reference for deploying the **`stage`** branch of `bworigin`
(`github.com/devciphercode/brandwise-2.0`) to the dedicated **BW-staging**
Railway project, with automatic deploys on every push/merge to `stage`.

> Staging counterpart of `RAILWAY_FAST_DEPLOY.md`. Read that file first for
> general Railway CLI setup, token creation, and troubleshooting.

---

## Resource map (IDs)

| Resource | Name | ID |
|---|---|---|
| Project | BW-staging | `fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090` |
| Environment ( **target** ) | staging | `42a3b024-6059-47e2-a977-0e4377ef6e13` |
| Environment (unused for now) | production | `5fd250b5-ddf5-429c-9b2b-3274c3d5a2d7` |
| Service — core app | `brandwise-2.0` | `02cf8da9-0b6f-4070-93da-92c9cc3ab43e` |
| Service — auth app | `identity-service` | `2db54fde-c125-41ba-98e4-613e4d54eadb` |
| Service — database | `Postgres` | `c8cfd9dc-7458-45d2-b8b8-e0790ed3f9cc` |
| Service — cache | `Redis` | `9c672285-0dca-4e96-b93d-22b1a902d5e4` |

| Item | Value |
|---|---|
| GitHub repo (remote `bworigin`) | `devciphercode/brandwise-2.0` |
| Deploy branch | `stage` |
| Core build | root `Dockerfile` (byte-identical to `Dockerfile.core`) → builds `core-service/`, app on port **8001** |
| Identity build | `identity-service/Dockerfile` (builder `RAILPACK`, root dir `identity-service/`) → app on port **8080** |
| Old production project (for reference) | `7abe5082-844c-4791-8158-f47e14fb68cb` |

> **Note:** BW-staging is a **project**, and `staging` is the **environment**
> inside it. Don't confuse the project-level `production` environment (unused)
> with the old production project (`horizon-sync-test`).

---

## How the environment is wired

- `brandwise-2.0` — the core app. `startCommand` is overridden to:
  `python -m alembic upgrade heads && uvicorn app.main:app --host 0.0.0.0 --port 8001`
  (`heads` is required — the migration graph has multiple heads; the
  Dockerfile's default `alembic upgrade head` fails on that).
- `identity-service` — the auth app. Shares the **same** Postgres as core via a
  separate `alembic_version_identity` table (core uses `core_alembic_version`).
  Its `startCommand` runs migrations in **two phases**
  (`alembic upgrade 019` then `alembic upgrade head`) because migration `020`
  opens its own AUTOCOMMIT connection to `ALTER TYPE resourcetype`, which is
  only visible after `001`–`019` commit.
- The Postgres database has the `uuid-ossp` extension enabled (migration `060`
  uses `uuid_generate_v4()`). Persisted in the database — no per-boot step.
- It has its own `Postgres` and `Redis` services inside BW-staging
  (no shared production data).
- Core ↔ identity wiring (internal Railway domains):
  - core `IDENTITY_SERVICE_URL` → `http://identity-service.railway.internal:8080`
  - identity `CORE_SERVICE_URL` → `http://brandwise-20.railway.internal:8001`

### Environment variables

Core (`brandwise-2.0`) — seeded from production `core-service`, then overridden:

| Variable | Staging value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `IDENTITY_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}/0` |
| `REDIS_WAREHOUSE_URL` | `${{Redis.REDIS_URL}}/1` |
| `ENVIRONMENT` | `staging` |
| `PORT` | `8001` |

Identity (`identity-service`) — seeded from production `identity-service`:

| Variable | Staging value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (shared with core) |
| `CORE_SERVICE_URL` | `http://brandwise-20.railway.internal:8001` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `ENVIRONMENT` | `staging` |
| `SECRET_KEY` | same as core (required for cross-service JWT validation) |

Review / change them:

```bash
railway variable list \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 --json
```

---

## Auto-deploy on push / merge to `stage`

Auto-deploy is handled by **GitHub Actions**
(`.github/workflows/deploy-stage.yml`), **not** Railway's native Git
integration.

### Why not Railway's native Git auto-deploy?

Railway's Git integration *was* pointed at `stage`, but Railway gates
Git-triggered deployments that come from a GitHub author it does not recognise
as a project member — the deployment lands in the **`NEEDS_APPROVAL`** state and
never builds until someone clicks *Approve* in the dashboard. Because commits to
`stage` are authored by `devnegikec` and the Railway project is owned by
`info@ciphercode.ai`, every push stalled at `NEEDS_APPROVAL`.

To make deploys fully automatic, the native Git trigger is **disabled** and the
GitHub Actions workflow performs the deploy instead. The workflow is
authenticated with a project token, so its deployments are never subject to the
approval gate.

> If you'd rather use Railway's native auto-deploy, invite the GitHub user who
> authors the commits to the Railway project (any role), then re-enable
> `source.branch = stage` for both services.

### Required repository secret

| Secret | Value |
|---|---|
| `RAILWAY_TOKEN` | A **project token** for BW-staging (Railway → project → **Settings → Tokens**), scoped to the `staging` environment |

The project / environment / service IDs are hard-coded in the workflow (they are
not secret). No other secrets are required.

### What the workflow does

On every push to `stage` that touches `core-service/**`, `identity-service/**`,
`Dockerfile.core`, `Dockerfile.identity`, `railway.toml`, or the workflow
itself, it:

1. checks out the repo,
2. installs the Railway CLI,
3. runs `railway up` for `brandwise-2.0`, then for `identity-service`,
   targeting the BW-staging project + `staging` environment.

`railway up` uploads the checked-out source (source = uploaded files), so the
deployment has no Git commit author and bypasses the approval gate.

Watch runs at **Actions → Deploy to Railway (BW-staging)**.

---

## Manual deploy commands

### Deploy from a local `stage` checkout (uploads the working tree)

> The services no longer have a Git source branch configured (native auto-deploy
> is disabled), so `railway redeploy --from-source` is **not** available — use
> `railway up`.

```bash
cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be
git checkout stage
railway up \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 \
  --detach -m "deploy stage"
```

Repeat with `--service identity-service` for the auth app.

### Verify deploy status

```bash
railway deployment list \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 --json
```

### Approve a stalled deployment

If a deployment is stuck in `NEEDS_APPROVAL`, open the service in the Railway
dashboard and click **Approve** — or switch to the GitHub Actions flow above,
which has no approval gate.

---

## Re-enabling Railway's native auto-deploy (optional)

The native Git trigger is disabled by leaving `source.branch` **empty** for both
services. To go back to Railway-native auto-deploys (and remove the need for the
GitHub Actions workflow):

```bash
railway environment edit \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service-config brandwise-2.0 source.branch stage \
  --message "Point staging at stage branch"
```

Repeat with `source.branch stage` for `identity-service` (which also keeps its
`source.rootDirectory = identity-service/`). **Then delete
`.github/workflows/deploy-stage.yml`** so a single push doesn't produce two
deployments — and make the GitHub author a project member, otherwise deployments
will return to the `NEEDS_APPROVAL` state.

> There is also a `production` environment inside BW-staging. It is currently
> unused. Do **not** point it at `stage` unless you intentionally want a separate
> production environment in this project.

---

## Quick health checks after deploy

```bash
railway status -p fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 -e 42a3b024-6059-47e2-a977-0e4377ef6e13

# runtime logs
railway logs \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0 --lines 100

# build logs (migrations run at container start, so check deploy logs)
railway logs -b \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090 \
  --environment 42a3b024-6059-47e2-a977-0e4377ef6e13 \
  --service brandwise-2.0
```

Once a public domain is added to `brandwise-2.0`, hit `https://<service-url>/health`.

---

## Known caveats / TODOs

1. **Fresh empty database.** Both services share one Postgres; migrations run
   automatically on boot. Seed data (orgs, admin user, chart of accounts,
   permissions, etc.) still needs to be loaded for a fully usable staging
   environment.
2. **Redis is Railway-managed** (plaintext, internal) rather than the production
   external Valkey (`rediss://`). Fine for staging; don't use it for production
   workloads.
3. **No public domain yet** on `brandwise-2.0` or `identity-service`. Add a
   Railway domain (`railway domain`) when you need public URLs.
4. **Railway, don't let the native Git trigger race the workflow.** If native
   auto-deploy is ever re-enabled, remove the GitHub Actions workflow first (or
   vice-versa) so a single push doesn't produce two deployments.
