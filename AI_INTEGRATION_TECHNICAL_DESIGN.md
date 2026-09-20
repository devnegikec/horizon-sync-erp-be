# AI / LLM / RAG / MCP Integration — Technical Design Document

> **Status:** Technical design — ready for implementation scoping  
> **Scope:** Four production-viable AI features integrated into the existing WMS microservices architecture  
> **Architecture:** `identity-service` + `core-service` + new `ai-service` (proposed)

---

## Overview

This document defines the technical architecture, data flows, API contracts, model choices, and phased implementation plan for four AI-powered features that plug into the existing Horizon Sync ERP WMS. The goal is to learn AI/LLM engineering on a live project while solving real warehouse-management problems.

**The four features**
1. **MCP Server for WMS** — Exposes warehouse data and operations via the Model Context Protocol so external AI assistants (Claude, Cursor, etc.) can query stock, ASN status, and user permissions safely.
2. **ASN Ingestion Agent** — Parses unstructured ASN documents (PDF, email, EDI, images) and converts them into structured `AsnOrder` drafts using an LLM with structured output.
3. **Warehouse SOP Copilot** — A RAG-powered chat assistant grounded in warehouse SOPs, pick/put-away rules, and location hierarchies that answers operator questions and suggests next-best actions.
4. **Discrepancy Detector** — Anomaly detection on receiving data (scan sessions vs. ASN, stock movements, cycle counts) using embeddings + lightweight classifier to flag SHORT / EXCESS / DAMAGE patterns before they become write-offs.

---

## 1. MCP Server for WMS

### 1.1 Problem & Value
External AI assistants cannot safely interact with the WMS because there is no standardized, permissioned protocol. Users paste screenshots or CSV exports into chat, which is slow and error-prone. An MCP server turns the WMS into a "tool" that Claude / Cursor / internal agents can call.

### 1.2 High-level Design

```
┌─────────────────┐     MCP (JSON-RPC)      ┌──────────────────┐
│  Claude Desktop │  <────────────────────>   │   ai-service     │
│  / Cursor / etc │   stdio or SSE transport  │  (MCP Server)    │
└─────────────────┘                         └────────┬─────────┘
                                                    │  HTTP / gRPC
                                                    ▼
                                           ┌──────────────────┐
                                           │  core-service    │
                                           │  identity-service│
                                           └──────────────────┘
```

### 1.3 Capabilities Exposed (Tools)

| Tool Name | Input | Output | RBAC Permission Required |
|-----------|-------|--------|--------------------------|
| `wms.stock.get` | `warehouse_id`, `item_id` (opt), `bin_id` (opt) | Current stock levels by bin | `stock.read` |
| `wms.asn.list` | `warehouse_id`, `status` (opt), `limit` | ASN orders with status + ETA | `asn_order.read` |
| `wms.asn.get` | `asn_order_id` | Full ASN with line items | `asn_order.read` |
| `wms.user.list` | `warehouse_id`, `role` (opt) | Users assigned to warehouse | `user.read` |
| `wms.location.list` | `warehouse_id`, `type` (opt) | Zones / aisles / bins | `warehouse.read` |
| `wms.putaway.get` | `put_away_list_id` | Put-away task with items & target bin | `put_away.read` |

> No write tools in V1 to minimize blast radius. Read-only audit trail.

### 1.4 Auth & Security
- MCP server runs as a standalone FastAPI service (`ai-service`) behind the gateway.
- Each MCP connection requires a **service-scoped JWT** issued by `identity-service`.
- Permission enforcement: reuse `has_permission` logic from `core-service/app/dependencies.py` via a shared Python package or HTTP call to identity-service.
- Rate-limit: 60 req/min per API key.

### 1.5 Transport Options
| Transport | Use Case | Config |
|-----------|----------|--------|
| **SSE** (Server-Sent Events) | Remote / cloud-hosted assistants | `ai-service` exposes `/mcp/sse`; assistant opens EventSource |
| **stdio** | Local desktop apps (Claude Desktop) | Wrapper script spawns `ai-service` CLI that speaks JSON-RPC over stdin/stdout |

