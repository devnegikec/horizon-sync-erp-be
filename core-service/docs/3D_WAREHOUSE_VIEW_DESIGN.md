# 3D Warehouse View & Smart Location Engine — Design Document

> **Status:** Design & Planning  
> **Scope:** WMS Inbound/Outbound — 3D visualization, optimal location suggestions, concurrent worker coordination  
> **Architecture:** Frontend (React Three Fiber) + Backend API (FastAPI) + Real-time (WebSocket + Redis)

---

## 1. Executive Summary

Build a 3D interactive warehouse view that lets workers (receivers, pickers, put-away operators) visualize the warehouse layout and receive real-time optimal location suggestions. The system dynamically avoids bin contention between concurrent workers and ensures FIFO/FEFO compliance for item picking.

**Key Principles:**
- The warehouse layout is **fully dynamic and configurable** per organization (multi-tenant)
- Each organization defines its own floor plan, aisle orientation, rows, levels, and bins
- The 3D view is procedurally generated from configuration — no hardcoded layouts

---

## 1A. Dynamic Layout & Multi-Tenant Configuration

### 1A.1 Configurable Warehouse Floor Plan

The system shall support warehouses with **any layout shape** — not just rectangular grids. Each warehouse floor plan is configured by the end user during warehouse provisioning.

**Configuration approach (user-friendly):**

1. **2D Floor Plan Canvas** — The admin draws/configures the warehouse on a 2D grid canvas:
   - Set warehouse dimensions (width × depth in meters)
   - Place aisles (horizontal and/or vertical) by drawing lines on the grid
   - Aisles have orientation: `horizontal`, `vertical`, or `diagonal`
   - Define aisle width (determines forklift/pallet jack accessibility)
   - Mark dock doors (inbound/outbound) positions on the perimeter

2. **Rack/Shelf Placement** — After aisles are drawn:
   - Place rack units along each aisle (left side, right side, or both)
   - Each rack unit = one "bay" in the hierarchy
   - Define how many levels per bay (vertical shelves)
   - Define how many bins per level

3. **The system auto-generates** the full `warehouse_locations` hierarchy from this config:
   - Zones = groups of aisles (user defines zone boundaries)
   - Aisles = the drawn paths with orientation + coordinates
   - Bays = rack units placed along aisles
   - Levels = vertical shelves within each bay
   - Bins = individual storage positions within each level

### 1A.2 Aisle Orientation & Movement Paths

**FR-DL-01:** Aisles shall support multiple orientations:
- `horizontal` — runs left-to-right (parallel to X-axis)
- `vertical` — runs top-to-bottom (parallel to Y-axis)
- `cross_aisle` — connects horizontal/vertical aisles (intersection/transfer points)

**FR-DL-02:** The system shall model walkable paths (aisles) separately from storage locations (bays/bins). This distinction is critical for:
- Route optimization (workers travel through aisles, not through racks)
- Forklift path planning (wider aisles vs narrow picker aisles)
- Collision avoidance (two forklifts in same narrow aisle)

**FR-DL-03:** Each aisle shall store:
- Start coordinates (x1, y1)
- End coordinates (x2, y2)
- Width (meters)
- Orientation (horizontal/vertical/cross_aisle)
- Traffic direction: one-way or two-way
- Equipment type allowed: forklift, pallet jack, manual picker

### 1A.3 Multi-Tenant Dynamic Configuration

**FR-DL-04:** Each organization can have N warehouses, each with a completely different layout. Two warehouses in the same org may have:
- Different dimensions
- Different aisle orientations
- Different rack densities
- Different zone structures

**FR-DL-05:** Layout changes shall be non-destructive:
- Adding new aisles/bays/bins does not affect existing stock records
- Deactivating a location prevents new stock from being assigned but preserves existing records
- Reorganization (moving a bay to a different aisle) updates coordinates without losing bin stock

**FR-DL-06:** A "Layout Designer" UI shall allow:
- Drag-and-drop aisle placement on a 2D grid
- Snapping to grid for alignment
- Auto-generation of bays/levels/bins from templates (e.g., "Standard rack: 4 levels × 3 bins per level")
- Import from CSV/Excel for bulk rack definition
- Live preview toggle (2D top-down ↔ 3D perspective)

### 1A.4 Data Model for Dynamic Layout

The existing `warehouse_locations` table is extended with layout metadata:

