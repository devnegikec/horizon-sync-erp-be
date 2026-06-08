# AI Integration — Phase 1 Knowledge Transfer Document

**Date:** 2026-06-01
**Scope:** Scaffold `ai-service`, implement machine-to-machine auth, typed core-service client, MCP Server V1, and Docker Compose wiring.
**Services touched:** `identity-service`, `core-service`, `ai-service`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Step 1 — Scaffold ai-service](#2-step-1--scaffold-ai-service)
3. [Step 2 — Machine-to-Machine JWT](#3-step-2--machine-to-machine-jwt)
4. [Step 3 — Typed core-service HTTP Client](#4-step-3--typed-core-service-http-client)
5. [Step 4 — MCP Server V1](#5-step-4--mcp-server-v1)
6. [Step 5 — Docker Compose + Test](#6-step-5--docker-compose--test)
7. [Files Summary](#7-files-summary)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Docker Compose Network                           │
│                                                                              │
│   ┌──────────────┐         client_credentials         ┌──────────────────┐  │
│   │  ai-service  │ ──────────────────────────────────> │ identity-service │  │
│   │   :8003      │  client_id=ai-service             │   :8000          │  │
│   │              │  client_secret=xxx                │                  │  │
│   │              │ <──────────────────────────────── │                  │  │
│   │              │         access_token (JWT)          │                  │  │
│   └──────┬───────┘                                     └──────────────────┘  │
│          │                                                                    │
│          │  Bearer <service_jwt>                                                │
│          │  GET /api/v1/stock-levels                                          │
│          └──────────────────────────────────────────> ┌──────────────────┐  │
│                                                         │   core-service   │  │
│                                                         │   :8001          │  │
│                                                         │                  │  │
│                                                         │ get_current_user │  │
│                                                         │ detects type=    │  │
│                                                         │ "service" → skips│  │
│                                                         │ /me HTTP call    │  │
│                                                         └──────────────────┘  │
│                                                                              │
│   External AI Assistant                                                      │
│         │                                                                    │
│         │  SSE / JSON-RPC     ┌──────────────┐                               │
│         └───────────────────> │  ai-service  │                               │
│              tools/call         │  MCP Server  │                               │
│              tools/list         │              │                               │
│                                 └──────────────┘                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key concepts:**
- **Service Token:** A JWT with `type: "service"` issued by `identity-service` to machine clients. It embeds `permissions` directly in the payload so `core-service` doesn't need to call `identity-service /me`.
- **MCP (Model Context Protocol):** Anthropic's JSON-RPC standard that lets AI assistants discover and invoke external tools. Our server exposes 6 read-only WMS tools.
- **Typed HTTP Client:** Instead of raw `requests.get()` scattered everywhere, `ai-service` has a single `CoreServiceClient` that knows all endpoint paths, handles auth headers, and returns structured data.

---

## 2. Step 1 — Scaffold ai-service

### Why
We need a dedicated microservice for all AI-related functionality (MCP, RAG, LLM orchestration, ingestion). Keeping it separate from `core-service` ensures:
- AI logic can be scaled independently
- Core WMS performance is never affected by LLM latency
- Clean separation of concerns

### Directory structure created
```
ai-service/
├── Dockerfile
├── requirements.txt
├── scripts/
│   ├── __init__.py
│   └── mcp_stdio.py          # stdio transport entrypoint (Step 4)
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app with lifespan + CORS
│   ├── config.py             # Pydantic BaseSettings
│   ├── api/
│   │   ├── __init__.py
│   │   └── mcp.py            # SSE endpoint (Step 4)
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── core_service.py   # Typed client (Step 3)
│   │   └── identity_service.py # M2M token client (Step 3)
│   └── services/
│       ├── __init__.py
│       └── mcp_server.py     # MCP tool handlers (Step 4)
```

### Key files

**`ai-service/app/main.py`** — FastAPI entrypoint with MCP router and health check.

**`ai-service/app/config.py`** — Pydantic `BaseSettings` loading env vars for core-service URL, identity-service URL, LLM config, and MCP server name.

**`ai-service/Dockerfile`** — Multi-stage build mirroring `core-service` pattern. Exposes port `8003`, health check on `/health`.

**`ai-service/requirements.txt`** — Includes `fastapi`, `pydantic`, `httpx`, `mcp`, `pgvector`, `scikit-learn`, `unstructured`, `python-dotenv`, `pytest`, `debugpy`.

---

## 3. Step 2 — Machine-to-Machine JWT (Client-Credentials)

### Why
When `ai-service` calls `core-service`, there is **no human** typing a password. Services must trust each other using a shared secret. This is the OAuth2 **client-credentials grant**.

### Flow
1. `ai-service` sends `client_id=ai-service` + `client_secret=xxx` to `identity-service`
2. `identity-service` verifies the secret against a bcrypt hash in `service_credentials` table
3. If valid, returns a JWT with `type: "service"` and `permissions` embedded in payload
4. `ai-service` sends this JWT to `core-service` in `Authorization: Bearer <token>` header
5. `core-service` sees `type: "service"`, skips the HTTP call to `identity-service /me`, reads permissions straight from JWT

### 3.1 identity-service — New model + migration

**`identity-service/app/models/service_credential.py`**
- New SQLAlchemy model: `ServiceCredential`
- Fields: `id`, `client_id` (unique), `client_secret_hash` (bcrypt), `service_name`, `permissions` (JSON list), `scopes`, `is_active`, `created_at`, `updated_at`, `last_used_at`

**`identity-service/alembic/versions/013_add_service_credentials.py`**
- Alembic migration creating `service_credentials` table with indexes on `client_id` and `(is_active, client_id)`.

**`identity-service/app/models/__init__.py`**
- Registered `ServiceCredential` in the models package.

### 3.2 identity-service — Security utils + endpoint

**`identity-service/app/core/security.py`** — Added:
- `create_service_token(data, expires_delta)`: Creates JWT with `type: "service"`, `sub: "service:client_id"`, `permissions`, `scopes`, `exp`, `iat`.
- `verify_client_secret(plain, hashed)`: bcrypt comparison for client secrets.

**`identity-service/app/config.py`** — Added:
- `service_token_expire_minutes: int = 60`

**`identity-service/app/schemas/auth.py`** — Added:
- `ClientCredentialsRequest`: Pydantic schema with `grant_type`, `client_id`, `client_secret`
- `ServiceTokenResponse`: Pydantic schema with `access_token`, `token_type`, `expires_in`

**`identity-service/app/api/v1/endpoints/auth.py`** — Added:
- `POST /auth/token` endpoint implementing client-credentials flow.
- Validates `grant_type == "client_credentials"`.
- Queries `ServiceCredential` by `client_id` where `is_active=True`.
- Verifies secret with `verify_client_secret()`.
- Updates `last_used_at`, generates token via `create_service_token()`, returns `ServiceTokenResponse`.

### 3.3 core-service — Recognize service tokens

**`core-service/app/dependencies.py`** — Updated `get_current_user`:
- After decoding JWT, checks `payload.get("type")`.
- If `type == "service"`: validates `sub` starts with `"service:"`, extracts `client_id`, reads `permissions` directly from payload.
- Returns `CurrentUser` with synthetic UUID, `user_type="service"`, and embedded permissions.
- **Skips the HTTP call to `identity-service /me`** — this is the performance optimization.
- If `type != "access"`: rejects with 401.

### 3.4 Seed script

**`identity-service/scripts/seed_ai_service_credential.py`**
- One-shot script to create the `ai-service` credential.
- Generates a random `client_secret` with `secrets.token_urlsafe(32)`.
- Stores bcrypt hash via `hash_password()`.
- Assigns permissions: `stock.read`, `asn_order.read`, `warehouse.read`, `user.read`, `put_away.read`.
- **Prints the raw secret ONCE** — must be saved in `.env` or secrets manager.

---

## 4. Step 3 — Typed core-service HTTP Client

### Why
Instead of raw `requests.get()` scattered in 6 places, we have one client that knows all paths, handles auth, and returns structured data.

### Architecture
```
ai-service
  ├── IdentityServiceClient  → POST /auth/token  → gets JWT
  │                              (identity-service)
  │
  └── CoreServiceClient  ──────► GET /api/v1/stock-levels
       │                         (core-service)
       │
       └── _get_auth_headers()
            └── calls identity_client.get_service_token()
```

### Key files

**`ai-service/app/clients/identity_service.py`**
- `IdentityServiceClient` class with `get_service_token()` method.
- Posts to `IDENTITY_SERVICE_URL/api/v1/identity/auth/token` with `client_id` + `client_secret`.
- Returns `access_token` string.
- Singleton: `identity_client = IdentityServiceClient()`

**`ai-service/app/clients/core_service.py`**
- `CoreServiceClient` class with:
  - `_get_auth_headers()`: fetches service token from `identity_client`, returns `{"Authorization": "Bearer <token>"}`
  - `_get(path, params)`: internal GET helper with auth + `raise_for_status()` + JSON parsing
- Six public methods mapping to core-service endpoints:
  - `get_stock(warehouse_id, item_id, bin_id)` → `GET /api/v1/stock-levels`
  - `get_asn_orders(warehouse_id, status, limit)` → `GET /api/v1/asn-orders`
  - `get_asn_order(asn_order_id)` → `GET /api/v1/asn-orders/{id}`
  - `get_users(warehouse_id, role)` → `GET /api/v1/warehouse-users`
  - `get_locations(warehouse_id, type_)` → `GET /api/v1/warehouse-locations`
  - `get_put_away(put_away_list_id)` → `GET /api/v1/put-away/{id}`
- Singleton: `core_client = CoreServiceClient()`

**`ai-service/app/config.py`** — Added:
- `SERVICE_CLIENT_ID: str = "ai-service"`
- `SERVICE_CLIENT_SECRET: str = ""`

---

## 5. Step 4 — MCP Server V1 (Read-Only Tools + SSE)

### Why MCP?
MCP lets AI assistants **discover** our API without being hard-coded. Claude asks our MCP server "What tools do you have?" then "Call `wms.stock.get` with warehouse_id=X". Our handler fetches data and returns structured JSON.

### Architecture
```
Claude Desktop / Cloud AI
        │
        │  1. initialize
        │  2. tools/list
        │  3. tools/call {name: "wms.stock.get", arguments: {...}}
        ▼
┌─────────────────────────────────────┐
│  ai-service :8003                 │
│  ┌─────────────────────────────┐  │
│  │  GET /mcp/sse               │  │
│  │  POST /mcp/messages/       │  │
│  │       ↓                     │  │
│  │  mcp.server.Server          │  │
│  │       ↓                     │  │
│  │  @mcp_server.tool(...)      │  │
│  │       ↓                     │  │
│  │  core_client.get_stock()    │  │
│  │       ↓                     │  │
│  │  core-service :8001         │  │
│  └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### MCP Host, Client, and Server — How they map to our codebase

This section documents the conceptual roles in the MCP ecosystem and where each role lives (inside or outside our repository).

**MCP Host** — *External to our code (not in repo)*
The Host is the application where the AI model runs. Examples: Claude Desktop, Cursor IDE, VS Code Copilot, or any custom agent. It initiates the connection to our ai-service. The React "AI Hub" UI (`apps/inventory/.../AiFeaturesHub.tsx`) is **not** the MCP Host — it is a human-facing dashboard that talks to ai-service over direct REST. The MCP Host is a separate external application that connects to ai-service over SSE.

**MCP Client** — *External library inside the Host (not in repo)*
The Client is the library embedded inside the Host that opens and maintains a 1:1 connection to our server. For Claude Desktop, that's Anthropic's `mcp` TypeScript client library. It handles:
1. Opening `GET http://ai-service:8003/mcp/sse`
2. Receiving the session POST URL from the SSE stream
3. Sending JSON-RPC tool requests (`tools/list`, `tools/call`) to `POST /mcp/messages/`
4. Receiving streamed responses back over SSE

**MCP Server** — *Fully in our code (`ai-service/`)*

| Layer | File | Role |
|-------|------|------|
| **MCP Protocol Server** | `app/services/mcp_server.py` | The actual MCP `Server` instance from the Anthropic Python SDK. Maintains the catalog of 6 read-only WMS tools (`wms.stock.get`, `wms.asn.list`, etc.) and dispatches tool calls to `_dispatch_tool()`. |
| **HTTP Transport** | `app/api/mcp.py` | FastAPI bridge that exposes the MCP Server over HTTP. `GET /mcp/sse` opens the SSE connection; `POST /mcp/messages/` receives JSON-RPC messages. Wires ASGI request/response into `SseServerTransport`. |
| **Data Backend** | `app/clients/core_service.py` | Internal HTTP client (not an MCP entity). The MCP Server uses this to fetch warehouse data from `core-service`. Acts as the adapter between the MCP protocol and the actual WMS database. |

**Connection flow:**
```
Claude Desktop / Cloud AI  (Host — external)
        │
        │  MCP Client library inside Host
        │  1. GET /mcp/sse  → receives session URL
        │  2. POST /mcp/messages/  → JSON-RPC request
        ▼
ai-service :8003  (Server — our code)
        │
        ├── app/api/mcp.py  (SSE transport)
        │     ↓
        ├── app/services/mcp_server.py  (MCP SDK Server)
        │     list_tools() / call_tool()
        │     ↓
        ├── app/clients/core_service.py  (internal client)
        │     ↓
        └── core-service :8001  (PostgreSQL + WMS data)
```

**Key distinction:** The React "AI Hub" UI (`AsnIngestion`, `SopCopilot`, `DiscrepancyDetector`, `McpTools`) uses **direct HTTP REST** to ai-service. Only the `McpTools` component provides configuration info for connecting an external MCP Host — it displays the SSE URL and Claude Desktop JSON config for a human admin to copy-paste.

---

### Key files

**`ai-service/app/services/mcp_server.py`**
- Imports `mcp.server.Server` and `mcp.types` (wrapped in `try/except` for graceful degradation).
- Creates `mcp_server = Server(settings.MCP_SERVER_NAME)`.
- **Important:** MCP SDK 1.6.0 uses `@server.list_tools()` and `@server.call_tool()` decorators, **not** `@server.tool()`. The latter does not exist in this version.
- Six tool handlers registered via `list_tools()` and `call_tool()`:
  - `wms.stock.get` → `core_client.get_stock()`
  - `wms.asn.list` → `core_client.get_asn_orders()`
  - `wms.asn.get` → `core_client.get_asn_order()`
  - `wms.user.list` → `core_client.get_users()` (with client-side role filtering)
  - `wms.location.list` → `core_client.get_locations()`
  - `wms.putaway.get` → `core_client.get_put_away()`
- Each handler:
  1. Validates required arguments (e.g., `warehouse_id`)
  2. Calls the appropriate `core_client` method
  3. Returns `types.TextContent` with JSON-serialized result
  4. Catches `httpx.HTTPStatusError` and returns error JSON with status code + response text
  5. Catches generic `Exception` and returns error message

**`ai-service/app/api/mcp.py`**
- `GET /mcp/sse`: SSE entrypoint using `mcp.server.sse.SseServerTransport`.
- Bridges ASGI `scope/receive/send` to MCP transport via `connect_sse()`.
- Calls `mcp_server.run(read_stream, write_stream, initialization_options)`.
- `POST /mcp/messages/`: Receives JSON-RPC messages from MCP clients.
- Both endpoints return `503` if MCP SDK is not installed.

**`ai-service/scripts/mcp_stdio.py`**
- Entrypoint for **stdio transport** (Claude Desktop, Cursor).
- Usage: `python scripts/mcp_stdio.py`
- Uses `mcp.server.stdio.stdio_server()` context manager.
- Bridges stdin/stdout to MCP server.

### Two transport modes

| Mode | Use Case | How to run |
|------|----------|-----------|
| **SSE** | Cloud assistants, remote clients | `uvicorn app.main:app --port 8003` → `http://localhost:8003/mcp/sse` |
| **stdio** | Claude Desktop, Cursor, local dev | `python scripts/mcp_stdio.py` → assistant spawns it as subprocess |

---

## 6. Step 5 — Docker Compose + Test

### Why
All services must boot together on a shared Docker network. `ai-service` depends on `identity-service` (for tokens) and `core-service` (for data).

### Changes

**`docker-compose.yml`** — Added `ai-service` block:
- `build.context: ./ai-service`, `dockerfile: Dockerfile`
- `container_name: horizon_ai`
- Environment variables:
  - `DATABASE_URL: postgresql://...@postgres:5432/ai_db`
  - `CORE_SERVICE_URL: http://core-service:8001`
  - `IDENTITY_SERVICE_URL: http://identity-service:8000`
  - `SERVICE_CLIENT_ID`, `SERVICE_CLIENT_SECRET` (from `.env`)
  - LLM config: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, etc.
  - MCP config: `MCP_SERVER_NAME`, `MCP_SERVER_VERSION`
- Ports: `8003:8003` (app), `5681:5681` (debugpy)
- `depends_on`: `postgres` (healthy), `identity-service` (started), `core-service` (started)
- `volumes`: hot-reload for `app/` and `scripts/`
- `command`: waits 20s for upstream services, then starts with debugpy on port 5681
- Added `ai-service` to `api-gateway` `depends_on`

**`scripts/init_databases.sql`** — Added:
- `CREATE DATABASE ai_db;`
- `GRANT ALL PRIVILEGES ON DATABASE ai_db TO horizon_user;`
- `\c ai_db; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

---

## 7. Files Summary

### New files

| File | Purpose |
|------|---------|
| `ai-service/Dockerfile` | Multi-stage Python build for ai-service |
| `ai-service/requirements.txt` | Python dependencies |
| `ai-service/app/__init__.py` | Package marker |
| `ai-service/app/main.py` | FastAPI app entrypoint |
| `ai-service/app/config.py` | Pydantic settings |
| `ai-service/app/api/__init__.py` | Package marker |
| `ai-service/app/api/mcp.py` | SSE + messages endpoints |
| `ai-service/app/clients/__init__.py` | Package marker |
| `ai-service/app/clients/core_service.py` | Typed HTTP client for core-service |
| `ai-service/app/clients/identity_service.py` | M2M token client for identity-service |
| `ai-service/app/services/__init__.py` | Package marker |
| `ai-service/app/services/mcp_server.py` | MCP tool handlers |
| `ai-service/scripts/__init__.py` | Package marker |
| `ai-service/scripts/mcp_stdio.py` | stdio transport entrypoint |
| `identity-service/app/models/service_credential.py` | Service credential SQLAlchemy model |
| `identity-service/alembic/versions/013_add_service_credentials.py` | Migration for service_credentials table |
| `identity-service/scripts/seed_ai_service_credential.py` | One-shot credential seed script |

### Modified files

| File | Changes |
|------|---------|
| `identity-service/app/models/__init__.py` | Imported `ServiceCredential` |
| `identity-service/app/core/security.py` | Added `create_service_token()`, `verify_client_secret()` |
| `identity-service/app/config.py` | Added `service_token_expire_minutes: int = 60` |
| `identity-service/app/schemas/auth.py` | Added `ClientCredentialsRequest`, `ServiceTokenResponse` |
| `identity-service/app/api/v1/endpoints/auth.py` | Added `POST /auth/token` endpoint + imports |
| `core-service/app/dependencies.py` | `get_current_user` now handles `type: "service"` tokens |
| `ai-service/app/config.py` | Added `SERVICE_CLIENT_ID`, `SERVICE_CLIENT_SECRET` |
| `docker-compose.yml` | Added `ai-service` block, updated `api-gateway` depends_on |
| `scripts/init_databases.sql` | Added `ai_db` creation and privileges |

---

## Testing the Full Chain

```bash
# 1. Stop everything and rebuild
$ docker compose down -v
$ docker compose up --build -d

# 2. Seed the ai-service credential (inside identity container)
$ docker exec -it horizon_identity bash -c "python scripts/seed_ai_service_credential.py"
# → Save the printed client_secret

# 3. Set it in your .env or export
$ export SERVICE_CLIENT_SECRET="the-secret-from-step-2"

# 4. Restart ai-service to pick up the secret
$ docker compose restart ai-service

# 5. Test health
$ curl http://localhost:8003/health
# → {"status":"healthy","service":"ai-service"}

# 6. Test token flow manually
$ curl -X POST http://localhost:8000/api/v1/identity/auth/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type":"client_credentials","client_id":"ai-service","client_secret":"YOUR_SECRET"}'
# → {"access_token":"...","token_type":"bearer","expires_in":3600}

# 7. Test that core-service accepts the service token
$ curl http://localhost:8001/api/v1/stock-levels \
  -H "Authorization: Bearer <service_token>"

# 8. Test SSE (if MCP SDK installed)
$ curl -N http://localhost:8003/mcp/sse
```

---

*End of Phase 1 KT Document. Next phases (ASN Ingestion, SOP Copilot, Discrepancy Detector) are documented in `AI_INTEGRATION_TECHNICAL_DESIGN.md`.*