### 1.6 Data Models
```python
class MCPRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    method: str          # tool name, e.g. "wms.stock.get"
    params: dict

class MCPResponse(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    result: Any | None
    error: dict | None
```

### 1.7 Implementation Tasks
- [ ] Scaffold `ai-service/` FastAPI app with `mcp` SDK (`pip install mcp>=1.0`).
- [ ] Define tool schema Pydantic models (input + output) for each tool.
- [ ] Implement `identity-service` endpoint to issue service-scoped JWTs for MCP clients.
- [ ] Wire `core-service` internal API (or reuse existing REST) to fetch data for each tool.
- [ ] Add SSE endpoint and stdio CLI entrypoint.
- [ ] Dockerize + add to `docker-compose.yml`.

---

## 2. ASN Ingestion Agent

### 2.1 Problem & Value
Suppliers send ASN data as PDFs, Excel files, emails, or photos of delivery notes. Operators manually retype this into the system. The agent reads the document, extracts structured fields, and creates a draft ASN for human confirmation.

### 2.2 High-level Design

```
┌──────────────┐   Upload   ┌──────────────┐   OCR / Parse   ┌──────────────┐
│   Frontend   │ ────────> │ ai-service   │ ──────────────> │  LLM Agent   │
│  (PDF/Img)   │           │  /ingest     │   (Unstructured│  (Structured  │
└──────────────┘           └──────────────┘    / Docling)    │   Output)    │
                                                             └──────┬───────┘
                                                                    │ JSON
                                                                    ▼
                                                             ┌──────────────┐
                                                             │ core-service │
                                                             │ POST /asn    │
                                                             │ (DRAFT)      │
                                                             └──────────────┘
```

### 2.3 Pipeline Stages

| Stage | Component | Technology | Notes |
|-------|-----------|------------|-------|
| **Ingest** | Upload endpoint | `ai-service` FastAPI, multipart upload | Store raw file in MinIO / S3 bucket `asn-ingestion-raw` |
| **Parse** | Document parser | `unstructured.io` or `docling` for PDF/Excel; `Pillow` for image pre-processing | Extract text + tables + bounding boxes |
| **Classify** | LLM document classifier | OpenAI GPT-4o / Claude 3.5 / Ollama | Single-token classification: `asn` \| `quotation` \| `pro_forma_invoice` \| `commercial_invoice` \| `packing_list` \| `unknown` |
| **Extract** | LLM structured extraction | OpenAI GPT-4o / Claude 3.5 Sonnet / local Llama 3.3 via Ollama | Use **response_format={"type": "json_schema"}** (OpenAI) or Anthropic tool-use |
| **Validate** | Business-rules layer | Pydantic validator in `ai-service` | Field completeness gate → PO lookup (must be open) → duplicate ASN check → supplier fuzzy match → SKU resolution |
| **Create** | Draft ASN creation | `core-service` API call | POST to existing `asn_orders.py` endpoint with `status=DRAFT`; set `created_by = "ai_agent"` |
| **Create (Manual)** | Direct ASN creation | `ai-service` FastAPI, JSON body | `POST /ai/asn/create` — skips parse/classify/extract; goes straight to validation |
| **Notify** | Human-in-the-loop | Reuse existing notification system | Notify warehouse supervisor that a new draft ASN awaits review |

### 2.4 Structured Output Schema (LLM Target)
```json
{
  "supplier_name": "string",
  "supplier_id": "uuid|null",
  "expected_delivery_date": "2026-06-10",
  "vehicle_number": "string|null",
  "driver_name": "string|null",
  "line_items": [
    {
      "sku": "string",
      "item_name": "string",
      "quantity": 100,
      "uom": "pieces",
      "batch_no": "string|null",
      "serial_nos": ["string"],
      "unit_cost": 0.00
    }
  ],
  "po_reference": "string|null",
  "confidence_score": 0.92,
  "low_confidence_fields": ["supplier_id", "batch_no"]
}
```