```sql
-- New columns on warehouse_locations
ALTER TABLE warehouse_locations ADD COLUMN orientation VARCHAR(20);       -- 'horizontal', 'vertical', 'cross_aisle'
ALTER TABLE warehouse_locations ADD COLUMN start_x NUMERIC(10,2);        -- aisle start point X
ALTER TABLE warehouse_locations ADD COLUMN start_y NUMERIC(10,2);        -- aisle start point Y
ALTER TABLE warehouse_locations ADD COLUMN end_x NUMERIC(10,2);          -- aisle end point X
ALTER TABLE warehouse_locations ADD COLUMN end_y NUMERIC(10,2);          -- aisle end point Y
ALTER TABLE warehouse_locations ADD COLUMN aisle_width NUMERIC(5,2);     -- width in meters
ALTER TABLE warehouse_locations ADD COLUMN traffic_direction VARCHAR(10); -- 'one_way', 'two_way'
ALTER TABLE warehouse_locations ADD COLUMN equipment_type VARCHAR(50);    -- 'forklift', 'pallet_jack', 'manual'

-- New table for warehouse floor plan metadata
CREATE TABLE warehouse_floor_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    warehouse_id UUID NOT NULL REFERENCES warehouses_extended(id),
    width_meters NUMERIC(10,2) NOT NULL,      -- total warehouse width
    depth_meters NUMERIC(10,2) NOT NULL,      -- total warehouse depth
    height_meters NUMERIC(5,2) DEFAULT 10,    -- ceiling height
    grid_cell_size NUMERIC(5,2) DEFAULT 1.0,  -- grid snap size for the designer
    dock_doors JSONB DEFAULT '[]',            -- [{type: "inbound"|"outbound", x, y, width}]
    metadata JSONB DEFAULT '{}',              -- floor type, temperature zones, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(warehouse_id)
);
```

### 1A.5 User Input Flow for New Warehouse

```
Step 1: Basic Info
  → Name, code, address, type (warehouse/store/transit)

Step 2: Dimensions
  → Width × Depth (meters), ceiling height
  → Grid cell size (default 1m, can be 0.5m for precision)

Step 3: Dock Doors
  → Place inbound/outbound dock doors on the perimeter
  → Each door has a position (wall + offset) and width

Step 4: Aisles (2D Canvas)
  → Draw aisles on the grid (horizontal + vertical lines)
  → Set width, direction, equipment type for each
  → Mark cross-aisles (intersections)

Step 5: Zones
  → Group aisles into zones (drag a boundary box)
  → Name zones (e.g., "Fast Movers", "Bulk", "Cold Storage")

Step 6: Racks/Bays
  → For each aisle, define racks on left/right side
  → Set rack template: N levels × M bins per level
  → Set bin capacity (units or volume)
  → System auto-generates the full hierarchy

Step 7: Review & Confirm
  → 3D preview of the generated warehouse
  → Adjust coordinates if needed
  → Confirm → all warehouse_locations records created
```

---

## 2. Current System Capabilities

| Component | Status | Details |
|---|---|---|
| Location hierarchy | ✅ Built | Zone → Aisle → Bay → Level → Bin via `warehouse_locations` |
| Position data | ✅ Partial | `position_x`, `position_y` exist; no explicit Z-axis (inferred from level) |
| Allocation rules | ✅ Built | Exclusive/preferred per item group via `location_allocations` |
| Put-away bin assignment | ✅ Built | `PutAwayService._assign_bins()` respects allocations + capacity |
| FIFO picking | ✅ Built | `PickListService.resolve_bin_locations()` uses `created_at ASC` |
| Route optimization | ✅ Built | `RoutingOptimizer` sorts items by position for minimal travel |
| Worker task management | ✅ Built | `WorkerTask` model with state machine transitions |
| Capacity tracking | ✅ Built | `BinStockService` with capacity rollup via `CapacityService` |
| Multi-tenant location support | ✅ Built | `organization_id` on all records; each org has isolated warehouses |
| Aisle orientation (H/V) | ❌ Missing | No orientation, start/end coords, or traffic direction on aisles |
| Dynamic layout designer | ❌ Missing | No UI to draw/configure warehouse floor plan |
| Warehouse floor plan metadata | ❌ Missing | No dimensions, dock door positions, grid config |
| Bin-level reservation | ❌ Missing | No mechanism to prevent concurrent access to same bin |
| Expiry date tracking | ❌ Missing | Only `created_at` for FIFO; no expiry-based FEFO |
| Real-time bin status | ❌ Missing | No WebSocket or live occupancy broadcast |
| 3D visualization | ❌ Missing | Current UI is a tree view only |

