# AI Integration — Phase 1 & Phase 2 Knowledge Transfer Document

> **Status:** Complete (Phase 1 MCP + Phase 2A Ingestion + Phase 2B Copilot + Phase 2C Detection)  
> **Scope:** All AI features implemented in `ai-service` with step-by-step code references  
> **Audience:** Engineering team onboarding, DevOps deployment, future maintainers

---

## Table of Contents

1. [Phase 1 — MCP Server (Foundation)](#phase-1)
2. [Phase 2A — ASN Ingestion Agent](#phase-2a)
3. [Phase 2B — SOP Copilot (RAG)](#phase-2b)
4. [Phase 2C — Discrepancy Detector](#phase-2c)
5. [Docker Build & Test Commands](#build-commands)
6. [Environment Variables Reference](#env-vars)
7. [API Endpoint Summary](#api-summary)

---

<a name="phase-1"></a>
## 1. Phase 1 — MCP Server (Foundation)

### 1.1 What is MCP?
MCP (Model Context Protocol) is Anthropic's open protocol for AI assistants to discover and invoke tools. It uses JSON-RPC over SSE (Server-Sent Events) or stdio.

### 1.2 Architecture
```
Claude Desktop / Cursor / Cloud AI
         |
    SSE or stdio
         |
    ai-service (MCP Server)
         |
    HTTP + JWT Bearer
         |
    core-service / identity-service
```

### 1.3 Files Created

#### `ai-service/app/services/mcp_server.py`
```python
from mcp.server import Server
import mcp.types as types

mcp_server = Server(settings.MCP_SERVER_NAME)

_TOOL_SCHEMAS = [
    types.Tool(name="wms.stock.get", description="...", inputSchema={...}),
    types.Tool(name="wms.asn.list", description="...", inputSchema={...}),
    # ... 6 tools total
]

@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return _TOOL_SCHEMAS

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return await _dispatch_tool(name, arguments)
```

**Key API pattern (mcp==1.6.0):**
- `@server.list_tools()` — discovery endpoint
- `@server.call_tool()` — invocation endpoint
- **NOT** `@server.tool()` — this decorator does not exist in 1.6.0

#### `ai-service/app/api/mcp.py`
```python
@router.get("/sse")
async def mcp_sse_endpoint(request: Request):
    async with mcp_transport.connect_sse(...) as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, init_options)
```

#### `ai-service/app/clients/core_service.py`
- Typed HTTP client for core-service
- Auto-fetches service JWT from identity-service via `identity_client.get_service_token()`
- Methods: `get_stock`, `get_asn_orders`, `get_asn_order`, `get_users`, `get_locations`, `get_put_away`

#### `ai-service/app/clients/identity_service.py`
- OAuth2 client-credentials flow: `POST /api/v1/identity/token`
- Caches token in memory, refreshes on 401

### 1.4 Machine-to-Machine Auth

#### identity-service changes:
- **Model:** `identity-service/app/models/service_credential.py` — bcrypt-hashed secrets
- **Migration:** `identity-service/alembic/versions/013_add_service_credentials.py`
- **Endpoint:** `identity-service/app/api/v1/endpoints/auth.py` — `POST /api/v1/identity/token` with `grant_type=client_credentials`
- **Seed script:** `identity-service/scripts/seed_ai_service_credential.py` — generates `client_secret` for ai-service

#### core-service changes:
- `core-service/app/dependencies.py` — `get_current_user` handles `type: "service"` tokens, skips `/me` call

### 1.5 Build & Seed
```bash
# 1. Ensure pgvector extension exists (already in init_databases.sql)
docker exec -it horizon_postgres psql -U horizon_user -d ai_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 2. Drop conflicting table if migration failed previously
docker exec -it horizon_postgres psql -U horizon_user -d identity_db -c "DROP TABLE IF EXISTS service_credentials CASCADE;"

# 3. Restart identity-service to run migration
docker compose restart identity-service

# 4. Seed the ai-service credential
docker exec -it horizon_identity bash -c "python scripts/seed_ai_service_credential.py"
# Save the printed client_secret into your .env as SERVICE_CLIENT_SECRET=...

# 5. Build ai-service
docker compose up --build -d ai-service

# 6. Test token endpoint
curl -X POST http://localhost:8000/api/v1/identity/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type":"client_credentials","client_id":"ai-service","client_secret":"YOUR_SECRET"}'
```

---

<a name="phase-2a"></a>
## 2. Phase 2A — ASN Ingestion Agent

### 2.1 Problem
Suppliers send ASN data as PDFs, Excel, emails, or photos. Operators manually retype into the system. The agent automates this.

### 2.2 Pipeline Flow
```
Two entry points:

A) Document Upload (supplier PDF / email / image)
Frontend Upload (or email/webhook)
      |
      v
POST /ai/asn/ingest  (multipart/form-data)
      |
      v
[IngestionJob]  status=PENDING  source_type=document_upload
      |
      v
BackgroundTask:
  1. Parse (DocumentParser)     -> raw_text
  1b. Classify (ASNExtractor.classify) -> asn | quotation | pro_forma_invoice | ...
       (if NOT asn -> REJECTED with reason)
  2. Extract (ASNExtractor)     -> structured JSON
  3. Validate (IngestionValidator) -> field completeness, PO match, supplier match, SKU resolution, duplicate check
  4. Create Draft (core_service.create_asn_draft) -> DRAFT_CREATED
      |
      v
Manual Review (if confidence < 0.90 or PO mismatch)
      |
      v
POST /ai/asn/ingest/{id}/review  (confirm | reject)

B) Manual Entry (warehouse operator / inter-warehouse transfer / supplier API)
Frontend Form  or  Supplier Webhook  or  Internal System
      |
      v
POST /ai/asn/create  (JSON body)
      |
      v
[IngestionJob]  status=VALIDATING  source_type=manual_entry|supplier_api|internal_transfer
      |
      v
BackgroundTask:
  (skip parse/classify/extract)
  3. Validate (IngestionValidator) -> PO match, supplier match, SKU resolution, duplicate check
  4. Create Draft (core_service.create_asn_draft) -> DRAFT_CREATED
      |
      v
Manual Review (if PO mismatch or duplicate)
      |
      v
POST /ai/asn/ingest/{id}/review  (confirm | reject)
```

### 2.3 Files Created

#### `ai-service/app/models/ingestion_job.py`
```python
class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    DRAFT_CREATED = "draft_created"
    MANUAL_REVIEW = "manual_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    FAILED = "failed"

class AsnSourceType(str, enum.Enum):
    DOCUMENT_UPLOAD = "document_upload"
    MANUAL_ENTRY = "manual_entry"
    SUPPLIER_API = "supplier_api"
    INTERNAL_TRANSFER = "internal_transfer"
    CUSTOMER_RETURN = "customer_return"

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    # Fields: id, original_filename, stored_path, file_type, status, raw_text,
    #         document_type (asn|quotation|pro_forma_invoice|...),
    #         rejection_reason, source_type, extracted_json, confidence_score,
    #         low_confidence_fields, validation_errors, draft_asn_order_id,
    #         reviewer_user_id, created_by_user_id, organization_id, warehouse_id,
    #         created_at, updated_at, completed_at
```

#### `ai-service/app/services/doc_parser.py`
```python
class DocumentParser:
    SUPPORTED_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "image/png": "png",
        "image/jpeg": "jpg",
        "text/plain": "txt",
        "message/rfc822": "email",
    }

    def parse(self, file_bytes: bytes, filename: str, content_type: str | None) -> str:
        # Uses unstructured-io when available
        # Falls back to openpyxl for Excel, pytesseract for images
```

**Key point:** `unstructured` is listed in `requirements.txt` but not all extras. For full PDF support you need `pip install unstructured[pdf]` which brings in `tesseract`, `poppler-utils`, etc. For now, the code has fallbacks.

#### `ai-service/app/services/extractor.py`
```python
class ASNExtractor:
    async def classify(self, raw_text: str) -> str:
        # Returns one of: asn, quotation, pro_forma_invoice,
        #                  commercial_invoice, packing_list, unknown
        # Uses a single-token LLM call (max_tokens=20, temperature=0.0)

    async def extract(self, raw_text: str) -> dict:
        # Calls OpenAI / Anthropic / Ollama with structured system prompt
        # Returns JSON matching ASN schema with confidence_score
```

**Classification prompt:** Runs first, before extraction. Quotation, pro-forma invoice, and commercial invoice documents are rejected at the pipeline level — no ASN extraction is attempted.

**Extraction prompt:** Enforces a strict JSON schema with fields: `supplier_name`, `supplier_id`, `expected_delivery_date`, `vehicle_number`, `driver_name`, `warehouse_id`, `line_items[]`, `po_reference`, `confidence_score`, `low_confidence_fields`.

#### `ai-service/app/services/ingestion_validator.py`
```python
class IngestionValidator:
    async def validate(self, extracted: dict, organization_id, warehouse_id) -> dict:
        # Returns:
        #   is_valid: bool
        #   auto_create: bool
        #   errors: [str]
        #   warnings: [str]
        #   matched_supplier_id: UUID | None
        #   matched_po_id: UUID | None
        #   is_duplicate: bool
        #   line_item_results: [{sku, matched_item_id, warnings}]
```

**Validation layers (run in order):**
1. **Field completeness gate** — checks `supplier_name`, `expected_delivery_date`, `line_items` exist
2. **PO matching** — looks up `po_reference` in core-service; rejects if PO not found, not open, or line-item qty mismatch (>10%)
3. **Duplicate ASN detection** — checks if `asn_order_number` already exists in core-service
4. **Supplier fuzzy match** — resolves `supplier_name` against core-service master data
5. **SKU resolution** — resolves each line-item SKU against item master

**Auto-create threshold:**
- `confidence_score >= 0.90`
- `is_duplicate == false`
- Zero validation errors
- Zero low-confidence fields
- Supplier resolved
- All SKUs resolved
- Open PO matched

#### `ai-service/app/api/ingest.py`
```python
@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest_asn_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    organization_id: str | None = Form(None),
    warehouse_id: str | None = Form(None),
    db: Session = Depends(get_db),
):
    # Document upload path. Returns job_id immediately.
    # BackgroundTasks.run(run_ingestion_pipeline) runs async

@router.post("/create", response_model=IngestResponse, status_code=202)
async def create_asn_directly(
    background_tasks: BackgroundTasks,
    request: CreateAsnRequest = Body(...),
    db: Session = Depends(get_db),
):
    # Manual entry path. Skips parse/classify/extract.
    # Goes straight to validation → draft creation.

@router.get("/ingest/{job_id}", response_model=JobStatusResponse)
async def get_ingestion_status(job_id: UUID, db: Session = Depends(get_db)):
    # Poll endpoint for status + source_type + extracted_json + validation_errors

@router.post("/ingest/{job_id}/review", response_model=JobStatusResponse)
async def review_ingestion_job(
    job_id: UUID,
    action: ReviewAction = Body(...),  # action: confirm | reject, corrected_json optional
    db: Session = Depends(get_db),
):
```

### 2.4 Core-Service Client Extensions

Added to `ai-service/app/clients/core_service.py`:
```python
async def search_suppliers(self, name, organization_id) -> list[dict]
async def search_items(self, sku, organization_id) -> list[dict]
async def create_asn_draft(self, payload: dict) -> dict
async def find_purchase_order(self, po_number, supplier_id, organization_id) -> dict | None
async def find_asn_by_number(self, asn_number, supplier_id, organization_id) -> dict | None
```

### 2.5 Database Setup
```bash
# ai-service needs its own DB tables
docker exec -it horizon_ai bash -c "python -c 'from app.database import Base, engine; Base.metadata.create_all(bind=engine)'"
```

Tables created automatically on startup via `_create_tables()` in `main.py` lifespan.

### 2.6 Usage

**A) Document upload (supplier PDF / Excel / image)**
```bash
curl -X POST http://localhost:8003/ai/asn/ingest \
  -F "file=@/path/to/asn.pdf" \
  -F "organization_id=uuid-here" \
  -F "warehouse_id=uuid-here"

# Response: {"job_id": "...", "status": "pending", "message": "..."}
```

**B) Manual entry (warehouse operator / inter-warehouse transfer)**
```bash
curl -X POST http://localhost:8003/ai/asn/create \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_name": "Acme Logistics",
    "supplier_id": "uuid-here",
    "expected_delivery_date": "2026-06-15",
    "warehouse_id": "uuid-here",
    "po_reference": "PO-2026-001",
    "line_items": [
      {"sku": "WIDGET-001", "item_name": "Blue Widget", "quantity": 100, "uom": "pieces"}
    ],
    "created_by_user_id": "uuid-of-operator",
    "organization_id": "uuid-here"
  }'

# Response: {"job_id": "...", "status": "validating", "message": "..."}
```

**Common: poll and review**
```bash
# Poll status (shows source_type, document_type, rejection_reason, extracted_json, validation_errors)
curl http://localhost:8003/ai/asn/ingest/{job_id}

# Review (confirm)
curl -X POST http://localhost:8003/ai/asn/ingest/{job_id}/review \
  -H "Content-Type: application/json" \
  -d '{"action":"confirm","review_notes":"Looks correct"}'

# Review (reject)
curl -X POST http://localhost:8003/ai/asn/ingest/{job_id}/review \
  -H "Content-Type: application/json" \
  -d '{"action":"reject","review_notes":"Wrong supplier"}'
```

---

<a name="phase-2b"></a>
## 3. Phase 2B — SOP Copilot (RAG)

### 3.1 What is RAG?
Retrieval-Augmented Generation: embed the user's question, search a vector database for relevant document chunks, feed those chunks as context to an LLM, and generate a grounded answer with citations.

### 3.2 Architecture
```
Operator Question
      |
      v
Embedding (text-embedding-3-small)
      |
      v
pgvector similarity search (top-k)
      |
      v
Build context window from chunks
      |
      v
LLM generates answer with [citations]
      |
      v
Log to chat_logs (audit)
```

### 3.3 Files Created

#### `scripts/init_databases.sql` — pgvector extension
```sql
-- Connect to ai_db
\c ai_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgvector for vector similarity search (SOP Copilot RAG)
CREATE EXTENSION IF NOT EXISTS "vector";
```

#### `ai-service/app/models/vector_chunk.py`
```python
class ChunkSource(str, enum.Enum):
    SOP = "sop"
    PLAYBOOK = "playbook"
    PUT_AWAY_RULE = "put_away_rule"
    LOCATION_HIERARCHY = "location_hierarchy"
    ITEM_MASTER = "item_master"

class VectorChunk(Base):
    __tablename__ = "vector_chunks"
    # id, source_type, source_id, source_title, section, chunk_index
    # content, content_hash
    # embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=False)
    # organization_id, warehouse_id (RBAC scope)
```

**Vector dimensions:** Configured via `EMBEDDING_DIMENSIONS` env var. Default: 1536 (OpenAI text-embedding-3-small). For Ollama nomic-embed-text: 768.

#### `ai-service/app/models/chat_log.py`
```python
class ChatLog(Base):
    __tablename__ = "chat_logs"
    # user_id, organization_id, warehouse_id, session_id
    # question, retrieved_chunks (JSONB), retrieval_time_ms
    # answer, model_used, generation_time_ms, citations (JSONB), blocked
```

#### `ai-service/app/services/embedding.py`
```python
class EmbeddingService:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        # OpenAI: batch up to 2048 per request, returns sorted by index
        # Ollama: one-by-one (Ollama embed API limitation)

    async def embed_single(self, text: str) -> list[float]:
```

#### `ai-service/app/services/rag_engine.py`
```python
class RAGEngine:
    async def ask(self, question: str, db, user_id, organization_id, warehouse_id, session_id) -> dict:
        # 1. Embed question
        # 2. Retrieve chunks via pgvector <=> operator (cosine distance)
        # 3. Filter by similarity threshold (default 0.75)
        # 4. Build context window
        # 5. Call LLM with _COPILOT_SYSTEM_PROMPT.format(context=context)
        # 6. Extract [bracket] citations
        # 7. Log to ChatLog
        # Returns: {answer, citations, retrieved_chunks, model_used}
```

**Retrieval SQL:**
```sql
SELECT id, source_type, source_title, section, content,
       embedding <=> :embedding AS distance
FROM vector_chunks
WHERE (organization_id = :org_id OR organization_id IS NULL)
  AND (warehouse_id = :wh_id OR warehouse_id IS NULL)
ORDER BY embedding <=> :embedding
LIMIT :limit
```

**Similarity conversion:** `cosine_similarity = 1 - distance`. Filter: `similarity >= threshold`.

#### `ai-service/app/api/copilot.py`
```python
@router.post("/ask", response_model=AskResponse)
async def copilot_ask(request: AskRequest = Body(...), db: Session = Depends(get_db)):
    # Enforces question min_length=3, max_length=2000

@router.get("/history", response_model=ChatHistoryResponse)
async def copilot_history(
    user_id: Optional[UUID] = Query(None),
    organization_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
```

#### `ai-service/scripts/embed_sops.py`
```bash
# Ingest a directory of markdown/PDF/text files
python scripts/embed_sops.py /app/knowledge_base/sops/ --source-type sop

# Or a single file
python scripts/embed_sops.py /app/knowledge_base/sops/receiving.md --source-type sop
```

**Chunking strategy:**
1. Parse file to raw text
2. If markdown headings exist (`## Section`), split by heading
3. Chunk each section by word count (default 512 words, overlap 64)
4. Deduplicate by SHA256 `content_hash`
5. Embed each chunk
6. Write to `vector_chunks` table

### 3.4 Configuration
```python
# ai-service/app/config.py
EMBEDDING_PROVIDER: str = "openai"        # openai | ollama
OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
EMBEDDING_DIMENSIONS: int = 1536          # text-embedding-3-small=1536, nomic=768

RAG_TOP_K: int = 5
RAG_SIMILARITY_THRESHOLD: float = 0.75
```

### 3.5 Usage
```bash
# Ingest knowledge base
docker exec -it horizon_ai bash -c \
  "python scripts/embed_sops.py /app/knowledge_base/sops/"

# Ask a question
curl -X POST http://localhost:8003/ai/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Where do I put pharma items that need cold storage?",
    "organization_id": "uuid-here",
    "warehouse_id": "uuid-here"
  }'

# View history
curl "http://localhost:8003/ai/copilot/history?limit=10"
```

---

<a name="phase-2c"></a>
## 4. Phase 2C — Discrepancy Detector

### 4.1 Problem
Receiving discrepancies (SHORT, EXCESS, DAMAGED) are often noticed too late. The detector learns normal receiving patterns and flags anomalies in real time.

### 4.2 Architecture
```
Scan Event (expected_qty, scanned_qty, supplier, dock, time, ...)
      |
      v
Feature Engineering (14 features)
      |
      v
Isolation Forest (scikit-learn)
      |
      v
Anomaly Score + Severity (low/medium/high/critical)
      |
      v
If anomalous: create DiscrepancyAlert
      |
      v
Operator feedback (TP/FP) -> weekly retraining
```

### 4.3 Files Created

#### `ai-service/app/models/discrepancy_alert.py`
```python
class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"

class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DiscrepancyAlert(Base):
    __tablename__ = "discrepancy_alerts"
    # scan_session_id, asn_order_id, anomaly_score, severity, alert_type
    # suggested_action, feature_vector (JSONB), status, acknowledged_by

class DiscrepancyFeedback(Base):
    __tablename__ = "discrepancy_feedback"
    # alert_id, is_true_positive, operator_notes, actual_discrepancy_type
```

#### `ai-service/app/services/anomaly_engine.py`

**Feature Engineering (14 features):**
| Feature | Type | Encoding |
|---------|------|----------|
| expected_qty | numeric | raw |
| scanned_qty | numeric | raw |
| qty_ratio | numeric | scanned / expected |
| hour_of_day_sin | cyclical | sin(2*pi*hour/24) |
| hour_of_day_cos | cyclical | cos(2*pi*hour/24) |
| day_of_week_sin | cyclical | sin(2*pi*dow/7) |
| day_of_week_cos | cyclical | cos(2*pi*dow/7) |
| item_category_encoded | categorical | hash % 100 / 100 |
| supplier_encoded | categorical | hash % 100 / 100 |
| dock_location_encoded | categorical | hash % 100 / 100 |
| operator_tenure_days | numeric | raw |
| vehicle_type_encoded | categorical | hash % 100 / 100 |
| asn_line_count | numeric | raw |
| avg_line_qty | numeric | raw |

**Isolation Forest config:**
```python
IsolationForest(
    n_estimators=100,
    contamination=0.05,    # expect 5% anomalies in data
    random_state=42,
    n_jobs=-1,
)
```

**Scoring:**
- `decision_function()` returns a score. Negative = more anomalous.
- Threshold: `score < -0.6` = anomaly
- Severity bands:
  - `-0.4` to `-0.6` → MEDIUM
  - `-0.6` to `-0.8` → HIGH
  - `< -0.8` → CRITICAL

**Model persistence:** Pickled to `/tmp/ai-models/isolation_forest.pkl`. In production, use S3/MinIO.

```python
class AnomalyEngine:
    def train(self, feature_vectors: list[np.ndarray]) -> None:
        # Requires minimum 50 samples
        # Generates 100 synthetic normals if insufficient data

    def predict(self, feature_vector: np.ndarray) -> dict:
        # Returns {anomaly_score, is_anomaly, severity, confidence}

    async def detect(self, scan_data: dict, db, organization_id, warehouse_id) -> dict:
        # Full pipeline: extract features → predict → create alert if anomaly
```

#### `ai-service/app/api/detect.py`
```python
@router.post("/discrepancy", response_model=DetectResponse)
async def detect_discrepancy(request: DetectRequest = Body(...), db: Session = Depends(get_db)):
    # Input: expected_qty, scanned_qty, item_category, supplier_id,
    #        dock_location, vehicle_type, operator_tenure_days,
    #        scan_timestamp, organization_id, warehouse_id, alert_type

@router.post("/feedback", status_code=201)
async def submit_feedback(request: FeedbackRequest = Body(...), db: Session = Depends(get_db)):
    # is_true_positive: true_positive | false_positive | unsure
    # Updates alert status automatically

@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    organization_id, warehouse_id, status, severity,
    limit=20, offset=0, db: Session = Depends(get_db),
):

@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: UUID, db: Session = Depends(get_db)):
    # Returns alert + all feedback entries
```

#### `ai-service/scripts/train_discrepancy.py`
```bash
# Weekly retraining (run via cron or scheduled job)
python scripts/train_discrepancy.py
```

**What it does:**
1. Fetches last 90 days of alerts with feature vectors
2. If < 50 samples, generates 100 synthetic normal events
3. Trains Isolation Forest
4. Saves model to `/tmp/ai-models/isolation_forest.pkl`
5. Logs false-positive patterns for review

### 4.4 Usage
```bash
# Detect on a scan event
curl -X POST http://localhost:8003/ai/detect/discrepancy \
  -H "Content-Type: application/json" \
  -d '{
    "expected_qty": 100,
    "scanned_qty": 45,
    "item_category": "electronics",
    "supplier_id": "supplier-uuid",
    "dock_location": "Dock-A",
    "scan_timestamp": "2026-06-02T14:30:00Z",
    "organization_id": "org-uuid",
    "warehouse_id": "wh-uuid"
  }'

# Response:
# {
#   "anomaly_score": -0.73,
#   "is_anomaly": true,
#   "severity": "high",
#   "confidence": 0.91,
#   "alert_id": "uuid-here",
#   "suggested_action": "SHORT detected: expected 100, scanned 45..."
# }

# Submit feedback
curl -X POST http://localhost:8003/ai/detect/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "alert-uuid",
    "is_true_positive": "true_positive",
    "actual_discrepancy_type": "short",
    "actual_variance_qty": -55
  }'

# List alerts
curl "http://localhost:8003/ai/detect/alerts?status=open&severity=high"

# Retrain
docker exec -it horizon_ai bash -c "python scripts/train_discrepancy.py"
```

---

<a name="build-commands"></a>
## 5. Docker Build & Test Commands

### Prerequisites
Ensure `ai_db` exists and `pgvector` extension is installed:
```bash
docker exec -it horizon_postgres psql -U horizon_user -d ai_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Build
```bash
# Full rebuild of ai-service
docker compose up --build -d ai-service

# Watch logs
docker compose logs -f ai-service
```

### Verify endpoints
```bash
# Health check
curl http://localhost:8003/health

# MCP SSE (returns 503 if MCP SDK not available, 200 if streaming)
curl http://localhost:8003/mcp/sse

# Ingestion (upload)
curl -X POST http://localhost:8003/ai/asn/ingest \
  -F "file=@test.pdf" -F "organization_id=test-org"

# Copilot
curl -X POST http://localhost:8003/ai/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'

# Detection
curl -X POST http://localhost:8003/ai/detect/discrepancy \
  -H "Content-Type: application/json" \
  -d '{"expected_qty": 100, "scanned_qty": 100}'
```

### Database tables
All tables are auto-created on startup via `Base.metadata.create_all()` in `main.py` lifespan.

---

<a name="env-vars"></a>
## 6. Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://.../ai_db` | Postgres connection for ai-service |
| `CORE_SERVICE_URL` | `http://localhost:8001` | core-service base URL |
| `IDENTITY_SERVICE_URL` | `http://localhost:8000` | identity-service base URL |
| `SERVICE_CLIENT_ID` | `ai-service` | Client ID for M2M JWT |
| `SERVICE_CLIENT_SECRET` | *(required)* | Generated by seed script |
| `LLM_PROVIDER` | `openai` | `openai` \| `anthropic` \| `ollama` |
| `OPENAI_API_KEY` | *(required for OpenAI)* | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `ANTHROPIC_API_KEY` | *(required for Anthropic)* | Anthropic API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama host |
| `EMBEDDING_PROVIDER` | `openai` | `openai` \| `ollama` |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSIONS` | `1536` | Must match model output size |
| `RAG_TOP_K` | `5` | Number of chunks retrieved |
| `RAG_SIMILARITY_THRESHOLD` | `0.75` | Minimum cosine similarity |
| `MCP_SERVER_NAME` | `horizon-wms-mcp` | MCP server identifier |

---

<a name="api-summary"></a>
## 7. API Endpoint Summary

### MCP (Phase 1)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/mcp/sse` | MCP SSE transport |
| POST | `/mcp/messages/` | MCP JSON-RPC message endpoint |

### ASN Ingestion (Phase 2A)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai/asn/ingest` | Upload document (PDF/Excel/image), returns job_id (202) |
| POST | `/ai/asn/create` | Create ASN from structured JSON (manual entry / transfer / API), returns job_id (202) |
| GET | `/ai/asn/ingest/{job_id}` | Poll job status + extracted data |
| POST | `/ai/asn/ingest/{job_id}/review` | Confirm or reject draft |

### SOP Copilot (Phase 2B)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai/copilot/ask` | Ask a question, get grounded answer |
| GET | `/ai/copilot/history` | Audit log of interactions |

### Discrepancy Detector (Phase 2C)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai/detect/discrepancy` | Submit scan event, get anomaly assessment |
| POST | `/ai/detect/feedback` | Submit TP/FP feedback |
| GET | `/ai/detect/alerts` | List alerts with filters |
| GET | `/ai/detect/alerts/{alert_id}` | Alert detail + feedback |

### Shared
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

---

## File Map (All New/Created Files)

```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Updated: includes all 4 routers + table creation
│   ├── config.py                  # Updated: +embedding, rag, mcp settings
│   ├── database.py                # NEW: SQLAlchemy engine + session
│   ├── api/
│   │   ├── __init__.py
│   │   ├── mcp.py                 # Phase 1: SSE transport
│   │   ├── ingest.py              # Phase 2A: upload, status, review
│   │   ├── copilot.py             # Phase 2B: ask, history
│   │   └── detect.py              # Phase 2C: detect, feedback, alerts
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── core_service.py        # Updated: +search_suppliers, search_items, create_asn_draft
│   │   └── identity_service.py    # Phase 1: M2M JWT client
│   ├── models/
│   │   ├── __init__.py            # Updated: exports all models
│   │   ├── ingestion_job.py       # Phase 2A
│   │   ├── vector_chunk.py        # Phase 2B
│   │   ├── chat_log.py            # Phase 2B
│   │   └── discrepancy_alert.py   # Phase 2C
│   └── services/
│       ├── mcp_server.py          # Phase 1: 6 read-only tools
│       ├── doc_parser.py          # Phase 2A: PDF/Excel/image parsing
│       ├── extractor.py           # Phase 2A: LLM document classifier + structured extraction
│       ├── ingestion_validator.py # Phase 2A: field completeness, PO match, duplicate check, supplier/SKU validation
│       ├── embedding.py           # Phase 2B: text → vector
│       ├── rag_engine.py          # Phase 2B: retrieval + generation
│       └── anomaly_engine.py      # Phase 2C: Isolation Forest
├── scripts/
│   ├── mcp_stdio.py               # Phase 1: stdio transport for Claude Desktop
│   ├── embed_sops.py              # Phase 2B: one-shot SOP ingestion
│   └── train_discrepancy.py       # Phase 2C: weekly model retraining
├── Dockerfile
├── requirements.txt               # Updated: +sqlalchemy, psycopg2-binary
└── knowledge_base/                # Create this dir, add SOP markdown/PDF files
    └── sops/
```

---

*End of Phase 1 & Phase 2 Knowledge Transfer Document.*
