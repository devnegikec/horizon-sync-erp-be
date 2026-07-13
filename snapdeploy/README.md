# 🚀 SnapDeploy Deployment Guide

Deploy Horizon Sync ERP as 3 independent containers on [SnapDeploy](https://snapdeploy.dev),
with **Neon** for PostgreSQL and **Upstash** for Redis.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  Frontend (SPA)                   │
│            Vercel / Netlify / SnapDeploy          │
└──────────────────┬───────────────────────────────┘
                   │ HTTPS
                   │
┌──────────────────┼───────────────────────────────┐
│          3 SnapDeploy Apps (this repo)            │
│                                                   │
│  ┌─────────────────┐  Port 8000   Medium ($25)    │
│  │ Identity Service │  /api/v1/identity/*          │
│  └────────┬────────┘                              │
│           │ calls                                  │
│  ┌────────┴────────┐  Port 8001   Medium ($25)    │
│  │  Core Service    │  /api/v1/*                   │
│  └────────┬────────┘                              │
│           │ calls                                  │
│  ┌────────┴────────┐  Port 8002   Small ($12)     │
│  │ Search Service   │  /api/v1/search/*            │
│  └─────────────────┘                              │
└──────────────────────────────────────────────────┘
                   │                    │
          ┌────────┴────────┐  ┌───────┴────────┐
          │  🗄️ Neon (PG)   │  │ ⚡ Upstash     │
          │  neon.tech       │  │  upstash.com   │
          │  Serverless SQL  │  │  Serverless KV │
          └─────────────────┘  └────────────────┘
```

---

## Prerequisites

- [SnapDeploy](https://snapdeploy.dev) account (free tier works for testing)
- [Neon](https://neon.tech) account (free tier: 0.5 GB storage, 1 project)
- [Upstash](https://upstash.com) account (free tier: 10K commands/day)
- GitHub repo with this code pushed

---

## Step 1: Set Up Neon PostgreSQL

1. Go to [neon.tech](https://neon.tech) → **Create Project**
2. After creation, go to **Dashboard** → **SQL Editor**
3. Run these commands to create 3 databases:

```sql
CREATE DATABASE identity_db;
CREATE DATABASE core_db;
CREATE DATABASE search_db;
```

4. Go to **Dashboard** → **Connection Details**
5. Copy the connection string. It looks like:

```
postgresql://horizon_owner:xxxx@ep-cool-darkness-a1b2c3d4.us-east-2.aws.neon.tech/identity_db?sslmode=require
```

> ⚠️ **Important:** Each database has its own URL. Just change the DB name at the end of the URL for each service. Add `?sslmode=require` if not already present.

---

## Step 2: Set Up Upstash Redis

1. Go to [upstash.com](https://upstash.com) → **Create Database**
2. Select **Regional** for lowest latency (or Global if users are worldwide)
3. After creation, copy the **`REDIS_URL`** from the **Connect** tab. It looks like:

```
rediss://default:AVau_xxxx@us1-friendly-gibbon-12345.upstash.io:6379
```

> ⚠️ **Upstash uses `rediss://` (double s) for TLS.** The Dockerfiles are pre-configured to handle this.

---

## Step 3: Deploy Identity Service (FIRST)

1. **SnapDeploy → Create New App**
2. Connect GitHub repo, set:
   - **Dockerfile path:** `snapdeploy/identity.Dockerfile`
   - **Port:** `8000`
   - **Plan:** Medium ($25/mo) — 2 GB RAM, 1 vCPU
3. Add **Environment Variables** (see full list below)
4. Click **Deploy**
5. Save the URL → e.g. `https://horizon-identity-a1b2.snapdeploy.dev`

### Identity Service — Env Vars Checklist

```
✅ DATABASE_URL=postgresql://<neon-user>:<pass>@<neon-host>.neon.tech/identity_db?sslmode=require
✅ SECRET_KEY=<openssl rand -hex 32>
✅ ENVIRONMENT=production
✅ DEBUG=false
✅ CORS_ORIGINS=https://your-frontend-domain.com
✅ EMAIL_ENABLED=true
✅ SMTP_HOST=smtp.gmail.com
✅ SMTP_PORT=587
✅ SMTP_USERNAME=your-email@gmail.com
✅ SMTP_PASSWORD=<gmail-app-password>
✅ SMTP_FROM_EMAIL=your-email@gmail.com
✅ COOKIE_SECURE=true
☐ CORE_SERVICE_URL=<set AFTER deploying Core>
```

---

## Step 4: Deploy Core Service (SECOND)

1. **SnapDeploy → Create New App** (same repo)
2. Set:
   - **Dockerfile path:** `snapdeploy/core.Dockerfile`
   - **Port:** `8001`
   - **Plan:** Medium ($25/mo) or Large ($45/mo) for heavy use
3. Add Environment Variables (see below)
4. Click **Deploy**
5. Save the URL → e.g. `https://horizon-core-c3d4.snapdeploy.dev`

### Core Service — Env Vars Checklist

```
✅ DATABASE_URL=postgresql://<neon-user>:<pass>@<neon-host>.neon.tech/core_db?sslmode=require
✅ SECRET_KEY=<same-key-as-identity>
✅ ENVIRONMENT=production
✅ DEBUG=false
✅ CORS_ORIGINS=https://your-frontend-domain.com
✅ IDENTITY_DATABASE_URL=postgresql://<neon-user>:<pass>@<neon-host>.neon.tech/identity_db?sslmode=require
✅ IDENTITY_SERVICE_URL=https://identity-xxxxx.snapdeploy.dev
✅ REDIS_URL=rediss://default:<upstash-pass>@<upstash-host>.upstash.io:6379
✅ REDIS_WAREHOUSE_URL=rediss://default:<upstash-pass>@<upstash-host>.upstash.io:6379/1
✅ EMAIL_ENABLED=true
✅ SMTP_HOST=smtp.gmail.com
✅ SMTP_PORT=587
✅ SMTP_USERNAME=your-email@gmail.com
✅ SMTP_PASSWORD=<gmail-app-password>
✅ SMTP_FROM_EMAIL=your-email@gmail.com
```

---

## Step 5: Deploy Search Service (THIRD)

1. **SnapDeploy → Create New App** (same repo)
2. Set:
   - **Dockerfile path:** `snapdeploy/search.Dockerfile`
   - **Port:** `8002`
   - **Plan:** Small ($12/mo) — 512 MB, 0.25 vCPU
3. Add Environment Variables (see below)
4. Click **Deploy**
5. Save the URL → e.g. `https://horizon-search-e5f6.snapdeploy.dev`

### Search Service — Env Vars Checklist

```
✅ DATABASE_URL=postgresql://<neon-user>:<pass>@<neon-host>.neon.tech/search_db?sslmode=require
✅ SECRET_KEY=<same-key-as-identity>
✅ ENVIRONMENT=production
✅ DEBUG=false
✅ CORS_ORIGINS=https://your-frontend-domain.com
✅ IDENTITY_SERVICE_URL=https://identity-xxxxx.snapdeploy.dev
✅ CORE_SERVICE_URL=https://core-xxxxx.snapdeploy.dev
✅ REDIS_URL=rediss://default:<upstash-pass>@<upstash-host>.upstash.io:6379
✅ SYNC_SERVICE_USERNAME=admin@example.com
✅ SYNC_SERVICE_PASSWORD=<admin-password>
```

---

## Step 6: Finalize Cross-Service URLs

Go back and add the missing env vars, then **redeploy**:

| Service      | Add Env Var        | Value                               |
| ------------ | ------------------ | ----------------------------------- |
| **Identity** | `CORE_SERVICE_URL` | `https://core-xxxxx.snapdeploy.dev` |

No other service needs updating — Core and Search already have their URLs set during deployment.

---

## Step 7: Deploy Frontend

Your frontend SPA can go anywhere:

| Platform       | Why                                      |
| -------------- | ---------------------------------------- |
| **Vercel**     | Free, auto-deploys from GitHub, Edge CDN |
| **Netlify**    | Free, simple drag-and-drop               |
| **SnapDeploy** | 4th app with an Nginx Dockerfile         |

Configure the frontend to point:

- All `/api/v1/*` calls → **Core Service URL** (`https://core-xxxxx.snapdeploy.dev`)

---

## 📊 Monthly Cost Estimate

| Resource         | Provider   | Plan               | Price      |
| ---------------- | ---------- | ------------------ | ---------- |
| Identity Service | SnapDeploy | Medium             | **$25/mo** |
| Core Service     | SnapDeploy | Medium             | **$25/mo** |
| Search Service   | SnapDeploy | Small              | **$12/mo** |
| PostgreSQL       | Neon       | Free (0.5 GB)      | **$0/mo**  |
| Redis            | Upstash    | Free (10K cmd/day) | **$0/mo**  |
| **TOTAL**        |            |                    | **$62/mo** |

> Scale up Neon ($19/mo for 1 GB) and Upstash ($0.2/100K cmds) as you grow.

---

## 🔒 Security Checklist

- [ ] `SECRET_KEY` is the same 64-char hex string across all 3 services
- [ ] `COOKIE_SECURE=true` (HTTPS only)
- [ ] `CORS_ORIGINS` is locked to your actual frontend domain (not `*`)
- [ ] `DEBUG=false` in all services
- [ ] Neon database uses strong passwords (auto-generated by Neon)
- [ ] Upstash uses TLS (`rediss://`)
- [ ] SMTP uses app-specific passwords (not main account password)

---

## 🐛 Troubleshooting

| Problem                       | Check                                                                         |
| ----------------------------- | ----------------------------------------------------------------------------- |
| **Neon connection refused**   | URL has `?sslmode=require` at the end                                         |
| **Upstash timeout**           | URL starts with `rediss://` not `redis://`                                    |
| **Migrations fail**           | The correct database exists on Neon (`identity_db` / `core_db` / `search_db`) |
| **Core can't reach Identity** | `IDENTITY_SERVICE_URL` is the full `https://...snapdeploy.dev` URL            |
| **CORS errors**               | `CORS_ORIGINS` includes your frontend domain                                  |
| **SSL errors**                | `ca-certificates` is installed (it is — added in Dockerfile)                  |
| **Alembic version conflict**  | Run `python scripts/normalize_alembic_version.py` in SnapDeploy shell         |

---

## 🏠 Local Development (unchanged)

```bash
make up        # All services via Docker Compose
make down      # Stop everything
```

The files in `identity-service/Dockerfile`, `core-service/Dockerfile`, `search-service/Dockerfile`, and `docker-compose.yml` are **untouched**.