### 2.4.1 Direct Creation Schema (Manual Entry / API)
```json
{
  "supplier_name": "string",
  "supplier_id": "uuid|null",
  "expected_delivery_date": "2026-06-10",
  "warehouse_id": "uuid",
  "po_reference": "string|null",
  "vehicle_number": "string|null",
  "driver_name": "string|null",
  "line_items": [
    {
      "sku": "string",
      "item_name": "string",
      "quantity": 100,
      "uom": "pieces",
      "batch_no": "string|null",
      "serial_nos": ["string"],
      "unit_cost": 0.00
    }
  ],
  "organization_id": "uuid|null",
  "created_by_user_id": "uuid|null",
  "notes": "string|null"
```

### 2.5 Confidence & Human-in-the-Loop
- **Confidence score** per field and per document.
- **Auto-create threshold**: `>= 0.90` and all SKUs resolved and open PO matched and not a duplicate → auto-draft.
- **Manual review threshold**: `< 0.90` or unknown SKU or PO mismatch → create `IngestionJob` record; UI shows side-by-side (original doc vs. extracted JSON) for operator correction.
- **Rejection**: Document classified as non-ASN (quotation, invoice, etc.) → immediate rejection with reason logged.

### 2.6 Implementation Tasks
- [x] Add `IngestionJob` model to `ai-service` (raw_path, status, document_type, rejection_reason, extracted_json, confidence, reviewer_user_id).
- [x] Add `POST /ai/asn/ingest` endpoint (multipart, returns `job_id`).
- [x] Integrate `unstructured` or `docling` for parsing.
- [x] Build LLM document classifier (single-token: asn vs quotation vs pro_forma_invoice vs commercial_invoice).
- [x] Build LLM prompt template with few-shot examples of ASN PDF layouts.
- [x] Implement structured-output extraction with retry logic.
- [x] Add validation layer: field completeness gate, PO lookup + line-item cross-check, duplicate ASN detection, SKU resolver, supplier fuzzy matcher.
- [x] Add `POST /ai/asn/create` for manual entry, inter-warehouse transfers, and supplier API push.
- [x] Call `core-service` to create draft ASN with service-to-service auth.
- [ ] Add frontend screen: Ingestion Inbox (list jobs → review → confirm/reject).

---

## 3. Warehouse SOP Copilot

### 3.1 Problem & Value
New operators ask repetitive questions: "Where do I put pharma items?", "What do I do if scan shows SHORT?", "How do I handle a damaged pallet?". The copilot answers instantly using the actual SOP documents, location hierarchy, and current stock rules.

### 3.2 High-level Design (RAG)

```
┌──────────────┐      Question        ┌──────────────┐   Embedding   ┌──────────────┐
│   Frontend   │ ──────────────────>  │ ai-service   │ ───────────>  │  Vector DB   │
│  (Chat UI)   │                      │  /copilot    │   (query)     │  (pgvector / │
└──────────────┘                      └──────┬───────┘               │   Chroma)    │
                                             │                       └──────┬───────┘
                                             │ Retrieve top-k chunks <──────┘
                                             │
                                             │  ┌──────────────┐
                                             └──> │    LLM       │
                                                  │  (generate)  │
                                                  └──────┬───────┘
                                                         │ Answer + citations
                                                         ▼
                                                  ┌──────────────┐
                                                  │   Frontend   │
                                                  └──────────────┘
```

### 3.3 Knowledge Corpus (Documents to Embed)

| Source | Format | Location | Chunking Strategy |
|--------|--------|----------|-------------------|
| SOP PDFs / Word docs | Text + tables | `knowledge_base/sops/` | 512 tokens, overlap 64; preserve table rows |
| Put-away rules | JSON from DB | `core-service` API → export | One rule per chunk |
| Location hierarchy | DB rows | `WarehouseLocation` | Zone→Aisle→Bay→Bin as text description |
| Item master (restricted) | DB rows | `Item` | Item name + category + storage conditions |
| ASN / receiving playbooks | Markdown | `knowledge_base/playbooks/` | Per-scenario chunk |

