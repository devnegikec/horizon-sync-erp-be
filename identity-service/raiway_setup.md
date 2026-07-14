Created 5 todos

Let me research Railway's deployment requirements and check your current files.

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/snapdeploy/identity.Dockerfile)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/snapdeploy/core.Dockerfile)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/snapdeploy/search.Dockerfile)

Fetched 3 resources

Fetched https://docs.railway.com/develop/cli

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/pyproject.toml#1-1), lines 1 to 30

Starting: _Create service-level Dockerfiles (identity/core/search)_ (3/5)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/identity-service)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/core-service)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/search-service)

There are already `Dockerfile`s in each service directory! Let me check them.

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/identity-service/Dockerfile)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/core-service/Dockerfile)

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/search-service/Dockerfile)

Searched for text `requests` (`**/search-service/requirements.txt`), no results

Read [](file:///Users/devnegi/Documents/www/horizon-sync-be/search-service/requirements.txt#1-1), lines 1 to 20

Now I have the full picture. Here's the plan:

## Railway Deployment Plan

**Good news**: Each service already has a Dockerfile in its directory — Railway will auto-detect them. The main fixes needed:

1. **Add migration step to each Dockerfile's CMD** (currently just starts uvicorn, no migrations)
2. **Fix search-service healthcheck** (uses `requests` but it's not in requirements.txt → switch to `curl`)
3. **Deploy with Railway CLI**

No changes needed for Neon/Upstash — just set them as environment variables in Railway dashboard.

Let me apply the fixes now:

```

```

```

```

```

```

Starting: _Install Railway CLI & deploy_ (4/4)

Let me install the Railway CLI and check if it's already available.

Ran terminal command: which railway 2>/dev/null && railway --version || echo "NOT_INSTALLED"

Ran terminal command: brew install railway

Ran terminal command: railway --version

Completed: _Install Railway CLI & deploy_ (4/4)

Here's the complete summary:

---

## ✅ Changes Made

| File       | What Changed                                                                                             |
| ---------- | -------------------------------------------------------------------------------------------------------- |
| Dockerfile | CMD now runs `alembic upgrade head` before uvicorn                                                       |
| Dockerfile | CMD now runs `alembic upgrade head` before uvicorn                                                       |
| Dockerfile | Added `curl` to deps, fixed healthcheck (was broken — `requests` not installed), CMD now runs migrations |

No `railway.toml` needed — Railway auto-detects everything from your Dockerfiles (port, healthcheck, start command).

---

## 🚀 Deploy to Railway — Step by Step

### 1. Login

```bash
railway login
```

This opens a browser. Log in with your Railway account.

### 2. Create project & services

```bash
# From project root, create the project
railway init

# Add each service (creates them in the Railway project)
cd identity-service && railway service add && cd ..
cd core-service && railway service add && cd ..
cd search-service && railway service add && cd ..
```

### 3. Set environment variables (via Railway dashboard or CLI)

For each service, set these in the **Railway dashboard → Service → Variables** (keep using Neon + Upstash, no Railway DB):

**Identity Service:**

```
DATABASE_URL=postgresql://...  (Neon)
SECRET_KEY=...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=...
SMTP_FROM_NAME=HorizonSync
PORT=8000
```

**Core Service:**

```
DATABASE_URL=postgresql://...  (Neon)
IDENTITY_DATABASE_URL=postgresql://...  (Neon, same DB)
SECRET_KEY=...  (same as identity)
IDENTITY_SERVICE_URL=https://identity-xxx.railway.app
REDIS_URL=rediss://...  (Upstash)
PORT=8001
```

**Search Service:**

```
DATABASE_URL=postgresql://...  (Neon)
SECRET_KEY=...
IDENTITY_SERVICE_URL=https://identity-xxx.railway.app
CORE_SERVICE_URL=https://core-xxx.railway.app
REDIS_URL=rediss://...  (Upstash)
PORT=8002
```

### 4. Deploy

```bash
# Deploy Identity first (others depend on it)
cd identity-service && railway up && cd ..

# Once Identity is live, deploy Core
cd core-service && railway up && cd ..

# Finally deploy Search
cd search-service && railway up && cd ..
```

### 5. After first deploy

Once Identity is up, grab its Railway URL (e.g., `https://identity-production-xxxx.up.railway.app`) and update `IDENTITY_SERVICE_URL` in Core/Search services, then redeploy them.

---

> ⚠️ **Important**: Deploy Identity **first**, then copy its Railway URL into Core/Search env vars before deploying them.

Made changes.
