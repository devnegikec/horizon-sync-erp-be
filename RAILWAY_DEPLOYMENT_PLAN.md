# 🚀 Horizon Sync - Railway Deployment Plan

## Architecture: What Gets Deployed Where

```
┌─────────────────────────────────────────────────────────┐
│                     Railway ($5 Hobby)                    │
│                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │   Identity    │ │    Core      │ │   PostgreSQL     │ │
│  │   Service     │ │   Service    │ │   (Railway)      │ │
│  │   :8000       │ │   :8001      │ │                  │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
          │                      │
          ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│   Upstash Redis  │   │   SMTP (Gmail)   │
│   (Free Tier)    │   │   (Existing)     │
└──────────────────┘   └──────────────────┘
```

## 💰 Cost Breakdown for Test Environment

| Resource                 | Provider | Plan              | Cost                         |
| ------------------------ | -------- | ----------------- | ---------------------------- |
| Identity Service (512MB) | Railway  | Hobby             | $5/mo credit covers services |
| Core Service (512MB)     | Railway  | Hobby             | ↑ same plan                  |
| PostgreSQL (1GB)         | Railway  | Included in Hobby | $0 (within $5 credit)        |
| Redis (256MB)            | Railway  | Included in Hobby | $0 (within $5 credit)        |
| **Total Estimated**      |          |                   | **$5/mo**                    |

> **Note**: Services auto-sleep when not used. For occasional testing, actual cost may be $2-4/mo.
> All databases (PostgreSQL + Redis) run directly on Railway — no external providers needed.

---

## 📋 Step-by-Step Deployment Guide

### Step 1: Set Up Free External Redis (Upstash)

1. Go to https://console.upstash.com/redis
2. Click **Create Redis Database**
3. Choose **Free tier** (256MB, 1 database)
4. Select a region close to Railway (e.g., `us-west1` or `us-east4`)
5. Click **Create**
6. Copy the **REST URL** and **Token** — you'll need these as env vars

```
UPSTASH_REDIS_URL=redis://default:xxxxx@your-db.upstash.io:6379
```

### Step 2: Create Railway Project & Services

```bash
# 1. Create a new Railway project
railway init --name "horizon-sync-test"

# 2. Deploy Identity Service (from identity-service directory)
cd identity-service
railway up --service-name=identity-service --detach

# 3. Deploy Core Service (from core-service directory)
cd ../core-service
railway up --service-name=core-service --detach

# 4. Add PostgreSQL database
railway add --database postgresql

# 5. Create a "dev" environment
railway environment create dev
```

### Step 3: Configure Environment Variables

Set these in Railway dashboard or via CLI:

#### Identity Service Variables

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=<generate-a-strong-secret-key>
ENVIRONMENT=test
ACCESS_TOKEN_EXPIRE_MINUTES=4320
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=*
CORE_SERVICE_URL=http://core-service.railway.internal:8001
REDIS_URL=<upstash-redis-url>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=devnegikec@gmail.com
SMTP_PASSWORD=<your-app-password>
SMTP_FROM_EMAIL=devnegikec@gmail.com
SMTP_FROM_NAME=HorizonSync-Test
```

#### Core Service Variables

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=<same-secret-key>
ENVIRONMENT=test
CORS_ORIGINS=*
IDENTITY_SERVICE_URL=http://identity-service.railway.internal:8000
REDIS_URL=<upstash-redis-url>
```

### Step 4: Set Up GitHub CI/CD (✅ Working)

The project uses **GitHub Actions** with **Railway config-as-code** (`railway.toml`). Two files control deployment:

#### 4a. `railway.toml` (repo root) — Config-as-Code

```toml
[build]
builder = "dockerfile"
watchPatterns = ["**/*"]

[services.identity-service]
source = "identity-service/"
startCommand = "bash -c 'python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'"

[services.identity-service.build]
dockerfilePath = "Dockerfile.identity"

[services.identity-service.deploy]
healthcheckPath = "/health"
restartPolicyMaxRetries = 3

[services.core-service]
source = "core-service/"
startCommand = "bash -c 'python -m alembic upgrade heads || true && uvicorn app.main:app --host 0.0.0.0 --port 8001'"

[services.core-service.build]
dockerfilePath = "Dockerfile.core"

[services.core-service.deploy]
healthcheckPath = "/health"
restartPolicyMaxRetries = 3
```

> **Key detail**: `startCommand` runs `alembic upgrade head(s)` before starting uvicorn — so **DB migrations run automatically on every deploy**. No separate migration step needed. Core uses `upgrade heads` (plural) because it has diverged migration branches.

#### 4b. `.github/workflows/deploy-dev.yml` — CI Pipeline

```yaml
name: Deploy to Railway (Dev)

on:
  push:
    branches:
      - dev
    paths:
      - "identity-service/**"
      - "core-service/**"
      - "docker-compose.yml"
      - ".github/workflows/deploy-dev.yml"

concurrency:
  group: railway-dev
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: dev

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install Railway CLI
        run: |
          curl -fsSL https://railway.com/install.sh | sh
          echo "$HOME/.railway/bin" >> $GITHUB_PATH

      - name: Deploy Identity Service
        run: |
          railway up ./identity-service \
            --path-as-root \
            --service="${{ secrets.RAILWAY_IDENTITY_SERVICE_ID }}" \
            --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy Core Service
        run: |
          railway up ./core-service \
            --path-as-root \
            --service="${{ secrets.RAILWAY_CORE_SERVICE_ID }}" \
            --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deployment Summary
        if: always()
        run: |
          echo "### 🚀 Railway Deployment Complete" >> $GITHUB_STEP_SUMMARY
          echo "| Service | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|---------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| Identity Service | ${{ job.status }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Core Service | ${{ job.status }} |" >> $GITHUB_STEP_SUMMARY
```

