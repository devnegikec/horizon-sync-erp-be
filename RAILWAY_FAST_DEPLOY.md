# Railway Fast Deploy — Horizon Sync

## Purpose

Quick reference for interactive and non-interactive Railway deployments of the Horizon Sync services (core-service and identity-service).

## Files / Scripts

- `deploy_to_railway.sh` — main deploy script (repo root).
- `deploy_core_to_railway.sh` — wrapper that deploys `core-service`.
- `deploy_identity_to_railway.sh` — wrapper that deploys `identity-service`.

## Prerequisites

- Railway CLI installed: `npm i -g @railway/cli` (or see Railway docs).
- Docker available locally (used by `railway up` builds).
- Git (to confirm branch/status) and a local checkout of the repo.

## Get a Railway token

1. Sign in to https://railway.app
2. Avatar → Account → API Keys / Tokens → Create Token
3. Copy token (you won't be able to view it again). Use it as `RAILWAY_TOKEN`.

## Quick commands

# Make scripts executable (once)

chmod +x deploy_to_railway.sh deploy_core_to_railway.sh deploy_identity_to_railway.sh

# Interactive (login & link handled by CLI)

./deploy_core_to_railway.sh -s horizon-sync-be/core-service -e production -m

# Non-interactive (using token + project id)

RAILWAY_TOKEN=your_token_here ./deploy_core_to_railway.sh -p <PROJECT_ID> -s horizon-sync-be/core-service -e production -m

# Identity service (wrapper)

RAILWAY_TOKEN=your_token_here ./deploy_identity_to_railway.sh -p <PROJECT_ID> -e production -m

## What the scripts do

- `deploy_to_railway.sh` will:
  - check for `railway` CLI,
  - login (non-interactive if `RAILWAY_TOKEN` is provided, otherwise interactive),
  - `railway link` to associate the local directory with a Railway project (non-interactive if `-p` given),
  - `railway up` to build and deploy the specified service directory,
  - optionally `railway run -- make migrate` when `-m` is passed.

## Notes / Tips

- **Migrations run automatically** on deploy: the `startCommand` in `railway.toml` already does `alembic upgrade heads || true` before starting uvicorn, so no separate `-m` / `make migrate` step is needed for Railway.
- If you get "Invalid RAILWAY_TOKEN", create a fresh token in the Railway dashboard and retry.
- If the script fails saying `Service directory 'core-service' does not exist`, pass the full path relative to repo root: `-s horizon-sync-be/core-service`.
- Use `railway status` and the Railway web dashboard to inspect deployed services and recent builds.
- The scripts call `make migrate` remotely; if your migrations command differs, edit `deploy_to_railway.sh` where `railway run -- make migrate` appears.

## Proven working command (2026-08-14)

This is the exact flow that successfully deployed `core-service` to Railway production (no token needed — uses browser OAuth).

```bash
# Run from the horizon-sync-be directory
cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be

# Login + deploy in ONE command (auth does not persist across separate terminal sessions)
railway login && railway up \
  -p 7abe5082-844c-4791-8158-f47e14fb68cb \
  -s core-service \
  -e production \
  -m "deploy bugfix-product-item-sync fixes" \
  -d
```

Key facts:

- Project ID: `7abe5082-844c-4791-8158-f47e14fb68cb`
- Core service ID: `ce06d3cb-743c-4ed3-b1f1-c6b4583f5480`
- `railway up` reads `railway.toml` (config-as-code) and builds `core-service` using `Dockerfile.core`.
- `-d` detaches; you get a build-logs URL to monitor in the browser.
- If upload fails with `500 Internal Server Error`, just retry — it is usually transient.

## Agent / scripted-session notes

- In a sandboxed terminal, Railway CLI auth does **not** persist between separate `run_in_terminal` calls — chain `railway login && railway up ...` in a single command.
- Browser OAuth auto-completes only when a browser is already authenticated; otherwise Railway falls back to a device code (`railway.com/activate?user_code=...`) that a human must complete.
- For fully non-interactive/CI use, set `RAILWAY_TOKEN` and run `railway login --ci --token "$RAILWAY_TOKEN"` first.

## Troubleshooting

- "railway up failed": check the build logs in the Railway dashboard for build/container errors.
- "Failed to upload code with status code 500 Internal Server Error": transient Railway upload error — retry the same command.
- "Not signed in. Run `railway login`": the CLI lost its auth state; run `railway login` again (chain it with `&&` before `railway up`).
- Browser won't open during login: complete the device-code flow at `https://railway.com/activate` with the code printed by the CLI.
- Permission issues on scripts: run `chmod +x` on the scripts.

## CI / GitHub Actions

- Add `RAILWAY_TOKEN` as a GitHub secret and run the wrapper in a workflow step:

```yaml
- name: Deploy core to Railway
  run: RAILWAY_TOKEN=${{ secrets.RAILWAY_TOKEN }} ./horizon-sync-be/deploy_core_to_railway.sh -p <PROJECT_ID> -s horizon-sync-be/core-service -e production -m
```

## Checklist before pressing deploy

- Commit & push the branch you want to deploy.
- Confirm `railway link` points to the expected Railway project/environment.
- Ensure environment variables required by the service are configured in Railway (via Dashboard or `railway variables` command).
- Confirm migrations are ready and compatible with the running DB (backup first on production).

## Quick health checks after deploy

- `railway status`
- Visit service health endpoint: `curl -s https://<service-url>/health` (replace with actual URL shown in Railway dashboard)

## Contact

If something in this repo needs a deploy tweak, add a short note to `RAILWAY_DEPLOYMENT_PLAN.md` or open an issue in the project repo.