---

## 3. Feature Requirements

### 3.1 3D Warehouse Visualization

**FR-3D-01:** The system shall render a 3D interactive view of the warehouse layout derived from the `warehouse_locations` hierarchy.

**FR-3D-02:** Bins shall be color-coded by fill percentage:
- 🟢 Green: 0–30% full (plenty of space)
- 🟡 Amber: 31–70% full (moderate)
- 🔴 Red: 71–100% full (near capacity)
- 🔵 Blue pulse: Currently locked/in-use by a worker
- ✨ Gold glow: System-suggested optimal location

**FR-3D-03:** The view shall support pan, rotate, zoom via mouse/touch gestures.

**FR-3D-04:** Clicking a bin shall display a detail panel showing:
- Bin code and full path
- Items stored (name, SKU, quantity, batch number, expiry date)
- Available capacity vs total capacity
- Current reservation status (locked by whom, time remaining)

**FR-3D-05:** The system shall show a highlighted navigation path from the worker's current position to the suggested bin.

### 3.2 Smart Location Suggestion Engine

**FR-SL-01 (Put-Away):** When a worker needs to put away items, the engine shall suggest optimal bin(s) scored by:

| Factor | Weight | Logic |
|---|---|---|
| Allocation match | ×100 | Exclusive allocation = mandatory; preferred = bonus |
| Available capacity | ×10 | Must have enough space; higher available = higher score |
| Proximity to dock | ×5 | Closer to receiving area = less travel time |
| Not locked | ×1000 (penalty) | Skip any bin currently reserved by another worker |
| Same item already here | ×20 | Consolidation bonus — same SKU in same area |
| Item group affinity | ×15 | Items from same group stored nearby = faster future picks |

**FR-SL-02 (Picking):** When a picker needs to pick items, the engine shall select bins using:

| Factor | Priority | Logic |
|---|---|---|
| FEFO (expiry) | 1st | If `expiry_date` exists, pick earliest expiry first |
| FIFO (arrival) | 2nd | If no expiry, use `created_at` (oldest stock first) |
| Not locked | Mandatory | Skip bins currently reserved by another picker |
| Route efficiency | 3rd | Minimize backtracking; prefer bins along the route |
| Quantity match | 4th | Prefer bin that satisfies the full requested qty in one stop |
| Batch consolidation | 5th | Prefer picking from fewer batches to reduce complexity |

**FR-SL-03:** Suggestions shall update in real-time. If Worker A reserves Bin X, Worker B's suggestions shall immediately exclude Bin X without requiring a page refresh.

### 3.3 Concurrent Worker Coordination

**FR-CW-01:** The system shall maintain a bin reservation table that prevents two workers from being directed to the same bin simultaneously.

**FR-CW-02:** Reservations shall have a configurable TTL (default: 5 minutes). If a worker does not complete or release within TTL, the reservation auto-expires.

**FR-CW-03:** A worker may explicitly release a reservation (e.g., pressing "Skip" to get an alternative suggestion).

**FR-CW-04:** Managers shall be able to force-release any reservation from the 3D overview.

**FR-CW-05:** The system shall broadcast lock/release events via WebSocket so all connected clients update their view instantly.

### 3.4 FEFO (First Expired, First Out) Support

**FR-FE-01:** `bin_stock_levels` shall track `expiry_date` (nullable DATE).

**FR-FE-02:** When picking, if `expiry_date` is populated, the system shall prioritize earliest expiry regardless of arrival time.

**FR-FE-03:** The 3D view shall highlight bins with items nearing expiry (within 30 days) with a warning indicator.

### 3.5 Worker Views

**FR-WV-01 (Personal View):** A worker sees:
- Their current task (put-away or pick)
- The suggested bin highlighted with a glow effect
- A navigation path showing the optimal route
- Estimated distance/time to the next location
- A "Skip" button to request an alternative (auto-releases current reservation)

**FR-WV-02 (Manager View):** A manager sees:
- All active workers as colored dots in the 3D view
- Real-time worker positions (updated when they scan at a bin)
- Bottleneck detection: bins with queued workers highlighted
- Heat map overlay: activity density per zone
- Throughput metrics per zone/aisle

