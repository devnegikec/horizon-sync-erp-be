# Analytics Enhancement Plan — QSeal QR Scan Analytics

> **Status:** Planning
> **Strategy:** Enhance existing `qr_scan_events` + add `qr_scan_interactions` table
> **Users:** Anonymous consumers scanning product QR codes

---

## Current State (What Already Exists)

| Layer            | File                                       | What It Does                                                                                                                           |
| ---------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Model**        | `app/models/qr_scan_event.py`              | `QRScanEvent` — serial_number, device_type, os, browser, ip_address, city, state, country, lat/lng, scan_timestamp, extra_data (JSONB) |
| **Model**        | `app/models/product_item.py`               | `ProductItem` — links serial_number → QRProduct, has scan_count, last_scanned_at                                                       |
| **Model**        | `app/models/qr_product.py`                 | `QRProduct` — has `qr_type`, `landing_page`                                                                                            |
| **Schema**       | `app/schemas/analytics.py`                 | `QRScanEventIngest`, `QRScanEventResponse`, `QRScanAnalyticsResponse`                                                                  |
| **Repository**   | `app/repositories/analytics_repository.py` | `QRScanEventRepository` — create, list, get_scan_analytics (by date/country/device)                                                    |
| **Service**      | `app/services/analytics_service.py`        | `AnalyticsService` — ingest_scan, list_scan_events, get_scan_analytics                                                                 |
| **Endpoint**     | `app/api/v1/endpoints/analytics.py`        | `POST /analytics/scans/ingest` (public), `GET /analytics/scans`, `GET /analytics/scans/summary`                                        |
| **Migration**    | `alembic/versions/024_*.py`                | Created `qr_scan_events` table                                                                                                         |
| **Feature Flag** | `app/core/constants.py`                    | `ANALYTICS_MODULE_ENABLED = "analytics_module_enabled"`                                                                                |

### Gaps vs Requirements

| Requirement            | Current State                          | What's Missing                            |
| ---------------------- | -------------------------------------- | ----------------------------------------- |
| Collect user agent     | Raw strings (device_type, os, browser) | No auto-parsing from User-Agent header    |
| IP → geolocation       | Client sends city/country              | No server-side IP geolocation fallback    |
| QR code type           | `qr_type` on QRProduct                 | Not captured in scan event                |
| Call to Action         | None                                   | No CTA tracking at all                    |
| Post-scan interactions | None                                   | No way to track what user does after scan |
| Referrer tracking      | None                                   | No referrer URL captured                  |

---

## Phase 1: Database Schema Enhancement

### What We Build

Add 5 new columns to `qr_scan_events` + create `qr_scan_interactions` table for post-scan activity.

### Database Changes (Alembic Migration)

**File:** `alembic/versions/0xx_enhance_qr_scan_events.py`

```python
"""Enhance qr_scan_events + add qr_scan_interactions

Revision ID: 0xx_enhance_qr_scan_events
Revises: 028_add_analytics_module
"""

def upgrade():
    # ── Add columns to qr_scan_events ─────────────────────────────────
    op.add_column('qr_scan_events',
        sa.Column('user_agent_raw', sa.Text, nullable=True))
    op.add_column('qr_scan_events',
        sa.Column('user_agent_parsed', postgresql.JSONB, nullable=True))
    op.add_column('qr_scan_events',
        sa.Column('qr_type', sa.String(30), nullable=True))
    op.add_column('qr_scan_events',
        sa.Column('cta_action', sa.String(50), nullable=True))
    op.add_column('qr_scan_events',
        sa.Column('referrer_url', sa.Text, nullable=True))
    op.add_column('qr_scan_events',
        sa.Column('language', sa.String(10), nullable=True))

    # ── Create qr_scan_interactions ───────────────────────────────────
    op.create_table(
        'qr_scan_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  nullable=False, index=True),
        sa.Column('scan_event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qr_scan_events.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('interaction_target', sa.Text, nullable=True),
        sa.Column('interaction_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()')),
    )
    op.create_index('idx_qr_interactions_scan',
                    'qr_scan_interactions', ['scan_event_id'])


def downgrade():
    op.drop_table('qr_scan_interactions')
    op.drop_column('qr_scan_events', 'language')
    op.drop_column('qr_scan_events', 'referrer_url')
    op.drop_column('qr_scan_events', 'cta_action')
    op.drop_column('qr_scan_events', 'qr_type')
    op.drop_column('qr_scan_events', 'user_agent_parsed')
    op.drop_column('qr_scan_events', 'user_agent_raw')
```

