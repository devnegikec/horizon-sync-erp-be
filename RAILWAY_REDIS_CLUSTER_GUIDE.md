# Railway Redis Cluster Configuration Guide

> Scope: `horizon-sync-erp-be` services deployed on Railway
> Date: 2026-08-14

This guide covers **Redis in Railway cloud** — both the simple managed-Redis setup (what this project currently uses) and a true **Redis Cluster** (sharded) setup if you need horizontal scaling / high availability.

---

## 1. What the codebase uses Redis for

| Setting | DB | Purpose | Client |
|---|---|---|---|
| `REDIS_URL` | `.../0` | Search-service event stream (`app/events/publisher.py`, search-service consumer) | `redis` (sync) + `aioredis` |
| `REDIS_WAREHOUSE_URL` | `.../1` | 3D warehouse real-time pub/sub (`app/core/redis_pubsub.py`, `wms_3d.py`) | `redis` + `aioredis` |

Current defaults in `core-service/app/config.py`:
```python
redis_url: str = "redis://redis:6379/0"
redis_warehouse_url: str = "redis://redis:6379/1"
```

---

## 2. Options (pick one)

| Option | Provider | Clustering / HA | Effort | When to use |
|---|---|---|---|---|
| **A. Managed Redis** | Railway Redis plugin | single (replicated) | low | default, most projects |
| **B. Managed Redis (HA)** | Upstash / Aiven / Redis Cloud | replication + failover | low | prod without managing nodes |
| **C. Self-hosted Redis Cluster** | Your own services in Railway | true sharding (3×3) | high | high throughput, > single-node memory, pub/sub at scale |

> **Recommendation:** for this project, **Option A** (Railway Redis plugin) is enough. Your workload is pub/sub + a short event stream, not a large key space. Jump to §4 only if you specifically need sharding.

---

## 3. Option A — Managed Redis (Railway plugin / Upstash)

### 3.1 Provision

**Railway plugin (simplest):**
```bash
railway login
railway link                 # in horizon-sync-erp-be
railway add
# → select "Redis" plugin (or "Database" → Redis)
```
This creates a `Redis` service and exposes `${{Redis.REDIS_URL}}` to your app services.

**Upstash (existing approach in this repo):**
1. https://console.upstash.com/redis → **Create Redis Database**
2. Choose region close to your Railway project (e.g. `us-west1`)
3. Copy the connection string.

### 3.2 Environment variables

Set on each service (Railway dashboard → service → Variables, or via `railway variables`):

```bash
# shared events (search)
REDIS_URL=rediss://default:<password>@<host>.upstash.io:6379/0

# 3D warehouse events (separate logical DB)
REDIS_WAREHOUSE_URL=rediss://default:<password>@<host>.upstash.io:6379/1
```

> **TLS:** managed providers usually require `rediss://` (TLS). If the URL starts with `redis://`, append `?ssl=true` or change to `rediss://`. Upstash default is TLS on port `6379` — use `rediss://`.

### 3.3 Reference the Railway plugin (optional, config-as-code)