---

## 4. Data Model Changes

### 4.1 New Table: `bin_reservations`

```sql
CREATE TABLE bin_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    bin_location_id UUID NOT NULL REFERENCES warehouse_locations(id),
    worker_id UUID NOT NULL,
    task_id UUID,                     -- reference to worker_tasks.id
    task_type VARCHAR(20),            -- 'put_away' or 'pick'
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,  -- reserved_at + TTL
    released_at TIMESTAMPTZ,          -- NULL while active
    CONSTRAINT uq_active_bin_reservation UNIQUE (bin_location_id)
        WHERE released_at IS NULL AND expires_at > NOW()
);

CREATE INDEX idx_bin_reservations_active
    ON bin_reservations (bin_location_id)
    WHERE released_at IS NULL;

CREATE INDEX idx_bin_reservations_worker
    ON bin_reservations (worker_id, organization_id)
    WHERE released_at IS NULL;
```

### 4.2 Column Addition: `bin_stock_levels.expiry_date`

```sql
ALTER TABLE bin_stock_levels
ADD COLUMN expiry_date DATE;

CREATE INDEX idx_bin_stock_expiry
    ON bin_stock_levels (expiry_date)
    WHERE expiry_date IS NOT NULL;
```

### 4.3 Column Addition: `warehouse_locations.position_z`

```sql
ALTER TABLE warehouse_locations
ADD COLUMN position_z NUMERIC(10,2) DEFAULT 0;
```

> **Note:** For existing data, `position_z` can be auto-populated from the level's ordinal position within its bay (Level 1 = z:0, Level 2 = z:1, etc.).

---

## 5. API Design

### 5.1 Layout API

```
GET /api/v1/wms-3d/layout?warehouse_id={id}
```

Returns the full 3D geometry tree for a warehouse:

```json
{
  "warehouse": {
    "id": "...",
    "name": "Transit Hub",
    "code": "TR-001"
  },
  "zones": [
    {
      "id": "...",
      "code": "ZN-IB",
      "name": "Inbound Zone",
      "position": { "x": 0, "y": 0, "z": 0 },
      "aisles": [
        {
          "id": "...",
          "code": "A01",
          "position": { "x": 0, "y": 10, "z": 0 },
          "bays": [
            {
              "id": "...",
              "code": "B01",
              "position": { "x": 0, "y": 10, "z": 0 },
              "levels": [
                {
                  "id": "...",
                  "code": "L01",
                  "position": { "x": 0, "y": 10, "z": 0 },
                  "bins": [
                    {
                      "id": "...",
                      "code": "BIN-001",
                      "full_path": "ZN-IB/A01/B01/L01/BIN-001",
                      "position": { "x": 0, "y": 10, "z": 0 },
                      "capacity": 200,
                      "available_capacity": 150,
                      "fill_percentage": 25,
                      "is_reserved": false,
                      "reserved_by_worker_id": null,
                      "items_count": 2,
                      "has_expiring_items": false
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### 5.2 Live Status API (Polling fallback)

```
GET /api/v1/wms-3d/status?warehouse_id={id}
```

Returns current bin statuses (fill %, reservation, worker positions):

```json
{
  "bins": [
    {
      "bin_id": "...",
      "fill_percentage": 75,
      "is_reserved": true,
      "reserved_by": { "worker_id": "...", "worker_name": "Jack Maa", "expires_in_seconds": 245 }
    }
  ],
  "workers": [
    {
      "worker_id": "...",
      "name": "Jack Maa",
      "current_bin_id": "...",
      "task_type": "pick",
      "last_scan_at": "2026-06-12T10:30:00Z"
    }
  ]
}
```

### 5.3 Suggest Location API

```
POST /api/v1/wms-3d/suggest
Body: {
  "task_type": "put_away" | "pick",
  "item_id": "...",
  "quantity": 50,
  "warehouse_id": "...",
  "worker_id": "...",
  "batch_number": "BATCH-LP-2026-01",     // optional
  "exclude_bin_ids": ["...", "..."]         // bins already skipped
}
```

Returns ranked suggestions:

```json
{
  "suggestions": [
    {
      "rank": 1,
      "bin_id": "...",
      "bin_code": "ZN-IB/A01/B01/L01/BIN-001",
      "position": { "x": 0, "y": 10, "z": 0 },
      "score": 850,
      "reasons": ["Preferred allocation match", "60% capacity available", "Nearest to dock"],
      "available_capacity": 150,
      "distance_from_worker": 12.5,
      "estimated_time_seconds": 45
    },
    {
      "rank": 2,
      "bin_id": "...",
      "bin_code": "ZN-IB/A01/B01/L02/BIN-003",
      "position": { "x": 0, "y": 11, "z": 1 },
      "score": 720,
      "reasons": ["Preferred allocation match", "90% capacity available"],
      "available_capacity": 180,
      "distance_from_worker": 18.2,
      "estimated_time_seconds": 65
    }
  ],
  "strategy_used": "put_away_scored",
  "total_candidates_evaluated": 12,
  "excluded_bins": 3
}
```

### 5.4 Reserve Bin API

```
POST /api/v1/wms-3d/reserve
Body: {
  "bin_id": "...",
  "worker_id": "...",
  "task_id": "...",
  "task_type": "put_away",
  "ttl_seconds": 300
}
```

### 5.5 Release Bin API

```
POST /api/v1/wms-3d/release
Body: {
  "bin_id": "...",
  "worker_id": "..."
}
```

### 5.6 WebSocket: Real-Time Updates

```
WS /api/v1/wms-3d/ws?warehouse_id={id}&token={jwt}
```

Events pushed to connected clients:

```json
// Bin reserved
{ "event": "bin_reserved", "bin_id": "...", "worker_id": "...", "worker_name": "Jack", "expires_at": "..." }