### 3.4 Embedding & Retrieval
- **Embedding model**: `text-embedding-3-small` (OpenAI, cheap, 1536 dims) or `nomic-embed-text` via Ollama (local, 768 dims).
- **Vector store**: `pgvector` extension on existing Postgres (preferred — no new infra) OR Chroma embedded in `ai-service`.
- **Retrieval**: Hybrid search = vector similarity (top 5) + BM25 keyword re-ranking (top 3) via `rank_bm25` or Postgres full-text search.
- **Re-ranking**: Cross-encoder (`ms-marco-MiniLM-L-6-v2`) on the combined (query + chunk) list for precision.

### 3.5 Generation Prompt (System)
```
You are a Warehouse Operations Assistant. Answer the operator's question using ONLY the provided SOP context and warehouse data.
Rules:
1. Cite the source document name and section in [brackets].
2. If the answer requires a system action (e.g., create a put-away exception), output the action in a JSON block.
3. If the answer is not in the context, say "I don't have that information" — do not hallucinate.
4. Keep answers under 150 words unless a detailed procedure is requested.
```

### 3.6 Guardrails
- **RBAC filter**: Inject user's `warehouse_id` and `permissions` into retrieval so the copilot only sees locations / items / SOPs the user is allowed to access.
- **Audit**: Log every question + retrieved chunks + generated answer to an `ai_chat_log` table for compliance review.

### 3.7 Implementation Tasks
- [ ] Install `pgvector` on the existing Postgres DB (or run Chroma sidecar).
- [ ] Build ingestion pipeline: `ai-service` command that reads SOP files, calls embedding API, writes chunks + vectors.
- [ ] Implement `POST /ai/copilot/ask` endpoint with RAG retrieval + LLM generation.
- [ ] Add citation rendering in the response schema.
- [ ] Build a lightweight chat UI component (React) in the frontend or expose as a floating widget.
- [ ] Add `ai_chat_log` table for audit trail.

---

## 4. Discrepancy Detector

### 4.1 Problem & Value
Receiving discrepancies (SHORT, EXCESS, DAMAGED) are often noticed too late — after the supplier has left or the stock is already in the bin. The detector learns normal receiving patterns from historical scan sessions and flags anomalies in real time as the operator scans.

### 4.2 High-level Design

```
┌─────────────────┐   Scan event   ┌─────────────────┐   Feature vector   ┌─────────────────┐
│  ScanSession    │ ──────────────> │  ai-service     │ ─────────────────> │  Anomaly Model  │
│  (inbound)      │   (Kafka /     │  /detect        │   (embedding)      │  (Isolation     │
│                 │    HTTP push)   │                 │                    │   Forest / AE)  │
└─────────────────┘                 └─────────────────┘                    └─────────────────┘
                                                                                  │
                                                                                  ▼
                                                                           ┌─────────────────┐
                                                                           │  Alert / Flag   │
                                                                           │  (real-time)    │
                                                                           └─────────────────┘
```

### 4.3 Feature Engineering (per receiving event)

| Feature | Source | Embedding / Encoding |
|---------|--------|----------------------|
| `supplier_id` | `AsnOrder` → `supplier_id` | Categorical → entity embedding (learned) |
| `item_category` | `Item` → category | Categorical → one-hot or embedding |
| `expected_qty` | `AsnOrderItem.qty` | Numeric, normalized |
| `scanned_qty` | `ScanSessionItem.qty` | Numeric, normalized |
| `qty_ratio` | `scanned / expected` | Numeric |
| `time_of_day` | Scan timestamp | Cyclical encoding |
| `day_of_week` | Scan timestamp | Cyclical encoding |
| `vehicle_type` | `AsnOrder.vehicle_id` → type | Categorical |
| `dock_location` | `ScanSession.dock_location` | Text → embedding |
| `operator_tenure_days` | `User` created_at delta | Numeric |

### 4.4 Model Choice

| Approach | Tool | When to Use | Decision |
|----------|------|-------------|----------|
| **Isolation Forest** | `scikit-learn` | Tabular, interpretable, no GPU needed | **V1 choice** — fast, explainable |
| **Autoencoder** | PyTorch / TensorFlow | Complex non-linear patterns, large data | V2 if V1 precision is insufficient |
| **LLM classifier** | GPT-4o fine-tune | Rich text context (damage descriptions) | V2 for DAMAGE classification from text |