### Field Definitions

| Column              | Type       | Purpose                                                                                              |
| ------------------- | ---------- | ---------------------------------------------------------------------------------------------------- |
| `user_agent_raw`    | Text       | Raw User-Agent header string (e.g. `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)...`)                    |
| `user_agent_parsed` | JSONB      | Auto-parsed: `{browser, browser_version, os, os_version, device_type, is_mobile, is_tablet, is_bot}` |
| `qr_type`           | String(30) | Copied from QRProduct.qr_type at scan time (e.g. `product_auth`, `marketing`, `warranty`)            |
| `cta_action`        | String(50) | What CTA the user engaged with (e.g. `view_product`, `visit_website`, `verify_auth`, `call_support`) |
| `referrer_url`      | Text       | HTTP Referer header                                                                                  |
| `language`          | String(10) | Accept-Language header (e.g. `en-US`)                                                                |

### `qr_scan_interactions` Table

| Column               | Type       | Purpose                                                                                      |
| -------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| `scan_event_id`      | UUID FK    | Links to the parent scan                                                                     |
| `interaction_type`   | String(50) | Generic type: `click`, `page_view`, `form_submit`, `call`, `share`, `download`, `video_play` |
| `interaction_target` | Text       | URL clicked, phone number called, etc.                                                       |
| `interaction_data`   | JSONB      | Any extra data: `{button_label, duration_ms, scroll_depth, ...}`                             |

### How to Test Phase 1

```bash
# 1. Run the migration
cd core-service
python -m alembic upgrade head

# 2. Verify new columns exist
docker exec -it horizon_postgres psql -U horizon_user -d core_db -c \
  "\d qr_scan_events"

# 3. Verify new table exists
docker exec -it horizon_postgres psql -U horizon_user -d core_db -c \
  "\d qr_scan_interactions"
```

---

## Phase 2: Enhanced Scan Ingestion

### What We Build

1. **User-Agent auto-parser** — Parse browser, OS, device from raw UA string
2. **Server-side IP geolocation** — Use free `ip-api.com` as fallback when client doesn't send location
3. **QR type lookup** — Automatically resolve `qr_type` from the `ProductItem` → `QRProduct` chain
4. **Enhanced ingest endpoint** — Accept new fields + auto-populate parsed data

### New Dependency

Add to `core-service/requirements.txt`:

```
user-agents==2.2.0
```

### Files to Create/Modify

| Action     | File                                 | Purpose                                                                |
| ---------- | ------------------------------------ | ---------------------------------------------------------------------- |
| **CREATE** | `app/services/geoip_service.py`      | IP → location lookup (ip-api.com free tier)                            |
| **CREATE** | `app/services/user_agent_service.py` | UA string → parsed device/browser/OS                                   |
| **MODIFY** | `app/schemas/analytics.py`           | Add new fields to `QRScanEventIngest` + `QRScanEventResponse`          |
| **MODIFY** | `app/models/qr_scan_event.py`        | Add new columns to model                                               |
| **MODIFY** | `app/services/analytics_service.py`  | Auto-enrich scan data before saving                                    |
| **MODIFY** | `app/api/v1/endpoints/analytics.py`  | Accept `User-Agent`, `Referer`, `Accept-Language` from request headers |