// Bin released
{ "event": "bin_released", "bin_id": "..." }

// Worker position update
{ "event": "worker_moved", "worker_id": "...", "bin_id": "...", "task_type": "pick" }

// Stock changed (put-away completed or pick completed)
{ "event": "stock_changed", "bin_id": "...", "fill_percentage": 45 }

// Suggestion invalidated (another worker took the suggested bin)
{ "event": "suggestion_invalidated", "bin_id": "...", "affected_worker_ids": ["..."] }
```

---

## 6. Frontend Architecture

### 6.1 Technology Stack

| Library | Purpose | Version |
|---|---|---|
| `@react-three/fiber` | React renderer for Three.js | ^8.x |
| `@react-three/drei` | Helpers (OrbitControls, Text, etc.) | ^9.x |
| `three` | Core 3D engine | ^0.160 |
| Native WebSocket | Real-time bin status updates | Built-in |

### 6.2 Component Hierarchy

```
<Warehouse3DView warehouseId={id} workerId={id} taskType="put_away">
  <Canvas>
    <OrbitControls />          // Pan, rotate, zoom
    <AmbientLight />
    <DirectionalLight />
    
    <WarehouseFloor />         // Grid floor with zone outlines
    
    {zones.map(zone => (
      <ZoneGroup key={zone.id}>
        {zone.aisles.map(aisle => (
          <AisleGroup key={aisle.id}>
            {aisle.bays.map(bay => (
              <BayShelf key={bay.id}>
                {bay.levels.map(level => (
                  <LevelRow key={level.id}>
                    {level.bins.map(bin => (
                      <BinCube
                        key={bin.id}
                        position={[bin.x, bin.z, bin.y]}
                        fillPercentage={bin.fill_percentage}
                        isReserved={bin.is_reserved}
                        isSuggested={bin.id === suggestedBinId}
                        onClick={() => showBinDetail(bin)}
                      />
                    ))}
                  </LevelRow>
                ))}
              </BayShelf>
            ))}
          </AisleGroup>
        ))}
      </ZoneGroup>
    ))}
    
    {workers.map(w => (
      <WorkerDot key={w.id} position={w.position} name={w.name} />
    ))}
    
    {suggestedPath && <NavigationPath points={suggestedPath} />}
  </Canvas>
  
  <SuggestionPanel suggestions={suggestions} onAccept={reserve} onSkip={skip} />
  <BinDetailPanel bin={selectedBin} />