In `railway.toml` you can inject the plugin URL with a variable reference in the Railway dashboard:
```
REDIS_URL=${{Redis.REDIS_URL}}
REDIS_WAREHOUSE_URL=${{Redis.REDIS_URL}}/1
```
(Set these under each service's Variables, not in `railway.toml` — `railway.toml` is for build/deploy config.)

### 3.4 Verify

```bash
# from local machine against the managed URL
python - <<'PY'
import redis
r = redis.Redis.from_url("rediss://default:<p>@<host>.upstash.io:6379/0")
print(r.ping())          # True
PY
```

---

## 4. Option C — True Redis Cluster (sharded), self-hosted in Railway

Use this only if you outgrow a single Redis node. A real Redis Cluster needs **≥ 6 nodes** (3 masters + 3 replicas) and a code change to use the cluster client.

### 4.1 Architecture

```
 3 master nodes (shards, each owns 1/3 of key slots 0-16383)
 3 replica nodes (one per master)
 Clients use MOVED/REDIRECT to talk to the right shard
```

### 4.2 Railway services (config-as-code in `railway.toml`)

Add 6 lightweight services, or run one Redis Docker image per node. Example for a single node (repeat for 6, with different ports/IDs):

```toml
[services.redis-node-1]
source = "infra/redis"
startCommand = "redis-server /etc/redis/redis.conf"
```

`infra/redis/redis.conf` (identical on all nodes except `port` / `cluster-announce-ip`):
```
port 6379
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
protected-mode no
bind 0.0.0.0
```

After all nodes are up, form the cluster once (run from any node):
```bash
redis-cli --cluster create \
  <node1>:6379 <node2>:6379 <node3>:6379 \
  <node4>:6379 <node5>:6379 <node6>:6379 \
  --cluster-replicas 1
```

> Railway caveat: services discover each other via internal DNS (`<service>.railway.internal`). Use that hostname for `--cluster create` and for `cluster-announce-ip`.

### 4.3 Code change — use the cluster client

```python
# single-node (current)
from redis import Redis
r = Redis.from_url(settings.redis_url)

# cluster
from redis.cluster import RedisCluster
r = RedisCluster.from_url("rediss://default:<p>@<host>:6379/0")
```

Async equivalent: `redis.asyncio.cluster.RedisCluster`.

### 4.4 Pub/Sub caveat (important)

- Redis **< 7**: pub/sub messages are **not** forwarded across shards. A publisher on shard A won't reach a subscriber on shard B.
- Redis **7+**: enables **cluster-wide pub/sub** (`cluster-bus` broadcasts). Your `bin.state.changed` / search events are pub/sub, so if you cluster, require Redis 7+ and test cross-shard delivery, or route pub/sub through a dedicated non-clustered Redis.

---

## 5. Railway-specific notes

- **Private networking:** use `redis.railway.internal` / `<service>.railway.internal` between services; use the public URL only for external access.
- **Ephemeral disk:** self-hosted Redis in Railway loses data on redeploy unless you attach a **Volume** and point `dir`/`appendonly` at it (`/data`).
- **Persistence:** for managed Redis, enable AOF/RDB in the provider console if you need durability.
- **Healthcheck:** Railway uses `/health` for HTTP services; for Redis use a TCP port healthcheck or rely on the plugin's managed health.

---

## 6. Recommended final config (this project)

| Env var | Value |
|---|---|
| `REDIS_URL` | `rediss://default:<pwd>@<upstash-host>.upstash.io:6379/0` |
| `REDIS_WAREHOUSE_URL` | `rediss://default:<pwd>@<upstash-host>.upstash.io:6379/1` |

That is the current, production-ready setup. Migrate to §4 only when you hit a single-node limit.

## How Railway bills Redis

There's **no fixed per-database fee** — Redis is deployed as a regular service (the standard `redis` Docker image) and billed by metered usage:

| Resource | Rate |
|---|---|
| RAM | $10 / GB / month |
| CPU | $20 / vCPU / month |
| Volume (optional persistence) | $0.15 / GB / month |
| Network egress | $0.05 / GB (negligible for internal pub/sub) |

## How the $5 Hobby plan works

- You **always pay $5/month** (subscription), which includes **$5 of usage credit**.
- If your total usage stays ≤ $5, your bill is just $5.
- If total usage exceeds $5, you pay only the **difference** on top.

So Redis doesn't add a fixed cost — it just adds to your metered usage.

## Realistic cost for WMS bin capacity

Bin capacity pub/sub + a small cache is very light. A minimal Redis is plenty:

| Redis size | RAM cost | CPU cost | Est. total/month |
|---|---|---|---|
| 256 MB + 0.1 vCPU | $2.50 | $2.00 | **~$4.50** |
| 256 MB + 0.25 vCPU | $2.50 | $5.00 | ~$7.50 |
| 512 MB + 0.5 vCPU | $5.00 | $10.00 | ~$15.00 |

**Bottom line:** a small Redis will add roughly **$2.50–$5/month** in usage. Since your existing services (Postgres + `core-service` + gateway) already consume part of the $5 credit, adding a 256 MB Redis will most likely push you a **few dollars over $5**, depending on your current usage.

## Two things worth noting

1. **WMS bin capacity doesn't actually require Redis.** Looking at bin_capacity_service.py, it computes occupancy directly from PostgreSQL (`compute_bin_occupancy`). Redis would only be an optional caching layer for the capacity tree, or for the 3D warehouse real-time pub/sub already described in the guide (`REDIS_WAREHOUSE_URL`).

2. **Persistence is extra.** The Railway Redis template is unmanaged and loses data on redeploy unless you attach a Volume ($0.15/GB/month).

If you want, I can check your current Railway usage to tell you exactly how much headroom you have left in the $5 credit before adding Redis.