**V1 architecture**: Train an Isolation Forest on the feature vector. Flag score < -0.6 as anomalous. Retrain nightly via a cron job in `ai-service`.

### 4.5 Real-time Flow
1. Operator scans item → `inbound_service.py` records `ScanSessionItem`.
2. `inbound_service.py` emits event `ScanSessionItemCreated` to a lightweight queue (Redis pub/sub or in-process HTTP call to `ai-service`).
3. `ai-service` computes feature vector, runs Isolation Forest, returns `anomaly_score`.
4. If anomalous:
   - Return `{"alert": "Discrepancy risk detected", "suggested_action": "Recount or flag item"}` to the scanner frontend.
   - Create a `DiscrepancyAlert` record linked to the scan session.
   - Notify supervisor via existing notification pipeline.

### 4.6 Feedback Loop
- Operator can mark alert as **True Positive** (actual discrepancy) or **False Positive** (normal).
- Feedback writes to `discrepancy_feedback` table.
- Weekly retraining script retrains Isolation Forest on latest 90 days of data + feedback labels.

### 4.7 Implementation Tasks
- [ ] Add `DiscrepancyAlert` and `DiscrepancyFeedback` models to `ai-service`.
- [ ] Add feature engineering module in `ai-service` (fetch data from `core-service` via internal API).
- [ ] Implement Isolation Forest training pipeline with `scikit-learn`.
- [ ] Add `POST /ai/detect/discrepancy` endpoint (feature vector in → score out).
- [ ] Wire event from `core-service` `inbound_service.py` to `ai-service` (HTTP call or Redis).
- [ ] Add frontend toast / scanner UI alert when discrepancy risk is detected.
- [ ] Add feedback buttons (TP / FP) on alert cards.
- [ ] Schedule nightly/weekly retraining cron inside `ai-service`.

---

## Shared Architecture: `ai-service`