### Code: `app/services/user_agent_service.py`

```python
"""Auto-parse User-Agent strings into structured device/browser/OS data."""
from user_agents import parse


def parse_user_agent(ua_string: str | None) -> dict | None:
    """Parse a User-Agent string. Returns None if input is empty."""
    if not ua_string:
        return None
    ua = parse(ua_string)
    return {
        "browser": ua.browser.family,
        "browser_version": ua.browser.version_string,
        "os": ua.os.family,
        "os_version": ua.os.version_string,
        "device_type": _device_type(ua),
        "is_mobile": ua.is_mobile,
        "is_tablet": ua.is_tablet,
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot,
    }


def _device_type(ua) -> str:
    if ua.is_tablet:
        return "tablet"
    if ua.is_mobile:
        return "mobile"
    if ua.is_pc:
        return "desktop"
    return "unknown"
```

### Code: `app/services/geoip_service.py`

```python
"""Server-side IP geolocation via ip-api.com (free, no API key needed)."""
import logging
import httpx

logger = logging.getLogger(__name__)

IP_API_URL = "http://ip-api.com/json/{}?fields=status,country,regionName,city,lat,lon"


async def lookup_ip(ip_address: str | None) -> dict | None:
    """Look up geolocation for an IP. Returns None on failure."""
    if not ip_address or ip_address in ("127.0.0.1", "::1", "localhost"):
        return None
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(IP_API_URL.format(ip_address))
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country"),
                    "state": data.get("regionName"),
                    "city": data.get("city"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
    except Exception as e:
        logger.warning("geoip lookup failed for %s: %s", ip_address, e)
    return None
```

### Code: Modified `app/services/analytics_service.py` (ingest_scan)

```python
# Add these imports at top
from app.services.user_agent_service import parse_user_agent
from app.services.geoip_service import lookup_ip

# Replace the ingest_scan method:
async def ingest_scan(
    self,
    data: QRScanEventIngest,
    organization_id: UUID,
    request_headers: dict | None = None,
):
    """Record a QR scan event with auto-enrichment."""
    payload = data.model_dump()
    payload["organization_id"] = organization_id
    payload["scan_timestamp"] = datetime.now(UTC)

    # ── Auto-enrich from HTTP headers ──────────────────────────────
    headers = request_headers or {}
    ua_raw = headers.get("user-agent")
    payload["user_agent_raw"] = ua_raw
    payload["user_agent_parsed"] = parse_user_agent(ua_raw)
    payload["referrer_url"] = headers.get("referer")
    payload["language"] = headers.get("accept-language", "")[:10]

    # ── Auto-resolve QR type from ProductItem → QRProduct ──────────
    if data.product_item_id and not data.extra_data:
        # Only look up if product_item_id is provided
        pass  # resolved in repository or via JOIN

    # ── Server-side IP geolocation (fallback) ──────────────────────
    if not data.city and not data.country:
        geo = await lookup_ip(data.ip_address)
        if geo:
            payload.update(geo)

    event = self.scan_repo.create(payload)
    logger.info(
        "[ANALYTICS] scan ingested org=%s serial=%s cta=%s ua=%s",
        organization_id, data.serial_number,
        data.cta_action, payload["user_agent_parsed"],
    )
    return event
```

### Code: Modified `app/api/v1/endpoints/analytics.py` (ingest endpoint)

```python
from fastapi import Request  # add import

@router.post(
    "/scans/ingest",
    response_model=QRScanEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a QR scan event (public — called by QR landing page)",
)
async def ingest_scan(                         # ← make async
    data: QRScanEventIngest,
    request: Request,                           # ← new: access raw request
    organization_id: UUID = Query(...),
    service: AnalyticsService = Depends(get_service),
):
    headers = dict(request.headers)
    return await service.ingest_scan(data, organization_id, headers)
```

### How to Test Phase 2