</Warehouse3DView>
```

### 6.3 Visual Design

**Bin cube appearance:**
- Size: proportional to capacity (bigger bins = larger cubes)
- Height fill: partially filled cubes show stock level as a "water fill" effect inside
- Suggested bin: gold wireframe outline + subtle pulsing animation
- Reserved bin: blue semi-transparent overlay + worker name label floating above

**Navigation path:**
- Animated dashed line from worker position to suggested bin
- Multiple suggested bins show numbered waypoints (1 → 2 → 3)
- Line color: green (optimal), yellow (alternative), red (blocked/skipped)

---

## 7. Scoring Algorithm Detail

### 7.1 Put-Away Scoring

```python
def score_put_away_bin(bin, item, worker_position, dock_position):
    score = 0
    
    # 1. Allocation match (mandatory for exclusive)
    if bin.has_exclusive_allocation(item.item_group_id):
        score += 100
    elif bin.has_preferred_allocation(item.item_group_id):
        score += 50
    elif bin.has_any_exclusive_allocation():
        return -1  # SKIP — exclusively allocated to another group
    
    # 2. Capacity available
    if bin.available_capacity < quantity_needed:
        return -1  # SKIP — insufficient capacity
    capacity_ratio = bin.available_capacity / bin.total_capacity
    score += capacity_ratio * 10
    
    # 3. Proximity to dock (shorter = better for inbound put-away)
    distance_to_dock = euclidean(bin.position, dock_position)
    max_distance = warehouse.max_dimension
    proximity_score = (1 - distance_to_dock / max_distance) * 5
    score += proximity_score
    
    # 4. Reservation check
    if bin.is_reserved and bin.reserved_by != worker_id:
        return -1  # SKIP — reserved by another worker
    
    # 5. Same item consolidation
    if bin.contains_item(item.id):
        score += 20
    elif bin.contains_item_group(item.item_group_id):
        score += 15
    
    return score
```

### 7.2 Pick Scoring

```python
def score_pick_bin(bin_stock, item_id, quantity_needed, worker_position, reserved_bins):
    score = 0
    
    # 1. Reservation check (mandatory exclude)
    if bin_stock.bin_id in reserved_bins:
        return -1  # SKIP
    
    # 2. FEFO / FIFO
    if bin_stock.expiry_date:
        days_until_expiry = (bin_stock.expiry_date - today).days
        score += (365 - days_until_expiry) * 100  # Earlier expiry = higher score
    else:
        age_days = (today - bin_stock.created_at.date()).days
        score += age_days * 80  # Older stock = higher score (FIFO)
    
    # 3. Quantity match (prefer bin that satisfies full request)
    if bin_stock.quantity_on_hand >= quantity_needed:
        score += 20  # No split needed
    else:
        score += 5   # Partial — will need another bin too
    
    # 4. Route efficiency
    distance = euclidean(bin_stock.position, worker_position)
    max_distance = warehouse.max_dimension
    route_score = (1 - distance / max_distance) * 30
    score += route_score
    
    return score
```

---

## 8. Concurrency Model

### 8.1 Bin Reservation Lifecycle

```
                 ┌─────────────┐
                 │  Available   │
                 └──────┬──────┘
                        │ POST /reserve
                        ▼
                 ┌─────────────┐
       TTL       │  Reserved    │──────── TTL expires ──► Available
       (5min)    └──────┬──────┘
                        │
              ┌─────────┼─────────┐
              │                   │
     Worker completes      Worker skips/releases
              │                   │
              ▼                   ▼
     ┌──────────────┐    ┌─────────────┐
     │  Completed   │    │  Available   │
     └──────────────┘    └─────────────┘
```

### 8.2 Race Condition Handling

1. **Suggest → Reserve gap:** Between receiving a suggestion and clicking "Accept", another worker might reserve the same bin. The `/reserve` endpoint uses `SELECT ... FOR UPDATE` to guarantee atomicity.
2. **Stale suggestions:** WebSocket pushes `suggestion_invalidated` event when a bin gets reserved by someone else. Frontend immediately refreshes suggestions.
3. **TTL expiry:** Redis (or PostgreSQL advisory locks) automatically expire reservations. A background task cleans up expired rows every 60 seconds.

---

## 9. Integration with Existing Flows

### 9.1 Inbound (Put-Away) Integration

Current flow:
```
Scan → End Session → Approve Slip → Generate Put-Away List → Worker Task
```

Enhanced flow:
```
Scan → End Session → Approve Slip → Generate Put-Away List → Worker Task
                                                                    │
                                              Worker opens 3D view ◄┘
                                                        │
                                              System suggests optimal bin(s)
                                                        │
                                              Worker accepts → Bin reserved
                                                        │
                                              Worker walks to bin → Scans bin QR
                                                        │
                                              complete_item() → Stock updated → Lock released
                                                        │
                                              Next item → New suggestion (excludes completed bins)
