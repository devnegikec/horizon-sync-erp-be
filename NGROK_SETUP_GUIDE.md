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
        ├── /identity/*  →  Identity Service (:8000)
        ├── /core/*      →  Core Service (:8001)
        └── /search/*    →  Search Service (:8002)
```

**One ngrok tunnel on port 9000 routes to all three services via URL path prefixes.**

---

## 1. Install ngrok

```bash
# Add ngrok GPG key and repo
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

# Identity Service through gateway
curl http://localhost:9000/identity/docs

# Core Service through gateway
curl http://localhost:9000/core/docs

# Search Service through gateway
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

| What             | Public URL                                             |
| ---------------- | ------------------------------------------------------ |
| Identity API     | `https://abcd-1234.ngrok-free.app/identity/api/v1/...` |
| Identity Swagger | `https://abcd-1234.ngrok-free.app/identity/docs`       |
| Core API         | `https://abcd-1234.ngrok-free.app/core/api/v1/...`     |
| Core Swagger     | `https://abcd-1234.ngrok-free.app/core/docs`           |
| Search API       | `https://abcd-1234.ngrok-free.app/search/api/v1/...`   |
| Search Swagger   | `https://abcd-1234.ngrok-free.app/search/docs`         |
| Gateway Health   | `https://abcd-1234.ngrok-free.app/health`              |

### Examples

```bash
# Login
curl -X POST https://abcd-1234.ngrok-free.app/identity/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Test@123"}'

# List items (with token)
curl https://abcd-1234.ngrok-free.app/core/api/v1/items \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 6. Update CORS Settings

Add the ngrok URL to `CORS_ORIGINS` in your `.env` file or directly in `docker-compose.yml`:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:4200,https://abcd-1234.ngrok-free.app
```

Then restart:

```bash
docker compose down && docker compose up -d
```

---

## 7. What Your Team Needs to Do

Each team member updates their frontend `.env.local`:

```env
# Point both services to the single ngrok gateway
REACT_APP_IDENTITY_API_URL=https://abcd-1234.ngrok-free.app/identity
REACT_APP_API_URL=https://abcd-1234.ngrok-free.app/core
```

> Adjust variable names to match your frontend config.

### Add ngrok Header (Important!)

Free-plan ngrok shows a browser warning page that breaks API calls. Add this header globally in the frontend HTTP client:

```typescript
// In your axios setup or API client
import axios from "axios";

axios.defaults.headers.common["ngrok-skip-browser-warning"] = "true";
```

Then start the frontend normally:

```bash
npm run dev
```

---

## 8. Monitor Traffic

ngrok provides a local inspector at:

```
http://127.0.0.1:4040
```

Shows all requests, response codes, and timing — great for debugging.

---

## 9. Run ngrok in Background (Optional)

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

## 10. Stop Everything

```bash
# Stop ngrok
pkill ngrok

# Stop all services including gateway
docker compose down
```

---

## File Structure

```
nginx-gateway/
├── Dockerfile        # Alpine nginx image with custom config
└── nginx.conf        # Routes /identity/, /core/, /search/ to services
```

The gateway service is defined in `docker-compose.yml` as `api-gateway` on port 9000.

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

| Problem                              | Solution                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| `502 Bad Gateway` on `/identity/...` | Identity service isn't ready yet. Check `docker compose logs identity-service` |
| `502 Bad Gateway` on `/core/...`     | Core service isn't ready yet. Check `docker compose logs core-service`         |
| CORS errors in browser               | Add ngrok URL to `CORS_ORIGINS` and restart Docker                             |
| Frontend gets HTML instead of JSON   | Add `ngrok-skip-browser-warning` header (see Section 7)                        |
| ngrok URL changed after restart      | Free plan generates random URLs each time. Share the new one with team         |
| Gateway not starting                 | Run `docker compose build api-gateway` then `docker compose up -d`             |
| Can't reach `localhost:9000`         | Check `docker compose ps` — gateway should show port 9000                      |
