Railway Fast Deploy — Horizon Sync
=================================

Purpose
-------
Quick reference for interactive and non-interactive Railway deployments of the Horizon Sync services (core-service and identity-service).

Files / Scripts
---------------
- `deploy_to_railway.sh` — main deploy script (repo root).
- `deploy_core_to_railway.sh` — wrapper that deploys `core-service`.
- `deploy_identity_to_railway.sh` — wrapper that deploys `identity-service`.

Prerequisites
-------------
- Railway CLI installed: `npm i -g @railway/cli` (or see Railway docs).
- Docker available locally (used by `railway up` builds).
- Git (to confirm branch/status) and a local checkout of the repo.

Get a Railway token
-------------------
1. Sign in to https://railway.app
2. Avatar → Account → API Keys / Tokens → Create Token
3. Copy token (you won't be able to view it again). Use it as `RAILWAY_TOKEN`.

Quick commands
--------------
# Make scripts executable (once)
chmod +x deploy_to_railway.sh deploy_core_to_railway.sh deploy_identity_to_railway.sh

# Interactive (login & link handled by CLI)
./deploy_core_to_railway.sh -s horizon-sync-be/core-service -e production -m

# Non-interactive (using token + project id)
RAILWAY_TOKEN=your_token_here ./deploy_core_to_railway.sh -p <PROJECT_ID> -s horizon-sync-be/core-service -e production -m

# Identity service (wrapper)
RAILWAY_TOKEN=your_token_here ./deploy_identity_to_railway.sh -p <PROJECT_ID> -e production -m

What the scripts do
--------------------
- `deploy_to_railway.sh` will:
  - check for `railway` CLI,
  - login (non-interactive if `RAILWAY_TOKEN` is provided, otherwise interactive),
  - `railway link` to associate the local directory with a Railway project (non-interactive if `-p` given),
  - `railway up` to build and deploy the specified service directory,
  - optionally `railway run -- make migrate` when `-m` is passed.

Notes / Tips
-----------
- If you get "Invalid RAILWAY_TOKEN", create a fresh token in the Railway dashboard and retry.
- If the script fails saying `Service directory 'core-service' does not exist`, pass the full path relative to repo root: `-s horizon-sync-be/core-service`.
- Use `railway status` and the Railway web dashboard to inspect deployed services and recent builds.
- The scripts call `make migrate` remotely; if your migrations command differs, edit `deploy_to_railway.sh` where `railway run -- make migrate` appears.

Troubleshooting
---------------
- "railway up failed": check the build logs in the Railway dashboard for build/container errors.
- Authentication issues: run `railway login` interactively to validate OAuth flow.
- Permission issues on scripts: run `chmod +x` on the scripts.

CI / GitHub Actions
-------------------
- Add `RAILWAY_TOKEN` as a GitHub secret and run the wrapper in a workflow step:

```yaml
- name: Deploy core to Railway
  run: RAILWAY_TOKEN=${{ secrets.RAILWAY_TOKEN }} ./horizon-sync-be/deploy_core_to_railway.sh -p <PROJECT_ID> -s horizon-sync-be/core-service -e production -m
```

Checklist before pressing deploy
--------------------------------
- Commit & push the branch you want to deploy.
- Confirm `railway link` points to the expected Railway project/environment.
- Ensure environment variables required by the service are configured in Railway (via Dashboard or `railway variables` command).
- Confirm migrations are ready and compatible with the running DB (backup first on production).

Quick health checks after deploy
-------------------------------
- `railway status`
- Visit service health endpoint: `curl -s https://<service-url>/health` (replace with actual URL shown in Railway dashboard)

Contact
-------
If something in this repo needs a deploy tweak, add a short note to `RAILWAY_DEPLOYMENT_PLAN.md` or open an issue in the project repo.