### Service Layout
```
ai-service/
├── app/
│   ├── main.py              # FastAPI app, lifespan management
│   ├── config.py            # Env vars, model API keys, vector DB URL
│   ├── dependencies.py      # Service-to-service auth, rate limits
│   ├── models/
│   │   ├── ingestion_job.py
│   │   ├── chat_log.py
│   │   ├── discrepancy_alert.py
│   │   └── vector_chunk.py
│   ├── api/
│   │   ├── mcp.py           # MCP SSE + stdio endpoints
│   │   ├── ingest.py        # ASN ingestion upload + manual create + status + review
│   │   ├── copilot.py       # RAG chat endpoint
│   │   └── detect.py        # Discrepancy detection endpoint
│   ├── services/
│   │   ├── mcp_server.py    # Tool registration + JSON-RPC handler
│   │   ├── doc_parser.py    # Unstructured / Docling wrapper
│   │   ├── extractor.py     # LLM document classifier + structured extraction
│   │   ├── ingestion_validator.py # PO match, duplicate check, supplier/SKU validation
│   │   ├── rag_engine.py    # Retrieval + generation orchestrator
│   │   └── anomaly_engine.py# Feature engineering + Isolation Forest
│   └── clients/
│       └── core_service.py  # Typed HTTP client for core-service APIs
├── knowledge_base/
│   └── sops/                # Markdown / PDF SOPs
├── scripts/
│   ├── embed_sops.py        # One-shot knowledge ingestion
│   └── train_discrepancy.py # Nightly retraining
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

### Infrastructure

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **LLM API** | OpenAI GPT-4o / Claude 3.5 Sonnet (cloud) OR Ollama + Llama 3.3 (local) | Cloud for quality; local for cost / air-gap |
| **Embeddings** | `text-embedding-3-small` (cloud) or `nomic-embed-text` (local) | Cheap, fast, good enough |
| **Vector DB** | `pgvector` on existing Postgres | Zero new infrastructure |
| **Queue** | Redis (already in `docker-compose.yml`) or in-process HTTP | Lightweight, no Kafka needed |
| **File Store** | MinIO or S3-compatible bucket | Raw ingestion files |
| **Observability** | Prometheus metrics + structured logging | Reuse existing stack |

### Service-to-Service Auth
- `ai-service` obtains a **machine-to-machine JWT** from `identity-service` using client-credentials flow (new grant type).
- JWT includes `service:ai-service` scope and limited permissions (`asn_order.create`, `stock.read`, etc.).
- `core-service` validates the JWT via existing `dependencies.py` logic.

---

## Phased Implementation Plan

### Phase 1 — Foundation (Week 1–2)
- [ ] Scaffold `ai-service` FastAPI project, Dockerfile, `docker-compose` entry.
- [ ] Add machine-to-machine JWT grant to `identity-service`.
- [ ] Build typed `core-service` HTTP client in `ai-service`.
- [ ] Implement **MCP Server V1** (read-only tools + SSE endpoint).
- [ ] Seed initial knowledge base with 3 SOP markdown files.

### Phase 2 — Ingestion (Week 3–4)
- [ ] Build `POST /ai/asn/ingest` pipeline (upload → parse → extract → validate).
- [ ] Integrate LLM structured output with retry logic.
- [ ] Add ingestion inbox UI in frontend (review/correct/confirm).
- [ ] Wire human-in-the-loop notification on low-confidence drafts.

### Phase 3 — Copilot (Week 5–6)
- [x] Install `pgvector`, create `vector_chunks` table.
- [x] Build SOP embedding pipeline (`scripts/embed_sops.py`).
- [x] Implement hybrid retrieval (vector + BM25) + re-ranking.
- [x] Add `POST /ai/copilot/ask` with guardrails + citations.
- [ ] Build chat UI widget in frontend.

### Phase 4 — Detection (Week 7–8)
- [x] Build feature engineering module for receiving events.
- [x] Implement Isolation Forest training + inference.
- [ ] Wire real-time scan event from `core-service` to `ai-service`.
- [ ] Add discrepancy alert UI + supervisor notification.
- [x] Implement feedback loop and scheduled retraining.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-01 | Four AI features selected | MCP (protocol exposure), Ingestion (structured extraction), Copilot (RAG), Detection (anomaly). Cover all four learning vectors: MCP, LLM, RAG, ML. |
| 2026-06-01 | Dedicated `ai-service` | Keeps AI dependencies (torch, transformers, unstructured) isolated from core/identity; allows independent scaling. |
| 2026-06-01 | `pgvector` over Chroma/Pinecone | Existing Postgres infrastructure; no new infra cost. |
| 2026-06-01 | Isolation Forest V1 for anomaly | Interpretable, fast, scikit-learn only; avoids GPU complexity. |
| 2026-06-01 | Read-only MCP V1 | Minimizes security risk while proving protocol value. Write tools in V2. |
| 2026-06-02 | Document classifier before ASN extraction | Prevents ingestion of quotations, pro-forma invoices, and cancelled orders. Single-token LLM call is cheap and fast. |
| 2026-06-02 | PO matching + duplicate ASN gate | An ASN without an open Purchase Order is not valid. Cross-checks line-item quantities within 10% tolerance. |
| 2026-06-02 | `POST /ai/asn/create` for manual entry | Warehouses need to create ASNs without supplier documents (operator entry, inter-DC transfers, customer returns). Same validation pipeline, skips parse/classify/extract. |

---

## Key File References

**New service (proposed):**
- `ai-service/app/main.py`, `ai-service/app/config.py`
- `ai-service/app/api/mcp.py`, `ingest.py`, `copilot.py`, `detect.py`
- `ai-service/app/services/mcp_server.py`, `extractor.py`, `ingestion_validator.py`, `rag_engine.py`, `anomaly_engine.py`
- `ai-service/app/clients/core_service.py`

**Existing services to touch:**
- `core-service/app/api/v1/endpoints/inbound.py` — emit scan event to `ai-service`
- `core-service/app/services/inbound_service.py` — hook for discrepancy alert
- `identity-service/app/models/token.py` — add machine-to-machine token type
- `identity-service/app/api/v1/endpoints/auth.py` — add client-credentials endpoint
- `docker-compose.yml` — add `ai-service`, `pgvector` enable, MinIO

---

*End of Technical Design Document. Awaiting approval to begin Phase 1 implementation.*