```

### 9.2 Outbound (Picking) Integration

Current flow:
```
Pick List Created → resolve_bin_locations() → Worker Task → Pick Scan → Dispatch
```

Enhanced flow:
```
Pick List Created → resolve_bin_locations() (now respects reservations)
                          │
            Worker opens 3D view with pick path highlighted
                          │
            System reserves first bin → Worker walks there
                          │
            Worker scans item → Stock decremented → Lock released
                          │
            Next item's bin auto-reserved → Path updates
                          │
            All items picked → Complete → Gate verification → Dispatch
```

---

## 10. Performance Considerations

| Concern | Solution |
|---|---|
| Large warehouses (10,000+ bins) | LOD (Level of Detail) — distant bins rendered as flat sprites, nearby as full 3D |
| WebSocket scaling (100+ concurrent workers) | Fan-out via Redis Pub/Sub — one message per bin change, clients filter by warehouse |
| Suggestion computation time | Pre-compute top-10 for each pending task, cache in Redis (invalidate on stock/lock change) |
| Layout API payload size | Cache full layout per warehouse (invalidate on location changes only) |
| Mobile/tablet performance | Offer a 2D overhead fallback for low-power devices |

---

## 11. Implementation Phases

### Phase 0: Dynamic Layout Configuration (Backend + Frontend) — ~4-5 days
- [ ] Alembic migration: `warehouse_floor_plans` table
- [ ] Alembic migration: add `orientation`, `start_x`, `start_y`, `end_x`, `end_y`, `aisle_width`, `traffic_direction`, `equipment_type` to `warehouse_locations`
- [ ] API: `POST/GET/PUT /api/v1/warehouses/{id}/floor-plan` — floor plan CRUD
- [ ] API: `POST /api/v1/warehouses/{id}/generate-layout` — auto-generate location hierarchy from floor plan + rack templates
- [ ] Frontend: 2D Layout Designer canvas (draw aisles, place racks, define zones)
- [ ] Frontend: Rack template configurator (levels × bins per level, capacity)
- [ ] Frontend: Dock door placement on warehouse perimeter
- [ ] Validation: ensure generated paths are connected (no isolated aisles)
- [ ] Import: CSV/Excel bulk rack definition for existing warehouses

### Phase 1: Foundation (Backend) — ~3-4 days
- [ ] Alembic migration: `bin_reservations` table
- [ ] Alembic migration: `expiry_date` on `bin_stock_levels`
- [ ] Alembic migration: `position_z` on `warehouse_locations`
- [ ] `BinReservationService` — reserve, release, check, cleanup expired
- [ ] Update `PutAwayService._assign_bins()` to exclude reserved bins
- [ ] Update `PickListService.resolve_bin_locations()` to exclude reserved bins
- [ ] API endpoints: `/wms-3d/layout`, `/wms-3d/suggest`, `/wms-3d/reserve`, `/wms-3d/release`
- [ ] Seed `position_z` from level hierarchy
- [ ] Update route optimizer to use aisle orientation + start/end coords for path planning

### Phase 2: 3D Visualization (Frontend) — ~5-7 days
- [ ] Install React Three Fiber + drei
- [ ] `<Warehouse3DView>` component with procedural geometry from layout API
- [ ] Render aisles as floor paths (horizontal/vertical/cross)
- [ ] Render racks as shelf structures along aisles
- [ ] Bin cubes with fill-percentage coloring
- [ ] Click interaction → bin detail panel
- [ ] Suggested bin glow animation
- [ ] Navigation path rendering following aisle paths (not straight lines through racks)
- [ ] Responsive layout (fits in the WMS Inbound/Outbound tab area)
- [ ] 2D top-down toggle for quick overview

### Phase 3: Real-Time (WebSocket) — ~2-3 days
- [ ] FastAPI WebSocket endpoint `/wms-3d/ws`
- [ ] Redis Pub/Sub for cross-worker broadcast
- [ ] Frontend WebSocket hook with reconnection
- [ ] Live bin color updates on reserve/release/stock change
- [ ] Worker position dots (updated on scan events)

### Phase 4: Polish & Advanced — ~2-3 days
- [ ] FEFO integration in pick scoring
- [ ] Wave picking (batch pick lists for same zone)
- [ ] "Skip" button with instant re-suggestion
- [ ] Manager heat map overlay
- [ ] 2D fallback for mobile devices
- [ ] Performance: LOD for large warehouses
- [ ] Aisle traffic direction enforcement in route planning
- [ ] Forklift vs manual picker path differentiation

---

## 12. Database ERD (Changes Only)

```
┌────────────────────────┐
│   bin_reservations     │  NEW TABLE
├────────────────────────┤
│ id                     │
│ organization_id        │
│ bin_location_id  ──────┼──► warehouse_locations.id
│ worker_id        ──────┼──► wms_workers.id
│ task_id          ──────┼──► worker_tasks.id (nullable)
│ task_type              │
│ reserved_at            │
│ expires_at             │
│ released_at            │
└────────────────────────┘