```bash
# 1. Ingest a scan with User-Agent header (simulating iPhone Safari)
curl -X POST http://localhost:9000/api/v1/analytics/scans/ingest \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" \
  -H "Accept-Language: en-IN,en;q=0.9" \
  -H "Referer: https://instagram.com/product-link" \
  -d '{
    "serial_number": "TEST-SERIAL-001",
    "ip_address": "8.8.8.8",
    "cta_action": "view_product"
  }' \
  "?organization_id=YOUR_ORG_UUID"

# 2. Verify user_agent_parsed was auto-populated
curl http://localhost:9000/api/v1/analytics/scans \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "?serial_number=TEST-SERIAL-001&page_size=1"

# Expected: response includes user_agent_parsed with browser, os, device_type fields
```

---

## Phase 3: Post-Scan Interaction Tracking

### What We Build

A new endpoint that the QR landing page calls whenever the user performs an action (click, form submit, etc.).

### Files to Create/Modify

| Action     | File                                       | Purpose                                                                        |
| ---------- | ------------------------------------------ | ------------------------------------------------------------------------------ |
| **CREATE** | `app/models/qr_scan_interaction.py`        | SQLAlchemy model                                                               |
| **MODIFY** | `app/models/__init__.py`                   | Export new model                                                               |
| **MODIFY** | `app/schemas/analytics.py`                 | Add `ScanInteractionIngest` + `ScanInteractionResponse`                        |
| **MODIFY** | `app/repositories/analytics_repository.py` | Add `ScanInteractionRepository`                                                |
| **MODIFY** | `app/services/analytics_service.py`        | Add interaction methods                                                        |
| **MODIFY** | `app/api/v1/endpoints/analytics.py`        | Add `POST /scans/{scan_id}/interactions` + `GET /scans/{scan_id}/interactions` |

### Code: `app/models/qr_scan_interaction.py`

```python
"""QR Scan Interaction model — tracks post-scan user actions."""
import uuid
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from app.database import Base
from app.models.types import JSONB, UUID


class QRScanInteraction(Base):
    __tablename__ = "qr_scan_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    scan_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("qr_scan_events.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    interaction_type = Column(String(50), nullable=False)
    interaction_target = Column(Text, nullable=True)
    interaction_data = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

### Code: New Schemas (add to `app/schemas/analytics.py`)

```python
class ScanInteractionIngest(BaseModel):
    """Payload: record a post-scan interaction."""
    interaction_type: str            # click, page_view, form_submit, call, share, download
    interaction_target: str | None = None   # URL, phone number, etc.
    interaction_data: dict[str, Any] | None = None  # {button_label, duration_ms, ...}


class ScanInteractionResponse(BaseModel):
    id: UUID
    scan_event_id: UUID
    interaction_type: str
    interaction_target: str | None
    interaction_data: dict[str, Any] | None
    created_at: datetime
    model_config = {"from_attributes": True}
```

### Code: New Repository (add to `app/repositories/analytics_repository.py`)

```python
class ScanInteractionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> QRScanInteraction:
        interaction = QRScanInteraction(**data)
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    def list_by_scan(self, scan_event_id: UUID) -> list[QRScanInteraction]:
        return (
            self.db.query(QRScanInteraction)
            .filter(QRScanInteraction.scan_event_id == scan_event_id)
            .order_by(QRScanInteraction.created_at.asc())
            .all()
        )
```

### Code: New Endpoints (add to `app/api/v1/endpoints/analytics.py`)

```python
@router.post(
    "/scans/{scan_id}/interactions",
    response_model=ScanInteractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a post-scan interaction (public)",
)
def record_interaction(
    scan_id: UUID,
    data: ScanInteractionIngest,
    organization_id: UUID = Query(...),
    service: AnalyticsService = Depends(get_service),
):
    return service.record_interaction(scan_id, data, organization_id)


