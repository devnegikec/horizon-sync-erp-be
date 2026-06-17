# 3D Warehouse View — Implementation Document

**Covers:** Phase 0 (Dynamic Layout Designer) → Phase 4 (Polish)  
**Last updated:** 2026-06-17

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 0 — Dynamic Layout Designer](#2-phase-0--dynamic-layout-designer)
3. [Phase 1–2 — 3D Canvas Foundation](#3-phase-12--3d-canvas-foundation)
4. [Phase 3 — Real-Time Updates](#4-phase-3--real-time-updates)
5. [Phase 4 — Polish](#5-phase-4--polish)
6. [API Reference](#6-api-reference)
7. [Data Flow](#7-data-flow)
8. [Database Schema](#8-database-schema)
9. [Testing](#9-testing)
10. [Performance Notes](#10-performance-notes)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                   │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────┐ │
│  │ Layout Designer     │    │ 3D Canvas View      │    │ Suggest     │ │
│  │ (form-based)        │    │ (isometric WebGL)   │    │ Panel       │ │
│  └──────────┬──────────┘    └──────────┬──────────┘    └──────┬──────┘ │
│             │                          │                      │        │
│             └────────────┬───────────┘──────────────────────┘        │
│                          REST API + WebSocket                         │
└──────────────────────────┬────────────────────────────────────────────┘
                           │
┌──────────────────────────┼────────────────────────────────────────────┐
│                          │         BACKEND                              │
│  ┌───────────────────────┴──────────────────────────────────────┐     │
│  │  FastAPI Routers                                               │     │
│  │  ├── /floor-plans  (preview, apply, list, get)                │     │
│  │  ├── /wms-3d       (layout, status, suggest, reserve)         │     │
│  │  └── /items/picker (search items for suggestion panel)      │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                          │                                            │
│  ┌───────────────────────┴──────────────────────────────────────┐     │
│  │  Services                                                      │     │
│  │  ├── FloorPlanGeneratorService  → creates WarehouseLocations  │     │
│  │  ├── Warehouse3DService         → builds layout tree            │     │
│  │  ├── LocationSuggestionService → ranks optimal bins           │     │
│  │  ├── BinReservationService     → TTL-bound bin locking        │     │
│  │  └── RedisPubSub               → real-time broadcast          │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                          │                                            │
│  ┌───────────────────────┴──────────────────────────────────────┐     │
│  │  PostgreSQL  (tables)                                           │     │
│  │  ├── warehouses_extended                                      │     │
│  │  ├── warehouse_floor_plans  ← NEW (Phase 0)                 │     │
│  │  ├── warehouse_locations    ← zone/aisle/bay/level/bin      │     │
│  │  ├── bin_reservations       ← TTL worker reservations       │     │
│  │  └── bin_stock_levels       ← quantity per bin/item         │     │
│  └──────────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 0 — Dynamic Layout Designer

### 2.1 Goal
Allow warehouse managers to design a complete location hierarchy (zones → aisles → bays → levels → bins) through a form-based UI, preview the outcome, and apply it in one click — automatically generating `WarehouseLocation` rows with correct 3D coordinates.

### 2.2 Backend

#### 2.2.1 Migration
`alembic/versions/060_add_warehouse_floor_plans.py`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | auto-generated |
| `organization_id` | UUID, indexed | **No FK** — avoids cross-service dependency on `organizations` table |
| `warehouse_id` | UUID, indexed | FK → `warehouses_extended.id` (CASCADE) |
| `name` | VARCHAR(255) | e.g. "Layout v1" |
| `description` | TEXT | optional |
| `config` | JSONB | serialised `FloorPlanConfig` |
| `generated_at` | TIMESTAMPTZ | when `apply` was last run |
| `is_active` | BOOLEAN | soft-delete flag |
| `created_at` / `updated_at` | TIMESTAMPTZ | audit |

#### 2.2.2 Model
`app/models/warehouse_floor_plan.py`

- `WarehouseFloorPlan` SQLAlchemy declarative model.
- `relationship("Warehouse", lazy="select")` for convenient warehouse access.

#### 2.2.3 Schemas
`app/schemas/floor_plan.py`

| Schema | Purpose |
|---|---|
| `AisleSpec` | `code`, `orientation` (x/y), `grid_x/y`, `num_bays`, `bay_spacing`, `num_levels`, `bins_per_level`, `bin_capacity`, `bay_width`, `level_height` |
| `ZoneSpec` | `code`, `name`, `grid_x/y`, `aisles: list[AisleSpec]` |
| `FloorPlanConfig` | `grid_unit`, `zones: list[ZoneSpec]` |
| `FloorPlanPreviewRequest` | `warehouse_id`, `config` |
| `FloorPlanPreviewResponse` | `summary` (zone/aisle/bay/level/bin counts), `sample_codes`, `total_locations` |
| `FloorPlanApplyRequest` | `warehouse_id`, `config`, `name`, `replace_existing: bool` |
| `FloorPlanApplyResponse` | `floor_plan_id`, `locations_created`, `locations_deleted` |
| `FloorPlanResponse` | list/get response shape |

#### 2.2.4 Service
`app/services/floor_plan_generator_service.py`

**`preview(warehouse_id, org_id, config)`**
- Validates warehouse exists.
- Recursively counts zones/aisles/bays/levels/bins from config.
- Returns summary WITHOUT writing to DB.

**`apply(warehouse_id, org_id, config, name, replace_existing=False)`**
- If `replace_existing=True`: soft-deletes ALL existing `WarehouseLocation` rows for this warehouse (`is_active = false`).
- Creates full hierarchy in one transaction:
  1. Zone (`location_type="zone"`)
  2. Aisle (`location_type="aisle"`, `parent_location_id=zone`)
  3. Bay (`location_type="bay"`, `parent_location_id=aisle`)
  4. Level (`location_type="level"`, `parent_location_id=bay`)
  5. Bin (`location_type="bin"`, `parent_location_id=level`)
- **Position calculation:**
  - **X orientation:** bays increment `position_x` by `bay_spacing`; `position_y` fixed.
  - **Y orientation:** bays increment `position_y` by `bay_spacing`; `position_x` fixed.
  - **Z orientation:** levels increment `position_z` by `level_height`.
  - Zone origin offsets everything by `zone.grid_x / grid_y`.
- Codes follow `{wh_code}-{zone}-{aisle}-{bay}-{level}` pattern (e.g. `WH1-A-A01-B01-L1`).
- Persists config to `warehouse_floor_plans` table for later retrieval.

#### 2.2.5 API Endpoints
`app/api/v1/endpoints/floor_plans.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/floor-plans/preview` | `WAREHOUSE_READ` | Non-destructive preview |
| POST | `/floor-plans/apply` | `WAREHOUSE_CREATE` | Persist locations + config |
| GET | `/floor-plans` | `WAREHOUSE_READ` | List floor plans for warehouse |
| GET | `/floor-plans/{id}` | `WAREHOUSE_READ` | Get single floor plan |

### 2.3 Frontend

#### 2.3.1 Types
`apps/inventory/src/app/types/floorplan.types.ts`

TypeScript interfaces mirroring Pydantic schemas, plus factory functions:
- `defaultAisleSpec()` — returns a sensible default aisle (4 bays, 3 levels, 2 bins/level).
- `defaultZoneSpec()` — returns a default zone with one default aisle.
- `defaultFloorPlanConfig()` — returns a config with one default zone.

#### 2.3.2 API Client
`apps/inventory/src/app/utility/api/floorplan.ts`

| Function | Endpoint |
|---|---|
| `preview(token, body)` | `POST /floor-plans/preview` |
| `apply(token, body)` | `POST /floor-plans/apply` |
| `list(token, warehouseId)` | `GET /floor-plans?warehouse_id=...` |
| `get(token, id)` | `GET /floor-plans/{id}` |

#### 2.3.3 UI Component
`apps/inventory/src/app/components/wms/WarehouseLayoutDesigner.tsx`

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  Warehouse Layout Designer                       │
│  [Add Zone]  [Preview]  [Apply Layout]           │
├─────────────────────────────────────────────────┤
│  Zone A                                          │
│    ├─ Aisle A01  [x] bays, [x] levels, ...    │
│    │   [Add Aisle]  [Remove]                     │
│  Zone B                                          │
│    ├─ Aisle B01 ...                              │
│    │   [Add Aisle]  [Remove]                     │
│  [+ Add Zone]                                    │
├─────────────────────────────────────────────────┤
│  Preview Summary (after clicking Preview)        │
│    Zones: 2  Aisles: 3  Bays: 12  Levels: 36 ...  │
│    Sample codes: WH1-A-A01-B01-L1 ...            │
└─────────────────────────────────────────────────┘
```

**State management:**
- Local React state for `FloorPlanConfig` (zones → aisles → spec fields).
- `onChange` callbacks bubble up from nested `ZoneEditor` → `AisleEditor` → parent.
- `preview`/`apply` state tracks loading/error/success.

**Wiring in `WMSManagement.tsx`:**
- The "Layout" tab now has two sub-tabs: **Location Tree** (existing) and **Layout Designer** (new).
- Uses the same tab-switching pattern already established for the "Manage" section.

---

## 3. Phase 1–2 — 3D Canvas Foundation

### 3.1 Goal
Render the warehouse location hierarchy as an interactive isometric 3D view on an HTML5 Canvas, with click-to-select, drag-to-pan, and scroll-to-zoom.

### 3.2 Key Components

`apps/inventory/src/app/components/wms/Warehouse3DView.tsx`

**Isometric projection:**
```
screen_x = offset_x + (world_x - world_y) * (tile_width / 2)
screen_y = offset_y + (world_x + world_y) * (tile_height / 2) - world_z * z_height
```

**Constants:**
| Constant | Value | Meaning |
|---|---|---|
| `BASE_TW` | 48 px | Tile width at zoom 1.0 |
| `BASE_TH` | 24 px | Tile height at zoom 1.0 |
| `BASE_ZH` | 30 px | Vertical pixels per Z-unit |

**Bin rendering (`drawBin`):**
- Draws three visible faces: right (+X), left (+Y), top (+Z).
- Each face gets a slightly different shade to simulate lighting.
- **Pulse glow overlay** for reserved/suggested bins (animated via `requestAnimationFrame`).

**Hit testing (`hitTest`):**
- Tests screen-point against each bin's top-face parallelogram.
- Iterates in **reverse paint order** (front-most first) so front bins win.
- Uses cross-product sign test for point-in-quad.

**Color modes (default — Phase 1):**
| State | Colors |
|---|---|
| Selected | Sky-blue (`#f0f9ff` top, `#0ea5e9` left) |
| Suggested | Amber/gold (`#fef9c3` top, `#d97706` left) |
| Reserved | Blue (`#dbeafe` top, `#3b82f6` left) |
| Expiring items | Orange (`#fff7ed` top, `#ea580c` left) |
| Fill 0–30% | Green (`#bbf7d0` top, `#22c55e` left) |
| Fill 31–70% | Yellow (`#fef3c7` top, `#f59e0b` left) |
| Fill 71–100% | Red (`#fecaca` top, `#ef4444` left) |
| Inactive | Slate grey |

### 3.3 Data Hook
`apps/inventory/src/app/hooks/useWarehouse3D.ts`

- Fetches layout (`GET /wms-3d/layout`) on mount.
- Polls status (`GET /wms-3d/status`) every 5s as WebSocket fallback.
- Flattens the zone/aisle/bay/level/bin tree into `FlatBin[]` for renderer consumption.
- Merges live status data (fill %, reservation state) onto each `FlatBin`.

---

## 4. Phase 3 — Real-Time Updates

### 4.1 Goal
Show live bin fill levels, reservations, and worker positions without requiring a page refresh.

### 4.2 Backend

**Redis Pub/Sub** (`app/core/redis_pubsub.py`)

```python
class RedisPubSub:
    CHANNEL_BIN_EVENTS = "bin_events"
    
    async def publish_bin_event(bin_id, event_type, data)
    async def subscribe_bin_events(callback)
```

- Publishes events on every bin state change (reserve, release, stock movement).
- Subscribers receive JSON: `{bin_id, event_type, fill_pct, is_reserved, ...}`.
- Gracefully handles missing Redis (logs warning, does not crash).

**WebSocket endpoint** (`app/api/v1/endpoints/wms_3d.py` — if implemented)
- Opens a WebSocket connection per warehouse.
- Subscribes to Redis `bin_events` and forwards to client.
- Falls back to HTTP polling if WebSocket unavailable.

### 4.3 Frontend

- Canvas render loop checks `live_is_reserved` / `live_fill_pct` on each `FlatBin`.
- If any reserved/suggested bin exists, `requestAnimationFrame` keeps animating the pulse glow.
- Otherwise, renders a single static frame for performance.

---

## 5. Phase 4 — Polish

### 5.1 Bin Suggestion Panel

**Goal:** Let managers (or workers) find the optimal bin for a put-away or pick task.

**UI:** `BinSuggestionPanel` (embedded in `Warehouse3DView.tsx`)

```
┌────────────────────────┐
│ Find Optimal Bins      │
│ [Put-away] [Pick]      │
│ Item: [Search...]      │
│ Qty:  [1]              │
│ [Suggest bins]         │
│ ────────────────────── │
│ #1  WH1-A-A01-B01-L1   │
│     245 pts · Near dock│
│     Avail: 100 ~7s     │
│ #2  WH1-A-A01-B02-L1   │
│     ...                │
└────────────────────────┘
```

**How it works:**
1. User selects an item via `ItemPickerSelect` (reuses existing component, queries `/items/picker`).
2. User chooses task type (put-away or pick) and quantity.
3. Frontend calls `POST /wms-3d/suggest` with `worker_id = NIL_UUID` (`00000000-0000-0000-0000-000000000000`).
   - Using a nil UUID is safe because `worker_id` is only used to **exclude the worker's own reservations** from the blocked list. A manager exploring the warehouse has no reservations to exclude.
4. Backend `LocationSuggestionService` returns ranked suggestions.
5. Frontend highlights suggested bins in **gold/amber** on the 3D canvas.
6. Clicking a suggestion **centers the camera** on that bin and selects it.

**API:** `POST /wms-3d/suggest`

| Field | Type | Description |
|---|---|---|
| `task_type` | `"put_away" \| "pick"` | Required |
| `item_id` | UUID | Required |
| `quantity` | Decimal (>0) | Required |
| `warehouse_id` | UUID | Required |
| `worker_id` | UUID | Required (use nil for manager exploration) |
| `batch_number` | string? | Optional pick hint |
| `exclude_bin_ids` | UUID[] | Bins the worker already skipped |
| `worker_position` | `{x,y,z}?` | Defaults to dock position |
| `limit` | int (1–50) | Default 10 |

**Scoring (backend):**
- **Put-away:** allocation match (exclusive/preferred) → capacity ratio → dock proximity → same-item consolidation → item-group affinity.
- **Pick:** FEFO (expiry-based) → FIFO (age-based) → quantity match → route efficiency (distance from worker).

### 5.2 Heat-Map Color Mode

**Goal:** Give managers an instant visual of fill density across the entire warehouse.

**Implementation:**
- New `colorMode` state: `'status'` (default) or `'heat'`.
- `getHeatColors(fillPct)` computes HSL hue: `120 * (1 - fillPct/100)` → green (0%) to red (100%).
- When heat mode is active, reserved/suggested/selected overrides still take precedence.
- Toggle button in toolbar: `[Flame] Heat-map`.

### 5.3 Level-of-Detail (LOD)

**Goal:** Maintain 60fps when rendering 1000+ bins.

**Trigger conditions:**
- `sorted.length > 600` (dense warehouse)
- **OR** `zoom < 0.55` (zoomed out — bins are tiny)

**Effect:**
- `drawBin` skips per-face stroke outlines (fills only).
- Selected and suggested bins **always** keep their outline so they remain visible.
- In 2D view, `strokeRect` is skipped unless the bin is selected.

---

## 6. API Reference

### 6.1 Floor Plans

```
POST /api/v1/floor-plans/preview
Body: { warehouse_id: UUID, config: FloorPlanConfig }
→ { summary: { zone_count, aisle_count, bay_count, level_count, bin_count },
    sample_codes: string[], total_locations: int }

POST /api/v1/floor-plans/apply
Body: { warehouse_id: UUID, config: FloorPlanConfig, name: string, replace_existing?: bool }
→ { floor_plan_id: UUID, locations_created: int, locations_deleted: int }

GET /api/v1/floor-plans?warehouse_id=UUID
→ FloorPlanResponse[]

GET /api/v1/floor-plans/{id}
→ FloorPlanResponse
```

### 6.2 WMS 3D

```
GET /api/v1/wms-3d/layout?warehouse_id=UUID
→ LayoutResponse (full zone/aisle/bay/level/bin tree)

GET /api/v1/wms-3d/status?warehouse_id=UUID
→ StatusResponse (live fill %, reservations, workers)

POST /api/v1/wms-3d/suggest
Body: SuggestRequest
→ SuggestResponse (ranked suggestions with scores & reasons)

POST /api/v1/wms-3d/reserve
Body: { bin_id, worker_id, task_id?, task_type?, ttl_seconds? }
→ ReservationResponse

POST /api/v1/wms-3d/release
Body: { bin_id, worker_id }
→ ReleaseResponse

POST /api/v1/wms-3d/force-release/{bin_id}
→ ReleaseResponse (manager override)
```

---

## 7. Data Flow

### 7.1 Designing a Layout (Phase 0)

```
Manager → Layout Designer UI
  → fills zones / aisles / bays / levels / capacity
  → clicks "Preview"
    → POST /floor-plans/preview
      → FloorPlanGeneratorService.preview()
        → counts locations, builds sample codes
      ← { summary, sample_codes }
    → UI shows summary (no DB changes)
  → clicks "Apply Layout"
    → POST /floor-plans/apply
      → FloorPlanGeneratorService.apply()
        → (optional) soft-delete existing locations
        → creates zone → aisle → bay → level → bin hierarchy
        → computes position_x / position_y / position_z
        → inserts all rows in one transaction
        → persists config to warehouse_floor_plans
      ← { locations_created, locations_deleted }
    → Switch to 3D View tab
      → GET /wms-3d/layout
        → new bins appear immediately in isometric canvas
```

### 7.2 Finding Optimal Bins (Phase 4)

```
Manager → 3D View → clicks "Suggest"
  → selects item + quantity + task type
  → clicks "Suggest bins"
    → POST /wms-3d/suggest (worker_id = nil UUID)
      → LocationSuggestionService.suggest()
        → loads item, checks allocations
        → excludes reserved bins (except worker's own — none for nil UUID)
        → scores candidates by capacity/proximity/consolidation or FEFO/FIFO
        → sorts by score descending
      ← { suggestions, strategy_used, total_candidates_evaluated }
    → UI highlights suggested bin IDs in gold on canvas
    → list shows ranked suggestions with reasons
  → clicks a suggestion
    → canvas centers on that bin
    → bin is selected (sky-blue highlight)
```

### 7.3 Real-Time Status (Phase 3)

```
BinReservationService.reserve() / release()
  → RedisPubSub.publish_bin_event()
    → Redis channel "bin_events"
      → (WebSocket subscriber forwards to frontend)
        → useWarehouse3D hook receives update
          → merges new fill_pct / is_reserved into FlatBin[]
            → Canvas re-renders with updated colors + pulse animation
```

---

## 8. Database Schema

### 8.1 warehouse_floor_plans (NEW — Phase 0)

```sql
CREATE TABLE warehouse_floor_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL,
    warehouse_id UUID NOT NULL REFERENCES warehouses_extended(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL,
    generated_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_wfp_org ON warehouse_floor_plans(organization_id);
CREATE INDEX idx_wfp_wh ON warehouse_floor_plans(warehouse_id);
```

### 8.2 warehouse_locations (existing — populated by Phase 0)

Key columns for 3D positioning:

| Column | Type | Meaning |
|---|---|---|
| `position_x` | Numeric | World X coordinate (bay spacing along aisle) |
| `position_y` | Numeric | World Y coordinate (aisle spacing) |
| `position_z` | Numeric | World Z coordinate (level height) |
| `location_type` | ENUM | `zone` / `aisle` / `bay` / `level` / `bin` |
| `parent_location_id` | UUID FK | Hierarchy parent (bin → level → bay → aisle → zone) |
| `capacity` | Numeric | Max capacity for bins |
| `is_active` | BOOLEAN | Soft-delete flag |

### 8.3 bin_reservations (Phase 1)

| Column | Type | Meaning |
|---|---|---|
| `bin_location_id` | UUID FK | Reserved bin |
| `worker_id` | UUID | Worker who reserved |
| `task_id` / `task_type` | UUID/string | Optional task association |
| `expires_at` | TIMESTAMPTZ | TTL deadline |
| `released_at` | TIMESTAMPTZ | When released (null = active) |

---

## 9. Testing

### 9.1 Floor Plan Generator Tests
`tests/test_floor_plan_generator_service.py`

| Test | Validates |
|---|---|
| `test_preview_counts_match_config` | Summary counts (zones, aisles, bays, levels, bins) |
| `test_preview_does_not_persist` | Preview is read-only |
| `test_preview_unknown_warehouse_raises` | Proper `NotFoundError` |
| `test_apply_persists_full_hierarchy` | All 16 locations created (1z+1a+2b+6l+6bin) |
| `test_apply_generates_expected_bin_codes` | Code pattern `{wh}-{zone}-{aisle}-{bay}-{level}` |
| `test_apply_assigns_z_by_level` | Z position increments by `level_height` |
| `test_apply_x_orientation_spaces_bays_along_x` | Bay spacing along correct axis |
| `test_apply_replace_existing_deactivates_old` | `replace_existing=True` soft-deletes old bins |

Run: `pytest tests/test_floor_plan_generator_service.py -q`

### 9.2 Bin Reservation Tests
`tests/test_bin_reservation_service.py`

13 tests covering reserve, release, force-release, TTL expiry, concurrency conflicts.

Run: `pytest tests/test_bin_reservation_service.py -q`

---

## 10. Performance Notes

### 10.1 Canvas Rendering

| Scenario | Optimization |
|---|---|
| < 600 bins, zoom ≥ 0.55 | Full 3D faces + strokes |
| ≥ 600 bins OR zoom < 0.55 | LOD: fills only, skip strokes |
| No animated bins | Single static frame (no RAF loop) |
| Reserved/suggested bins present | RAF loop for pulse animation |

### 10.2 API Polling

- Status poll interval: **5 seconds** (configurable in `useWarehouse3D`).
- WebSocket (when available) eliminates polling overhead.

### 10.3 Database

- `FloorPlanGeneratorService.apply()` creates all locations in **one transaction**.
- `replace_existing=True` uses a single `UPDATE ... WHERE warehouse_id = ?` to soft-delete old bins — O(1) regardless of bin count.
- Indexes on `warehouse_locations(warehouse_id, organization_id, location_type, is_active)` ensure fast layout queries.

---

## Appendix A: File Inventory

### Backend (core-service)

| File | Phase | Purpose |
|---|---|---|
| `alembic/versions/060_add_warehouse_floor_plans.py` | 0 | Migration |
| `app/models/warehouse_floor_plan.py` | 0 | SQLAlchemy model |
| `app/schemas/floor_plan.py` | 0 | Pydantic schemas |
| `app/services/floor_plan_generator_service.py` | 0 | Generator service |
| `app/api/v1/endpoints/floor_plans.py` | 0 | FastAPI router |
| `app/models/__init__.py` | 0 | Model registration |
| `app/api/v1/router.py` | 0 | Router registration |
| `tests/test_floor_plan_generator_service.py` | 0 | Unit tests |
| `app/core/redis_pubsub.py` | 3 | Pub/sub for real-time |
| `app/services/location_suggestion_service.py` | 1–4 | Smart bin ranking |
| `app/services/bin_reservation_service.py` | 1 | TTL reservations |
| `app/api/v1/endpoints/wms_3d.py` | 1–4 | 3D API router |

### Frontend (inventory)

| File | Phase | Purpose |
|---|---|---|
| `types/floorplan.types.ts` | 0 | Floor plan TypeScript types |
| `utility/api/floorplan.ts` | 0 | Floor plan API client |
| `components/wms/WarehouseLayoutDesigner.tsx` | 0 | Layout designer UI |
| `components/wms/Warehouse3DView.tsx` | 1–4 | 3D canvas + suggestions + heat-map |
| `components/wms/WMSManagement.tsx` | 0,4 | Tab wiring |
| `components/wms/index.ts` | 0 | Barrel export |
| `hooks/useWarehouse3D.ts` | 2 | Data fetching + polling |
| `types/wms3d.types.ts` | 1 | 3D view TypeScript types |
| `utility/api/wms3d.ts` | 1 | 3D API client |