┌────────────────────────┐
│   bin_stock_levels     │  MODIFIED
├────────────────────────┤
│ + expiry_date DATE     │  NEW COLUMN (nullable)
└────────────────────────┘

┌────────────────────────┐
│   warehouse_locations  │  MODIFIED
├────────────────────────┤
│ + position_z NUMERIC   │  NEW COLUMN (default 0)
└────────────────────────┘
```

---

## 13. Key Scenarios & Edge Cases

| Scenario | Handling |
|---|---|
| Worker's phone dies mid-task | TTL auto-releases the bin after 5 min |
| Two workers request same bin at exact same moment | PostgreSQL `SELECT FOR UPDATE` ensures only one succeeds; the other gets next-best |
| All bins for an item group are full | Suggest falls back to unallocated bins; if ALL bins full, show "No available location — contact manager" |
| Item has no item group (no allocation rules) | Falls directly to unallocated bin pool, scored by capacity + proximity |
| Worker wants to override suggestion | Allow "manual override" — worker can tap any bin in the 3D view to select it, system reserves that one instead |
| Expired reservation with stock partially put away | Reservation tracks `task_id` — if task still in_progress, auto-extend TTL rather than releasing |
| Network disconnection during WebSocket | Frontend reconnects with exponential backoff; on reconnect, fetches full status to sync |
| Manager force-releases a bin while worker is walking there | Worker's app shows alert: "Your assigned bin was released. Tap for a new suggestion." |

---

## 14. Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Avg pick time per item | -30% vs manual selection | `completed_at - started_at` on worker_tasks |
| Bin contention incidents | 0 per shift | Count of "suggestion_invalidated" events where worker was already walking |
| FEFO compliance | 100% | Audit: picked items should always be earliest expiry from available stock |
| Put-away time per pallet | -25% vs manual | `completed_at - assigned_at` on put-away worker_tasks |
| 3D view load time | <2 seconds for 500 bins | Frontend performance monitoring |
| WebSocket latency | <200ms for lock events | Server-side event timestamp vs client receipt |

---

## 15. Open Questions / Decisions Needed

1. **TTL duration:** 5 minutes default — should this be configurable per warehouse or per role?
2. **Mobile vs Desktop:** Should the 3D view be available on mobile scanners, or only on tablets/desktops? (Mobile might need the 2D overhead view)
3. **Wave picking:** Should we batch multiple pick lists for the same zone into a single worker task? (Reduces travel but increases task complexity)
4. **Audio/haptic feedback:** Should the worker's device beep/vibrate when approaching the suggested bin? (Requires native app or PWA)
5. **Historical analytics:** Should we track "suggestion accuracy" (how often workers accept vs skip the top suggestion)?

---

## 16. File References (Existing Code to Modify)

**Backend (core-service):**
- `app/services/put_away_service.py` — `_assign_bins()` needs reservation check
- `app/services/pick_list_service.py` — `resolve_bin_locations()` needs reservation check
- `app/services/bin_stock_service.py` — add_stock/remove_stock should release reservations
- `app/models/bin_stock_level.py` — add `expiry_date` column
- `app/models/warehouse_location.py` — add `position_z` column
- `app/api/v1/endpoints/` — new `wms_3d.py` router

**Frontend (inventory app):**
- `apps/inventory/src/app/components/wms/` — new `Warehouse3DView.tsx`
- `apps/inventory/src/app/utility/api/wms.ts` — new API methods
- `apps/inventory/src/app/types/wms.types.ts` — new type definitions
- `apps/inventory/src/app/hooks/` — new `useWarehouse3D.ts`, `useWebSocket.ts`

---

*Document created: June 12, 2026*  
*Author: Kiro (AI) + User collaboration*  
*Next step: User review → Phase 1 implementation*