@router.get(
    "/scans/{scan_id}/interactions",
    summary="Get all interactions for a scan event",
)
def list_interactions(
    scan_id: UUID,
    service: AnalyticsService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    return service.list_interactions(scan_id)
```

### How to Test Phase 3

```bash
# 1. First ingest a scan (get the scan ID from response)
SCAN_RESPONSE=$(curl -s -X POST http://localhost:9000/api/v1/analytics/scans/ingest \
  -H "Content-Type: application/json" \
  -d '{"serial_number": "INTERACTION-TEST-001", "cta_action": "view_product"}' \
  "?organization_id=YOUR_ORG_UUID")

SCAN_ID=$(echo $SCAN_RESPONSE | jq -r '.id')
echo "Scan ID: $SCAN_ID"

# 2. Record a "click website" interaction
curl -X POST "http://localhost:9000/api/v1/analytics/scans/${SCAN_ID}/interactions?organization_id=YOUR_ORG_UUID" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_type": "click",
    "interaction_target": "https://example.com/product-page",
    "interaction_data": {"button_label": "Visit Website", "duration_ms": 4500}
  }'

# 3. Record a "call support" interaction
curl -X POST "http://localhost:9000/api/v1/analytics/scans/${SCAN_ID}/interactions?organization_id=YOUR_ORG_UUID" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_type": "call",
    "interaction_target": "+91-9876543210",
    "interaction_data": {"call_duration_seconds": 120}
  }'

# 4. List all interactions for this scan (requires auth)
curl "http://localhost:9000/api/v1/analytics/scans/${SCAN_ID}/interactions" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Phase 4: Enhanced Analytics Endpoints

### What We Build

New aggregated endpoints that include CTA and interaction insights.

### New Endpoints

| Method | Path                                  | Auth | Purpose                                                                  |
| ------ | ------------------------------------- | ---- | ------------------------------------------------------------------------ |
| `GET`  | `/analytics/scans/cta-breakdown`      | Yes  | CTA action distribution (how many clicked website vs called vs verified) |
| `GET`  | `/analytics/scans/geo-heatmap`        | Yes  | Scans grouped by city with lat/lng for map rendering                     |
| `GET`  | `/analytics/scans/device-timeline`    | Yes  | Scans over time grouped by device type (mobile vs desktop)               |
| `GET`  | `/analytics/scans/interaction-funnel` | Yes  | Funnel: scans → CTA clicks → conversions                                 |

### Code: New Repository Methods (add to `QRScanEventRepository`)

```python
def get_cta_breakdown(
    self, organization_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Distribution of CTA actions across all scans."""
    q = self.db.query(
        QRScanEvent.cta_action,
        func.count().label("count"),
    ).filter(QRScanEvent.organization_id == organization_id)
    if date_from:
        q = q.filter(QRScanEvent.scan_timestamp >= date_from)
    if date_to:
        q = q.filter(QRScanEvent.scan_timestamp <= date_to)
    rows = q.group_by(QRScanEvent.cta_action).order_by(func.count().desc()).all()
    return [{"cta_action": r.cta_action or "unknown", "count": r.count} for r in rows]


def get_geo_heatmap(
    self, organization_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 500,
) -> list[dict]:
    """Scans grouped by city with coordinates for map rendering."""
    q = self.db.query(
        QRScanEvent.city, QRScanEvent.state, QRScanEvent.country,
        QRScanEvent.latitude, QRScanEvent.longitude,
        func.count().label("count"),
    ).filter(
        QRScanEvent.organization_id == organization_id,
        QRScanEvent.latitude.isnot(None),
    )
    if date_from:
        q = q.filter(QRScanEvent.scan_timestamp >= date_from)
    if date_to:
        q = q.filter(QRScanEvent.scan_timestamp <= date_to)
    rows = q.group_by(
        QRScanEvent.city, QRScanEvent.state, QRScanEvent.country,
        QRScanEvent.latitude, QRScanEvent.longitude,
    ).order_by(func.count().desc()).limit(limit).all()
    return [
        {
            "city": r.city, "state": r.state, "country": r.country,
            "latitude": float(r.latitude), "longitude": float(r.longitude),
            "count": r.count,
        }
        for r in rows
    ]
```

