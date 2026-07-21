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

### Step 4: Set Up GitHub CI/CD (Auto-Deploy on `dev` Push)

Railway has **native GitHub integration** — no need for complex GitHub Actions!

Option A: **Railway Native Git Integration (Recommended)**

1. Go to your Railway project → **Settings** → **GitHub**
2. Connect your GitHub repo
3. Under **Deploy Triggers**, set:
   - **Branch**: `dev`
   - **Auto-deploy**: ON
4. Each push to `dev` triggers an automatic deploy!

Option B: **GitHub Actions (More Control)**

Create `.github/workflows/deploy-dev.yml`:

```yaml
name: Deploy to Railway (Dev)

on:
  push:
    branches:
      - dev

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install Railway CLI
        run: |
          curl -fsSL https://railway.com/install.sh | sh

      - name: Deploy Identity Service
        run: |
          cd identity-service
          railway up --service=identity-service --environment=dev --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy Core Service
        run: |
          cd core-service
          railway up --service=core-service --environment=dev --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### Step 5: Run Database Migrations

Railway can auto-run migrations. Create a `railway.json` in each service directory:

Or set up a **start command override** in Railway dashboard:

```
bash -c "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

### Step 6: Set Up a Domain (Optional)

```bash
railway domain --environment dev
```

This gives you: `https://identity-service.up.railway.app`

---

## 🔄 CI/CD Flow (Branch → Deploy)

```mermaid
gitGraph
    commit id: "initial"
    branch dev
    checkout dev
    commit id: "feat: new API"
    commit id: "fix: bug"
    checkout main
    merge dev
```

| Branch | Environment | Auto-Deploy?           |
| ------ | ----------- | ---------------------- |
| `main` | Production  | ❌ Manual only         |
| `dev`  | Test/Dev    | ✅ Auto-deploy on push |

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

| Issue                | Solution                                                                                |
| -------------------- | --------------------------------------------------------------------------------------- |
| Service won't start  | Check logs: `railway logs --service=identity-service`                                   |
| DB connection failed | Verify `${{Postgres.DATABASE_URL}}` is set as env var                                   |
| CORS errors          | Set `CORS_ORIGINS=*` for test env                                                       |
| Migration fails      | Run manually: `railway run --service=identity-service "python -m alembic upgrade head"` |
| Out of credits       | Check usage: `railway billing`                                                          |

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

- [ ] Create Upstash Redis (free tier)
- [ ] Run `railway init` to create project
- [ ] Deploy identity-service with `railway up`
- [ ] Deploy core-service with `railway up`
- [ ] Add PostgreSQL: `railway add --database postgresql`
- [ ] Create `dev` environment
- [ ] Set all environment variables
- [ ] Run database migrations
- [ ] Connect GitHub repo in Railway dashboard
- [ ] Set `dev` branch for auto-deploy
- [ ] Push to `dev` → verify auto-deploy works!
