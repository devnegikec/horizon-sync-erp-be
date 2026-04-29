# Ngrok Setup Guide — Expose Backend Services for Team

This guide walks you through installing ngrok on Ubuntu 22.04 and exposing all backend services through a **single ngrok tunnel** using an Nginx API Gateway.

## Architecture

```
Team's Browser (Frontend on localhost:3000)
        │
        ▼
  ngrok tunnel (1 free tunnel)
        │
        ▼
  Nginx API Gateway (:9000)
        │
        ├── /api/v1/identity/*  →  Identity Service (:8000)
        ├── /api/v1/search/*    →  Search Service (:8002)
        └── /api/v1/*           →  Core Service (:8001)  [catch-all]
```

**One ngrok tunnel on port 9000. The gateway routes by the existing API path prefixes — no URL changes needed. Your frontend hits the same paths it always did, just on a different host.**

---

## 1. Install ngrok

```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null

echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list

sudo apt update && sudo apt install ngrok
```

Verify:

```bash
ngrok version
```

---

## 2. Create ngrok Account & Add Auth Token

1. Sign up at [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
2. Copy your authtoken from [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

---

## 3. Start All Services (Including the Gateway)

The API Gateway is already added to `docker-compose.yml`. Just run:

```bash
docker compose up -d --build
```

Verify the gateway is working:

```bash
# Gateway health check
curl http://localhost:9000/health

# Identity login endpoint through gateway
curl -X POST http://localhost:9000/api/v1/identity/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Test@123"}'

# Core service through gateway
curl http://localhost:9000/api/v1/items \
  -H "Authorization: Bearer YOUR_TOKEN"

# Swagger docs
curl http://localhost:9000/identity/docs
curl http://localhost:9000/core/docs
curl http://localhost:9000/search/docs
```

---

## 4. Start ngrok (Single Tunnel)

```bash
ngrok http 9000
```

You'll see output like:

```
Forwarding  https://abcd-1234.ngrok-free.app -> http://localhost:9000
```

Copy that `https://....ngrok-free.app` URL — this is your **single public URL** for everything.

---

## 5. URL Mapping

With ngrok URL `https://abcd-1234.ngrok-free.app`:

| What                       | Public URL                                               |
| -------------------------- | -------------------------------------------------------- |
| Login                      | `https://abcd-1234.ngrok-free.app/api/v1/identity/login` |
| Identity API               | `https://abcd-1234.ngrok-free.app/api/v1/identity/...`   |
| Core API (items, invoices) | `https://abcd-1234.ngrok-free.app/api/v1/items`          |
| Search API                 | `https://abcd-1234.ngrok-free.app/api/v1/search/global`  |
| Identity Swagger           | `https://abcd-1234.ngrok-free.app/identity/docs`         |
| Core Swagger               | `https://abcd-1234.ngrok-free.app/core/docs`             |
| Search Swagger             | `https://abcd-1234.ngrok-free.app/search/docs`           |
| Gateway Health             | `https://abcd-1234.ngrok-free.app/health`                |

**The API paths are identical to what the frontend already uses — no path rewriting needed.**

### Examples

```bash
# Login
curl -X POST https://abcd-1234.ngrok-free.app/api/v1/identity/login \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{"email":"admin@example.com","password":"Test@123"}'

# List items (core service)
curl https://abcd-1234.ngrok-free.app/api/v1/items \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "ngrok-skip-browser-warning: true"

# Global search
curl -X POST https://abcd-1234.ngrok-free.app/api/v1/search/global \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{"query":"widget"}'
```

---

## 6. What Your Team Needs to Do

Each team member only needs to change **one env variable** — the API base URL:

```env
# .env.local on team member's machine
# Both identity and core use the same base URL now
REACT_APP_API_URL=https://abcd-1234.ngrok-free.app
```

> No need for separate identity/core URLs. The gateway routes by path automatically.

### Add ngrok Header (Important!)

Free-plan ngrok shows a browser warning page that breaks API calls. Add this header globally:

```typescript
import axios from "axios";

axios.defaults.headers.common["ngrok-skip-browser-warning"] = "true";
```

Then start the frontend normally:

```bash
npm run dev
```

---

## 7. Monitor Traffic

ngrok provides a local inspector at:

```
http://127.0.0.1:4040
```

Shows all requests, response codes, and timing — great for debugging.

---

## 8. Run ngrok in Background (Optional)

```bash
# Option 1: nohup
nohup ngrok http 9000 > /dev/null 2>&1 &

# Option 2: screen
screen -S ngrok
ngrok http 9000
# Ctrl+A then D to detach
# screen -r ngrok to reattach
```

---

## 9. Stop Everything

```bash
# Stop ngrok
pkill ngrok

# Stop all services including gateway
docker compose down
```

---

## How the Routing Works

The gateway inspects the URL path and routes to the correct backend:

| URL path starts with         | Goes to          | Why                                       |
| ---------------------------- | ---------------- | ----------------------------------------- |
| `/api/v1/identity/`          | Identity (:8000) | Auth, users, roles, permissions           |
| `/api/v1/search/`            | Search (:8002)   | Global search, entity search              |
| `/api/v1/` (everything else) | Core (:8001)     | Items, invoices, warehouses, orders, etc. |

The paths are passed through **unchanged** — the backend receives the exact same URL it would if called directly.

---

## File Structure

```
nginx-gateway/
├── Dockerfile        # Alpine nginx image with custom config
└── nginx.conf        # Routes by /api/v1/ path prefix
```

---

## Quick Reference

| Command                        | What it does                 |
| ------------------------------ | ---------------------------- |
| `docker compose up -d --build` | Start all services + gateway |
| `ngrok http 9000`              | Expose gateway via ngrok     |
| `curl localhost:9000/health`   | Check gateway is running     |
| `http://127.0.0.1:4040`        | ngrok traffic inspector      |
| `pkill ngrok`                  | Stop ngrok                   |
| `docker compose down`          | Stop all services            |

---

## Troubleshooting

| Problem                            | Solution                                                                                |
| ---------------------------------- | --------------------------------------------------------------------------------------- |
| `502 Bad Gateway`                  | Backend service isn't ready. Check `docker compose logs identity-service`               |
| CORS errors in browser             | Gateway handles CORS — rebuild with `docker compose build api-gateway`                  |
| Frontend gets HTML instead of JSON | Add `ngrok-skip-browser-warning` header (see Section 6)                                 |
| ngrok URL changed after restart    | Free plan generates random URLs. Share the new one with team                            |
| Gateway not starting               | Run `docker compose build api-gateway` then `docker compose up -d`                      |
| Can't reach `localhost:9000`       | Check `docker compose ps` — gateway should show port 9000                               |
| Swagger docs show version error    | Rebuild gateway: `docker compose build api-gateway && docker compose up -d api-gateway` |