> **Search & Nginx** deploy steps are commented out — uncomment when those services are ready.

### Step 5: Running Manual DB Migrations

Migrations run **automatically** on deploy via `startCommand`. If you need to run them manually:

```bash
# Create a new migration locally, then deploy
cd core-service
python -m alembic revision --autogenerate -m "description"
git add . && git commit -m "migrations: description"
git push bworigin dev   # triggers CI deploy → migrations run on startup

# Or run directly on Railway (without redeploy)
railway run --service=identity-service --environment=production "python -m alembic upgrade head"
railway run --service=core-service --environment=production "python -m alembic upgrade heads"
```

### Step 6: Set Up a Domain (Optional)

```bash
railway domain --environment production
```

This gives you: `https://identity-service-production-xxxx.up.railway.app`

---

## 🔄 CI/CD Flow (✅ Working)

| Trigger               | What Happens                                                                 |
| --------------------- | ---------------------------------------------------------------------------- |
| Push to `dev` branch  | GitHub Actions builds & deploys Identity → Core via Railway CLI              |
| DB Migrations         | Run **automatically** on deploy via `startCommand` in `railway.toml`         |
| Manual redeploy       | Go to GitHub Actions → "Deploy to Railway (Dev)" → Run workflow              |

| Branch | Environment | Auto-Deploy?           | Status  |
| ------ | ----------- | ---------------------- | ------- |
| `main` | Production  | ❌ Manual only         | —       |
| `dev`  | Production  | ✅ Auto-deploy on push | Working |

---

## 📊 Monitoring & Logs

```bash
# View all service logs
railway logs --environment dev

# View specific service
railway logs --service=identity-service --environment dev

# View deployment status
railway status --json

# Open Railway dashboard
railway open
```

---

## 🔧 Troubleshooting

| Issue                       | Solution                                                                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------- |
| Service won't start         | Check logs: `railway logs --service=identity-service`                                           |
| DB connection failed        | Verify `DATABASE_URL` is set as env var on Railway                                              |
| CORS errors                 | Set `CORS_ORIGINS=*` for test env                                                               |
| Migration fails             | Migrations run in `startCommand`. Check Railway logs for the service.                           |
| `railway: command not found`| CLI installs to `$HOME/.railway/bin` — ensure `$GITHUB_PATH` includes it in CI                  |
| `Environment not found`     | Use `--environment=production` (dev env may not exist on Railway)                               |
| `Service not found`         | Check `RAILWAY_*_SERVICE_ID` secrets are set in GitHub → Settings → Secrets → Actions           |
| `--service=""` (empty)      | Missing service ID secret — add `RAILWAY_IDENTITY_SERVICE_ID` / `RAILWAY_CORE_SERVICE_ID`       |
| Out of credits              | Check usage: `railway billing`                                                                  |
| PYTHONPATH warning          | Normal — Railway skips env vars that execute code in local processes. Harmless.                 |

---

## 🔗 Service URLs

| Service          | Public URL                                                | Internal URL                                    |
| ---------------- | --------------------------------------------------------- | ----------------------------------------------- |
| Identity Service | `https://identity-service-production-a1eb.up.railway.app` | `http://identity-service.railway.internal:8000` |
| Core Service     | `https://core-service-production-66e9.up.railway.app`     | `http://core-service.railway.internal:8001`     |
| Redis            | `redis://default:***@redis.railway.internal:6379`         | Internal only                                   |
| Supabase DB      | `db.icpjudwiclyhcgbdstam.supabase.co:5432`                | External                                        |

## 📦 Service IDs

| Service          | ID                                     |
| ---------------- | -------------------------------------- |
| identity-service | `495ec8e8-639b-423a-8184-e88a22b70539` |
| core-service     | `ce06d3cb-743c-4ed3-b1f1-c6b4583f5480` |
| Redis            | `746957a2-3643-459d-91e6-8d9fee469895` |

## 🔐 GitHub Actions Secrets Required

Add these to your GitHub repo → Settings → Secrets → Actions:

| Secret                        | Value                                                       |
| ----------------------------- | ----------------------------------------------------------- |
| `RAILWAY_TOKEN`               | Get from `railway login --browserless` or Railway dashboard |
| `RAILWAY_IDENTITY_SERVICE_ID` | `495ec8e8-639b-423a-8184-e88a22b70539`                      |
| `RAILWAY_CORE_SERVICE_ID`     | `ce06d3cb-743c-4ed3-b1f1-c6b4583f5480`                      |

## ✅ Deployment Checklist

- [x] Create Railway project
- [x] Deploy identity-service
- [x] Deploy core-service
- [x] Add PostgreSQL database
- [x] Set all environment variables
- [x] Create `railway.toml` (config-as-code)
- [x] Create `.github/workflows/deploy-dev.yml`
- [x] Set `RAILWAY_TOKEN` GitHub secret
- [x] Set `RAILWAY_IDENTITY_SERVICE_ID` GitHub secret
- [x] Set `RAILWAY_CORE_SERVICE_ID` GitHub secret
- [x] Push to `dev` → verify auto-deploy works
- [ ] Set up Redis (Upstash or Railway)
- [ ] Deploy search-service (commented out, ready when needed)
- [ ] Deploy nginx-gateway (commented out, ready when needed)
- [ ] Set up custom domain