### How to Test Phase 4

```bash
# 1. CTA Breakdown
curl "http://localhost:9000/api/v1/analytics/scans/cta-breakdown" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: {"breakdown": [{"cta_action": "view_product", "count": 45}, ...]}

# 2. Geo Heatmap
curl "http://localhost:9000/api/v1/analytics/scans/geo-heatmap" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: [{"city": "Mumbai", "latitude": 19.07, "longitude": 72.87, "count": 23}, ...]

# 3. Interaction Funnel
curl "http://localhost:9000/api/v1/analytics/scans/interaction-funnel" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: {"scans": 100, "with_cta": 75, "with_interactions": 30, "conversion_rate": 0.3}
```

---

## Phase 5: CTA Configuration (Optional)

### What We Build

Allow organizations to configure which CTAs appear on their QR landing pages via the admin API.

### New Table: `qr_cta_configs`

```sql
CREATE TABLE qr_cta_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    product_id UUID REFERENCES qr_products(id),
    cta_type VARCHAR(50) NOT NULL,       -- view_product, visit_website, call_support, verify_auth
    cta_label VARCHAR(100) NOT NULL,     -- "Verify Authenticity", "Visit Our Website"
    cta_target TEXT,                      -- URL, phone number, etc.
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### CRUD Endpoints

```
POST   /admin/qr-products/{product_id}/ctas     — Create CTA
GET    /admin/qr-products/{product_id}/ctas     — List CTAs
PUT    /admin/qr-products/{product_id}/ctas/{id} — Update CTA
DELETE /admin/qr-products/{product_id}/ctas/{id} — Delete CTA
```

> **Skip Phase 5 for now** — the generic JSONB approach in Phases 1-4 already supports any CTA type without configuration.

---

## Summary: File Change Map

```
Phase 1 — Database
├── CREATE  alembic/versions/0xx_enhance_qr_scan_events.py

Phase 2 — Enhanced Ingestion
├── CREATE  app/services/user_agent_service.py
├── CREATE  app/services/geoip_service.py
├── MODIFY  app/models/qr_scan_event.py          (+5 columns)
├── MODIFY  app/schemas/analytics.py              (+new fields in ingest/response)
├── MODIFY  app/services/analytics_service.py     (enrich scan data)
├── MODIFY  app/api/v1/endpoints/analytics.py     (read headers)
├── MODIFY  requirements.txt                      (+user-agents)

Phase 3 — Interactions
├── CREATE  app/models/qr_scan_interaction.py
├── MODIFY  app/models/__init__.py                (export new model)
├── MODIFY  app/schemas/analytics.py              (+interaction schemas)
├── MODIFY  app/repositories/analytics_repository.py (+ScanInteractionRepository)
├── MODIFY  app/services/analytics_service.py     (+interaction methods)
├── MODIFY  app/api/v1/endpoints/analytics.py     (+interaction endpoints)

Phase 4 — Enhanced Analytics
├── MODIFY  app/repositories/analytics_repository.py (+cta_breakdown, geo_heatmap)
├── MODIFY  app/services/analytics_service.py     (+new analytics methods)
├── MODIFY  app/schemas/analytics.py              (+response schemas)
├── MODIFY  app/api/v1/endpoints/analytics.py     (+4 new GET endpoints)
```

---

## Quick Start: Run All Tests After Each Phase

```bash
# After each phase, run these to validate nothing is broken:

# 1. Run migrations
cd core-service && python -m alembic upgrade head

# 2. Check the app starts
curl http://localhost:9000/api/v1/health

# 3. Run existing analytics tests (if any)
cd core-service && python -m pytest tests/ -k analytics -v

# 4. Test the new endpoint for that phase (see curl commands in each phase)
```
