# Design Document: Warehouse QR-Based Inbound/Outbound with Bin Management

## Overview

This document describes the unified architecture for a warehouse management system combining:

- Physical layout hierarchy (Zone → Aisle → Bay → Level → Bin) with capacity rollup
- Bin-level stock tracking with real-time capacity updates
- QR code-driven inbound receiving (scan → receiving slip → put-away)
- SAP invoice-triggered outbound (pick list → QR fulfillment → gate verification → dispatch)
- Optimized routing for put-away and pick operations
- Worker task assignment with QR scan-based time tracking
- Location allocation for item groups (fast/slow movers)
- Level-based filtering and views

### Key Design Decisions

1. **Self-contained QR payloads** — QR codes embed SKU, quantity, and batch directly. No server lookup needed to decode, enabling offline scanning.
2. **Hierarchical location model** — Single `warehouse_locations` table with `location_type` enum and `parent_location_id` for the full Zone → Aisle → Bay → Level → Bin tree.
3. **Capacity rollup on write** — Capacity is recalculated on every bin change (add/remove/deactivate) and propagated up the tree within the same transaction.
4. **Scan sessions as first-class entities** — Group scans into sessions (inbound or gate) for atomic operations and duplicate detection.
5. **Receiving slip review workflow** — Slips go through PENDING_REVIEW → PENDING_PUTAWAY to allow managers to approve before put-away begins.
6. **SAP invoice triggers pick lists** — Outbound flow starts when a sales invoice webhook arrives from SAP, creating a pick list automatically with FIFO bin resolution.
7. **Gate verification as a separate step** — Security personnel verify dispatched items independently from the picking process.
8. **Nearest-neighbor routing** — Simple heuristic with aisle grouping for both put-away and pick operations.
9. **Location allocations** — Exclusive and preferred allocation types control which items go where during put-away.
10. **Optimistic locking** — Concurrent stock updates use version columns to detect conflicts and retry.

## High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        WAREHOUSE SETUP                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Manager defines:  Warehouse → Zone → Aisle → Bay → Level → Bin                 │
│  Sets bin capacities → Capacity rolls up to all ancestors                        │
│  Allocates locations to item groups (exclusive/preferred)                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INBOUND FLOW                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Dock Worker              System                      Warehouse Manager           │
│  ───────────              ──────                      ─────────────────           │
│  Start Session ──────────► Create Scan Session (OPEN)                             │
│  Scan Box QR ────────────► Decode Payload, Reject Duplicates                      │
│  Scan Box QR ────────────► Aggregate by SKU/Batch                                 │
│  ...                                                                              │
│  End Session ────────────► Close Session                                          │
│                            Generate Receiving Slip ────► Review Slip               │
│                            (PENDING_REVIEW)              Approve / Reject          │
│                                                          │                        │
│                            ◄─────────────────────────────┘                        │
│                            Generate Put-Away List (grouped by zone/aisle)          │
│                            Assign Worker Task                                      │
│  Scan at Bin ────────────► Update Bin Stock + Capacity Rollup                     │
│  (start/finish QR) ─────► Track Time per Location                                 │
│                            Mark Item COMPLETED                                     │
│                            (all done → PUTAWAY_COMPLETE)                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OUTBOUND FLOW                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SAP System               System                      Picker / Gate Security      │
│  ──────────               ──────                      ──────────────────────      │
│  Sales Invoice ──────────► Create Pick List (OPEN)                                │
│                            Resolve Bins (FIFO)                                    │
│                            Optimize Route                                          │
│                            Assign Worker Task                                      │
│                                                        Scan Box QR (pick)         │
│                            ◄───────────────────────────Match to Pick List          │
│                            Increment picked_qty                                   │
│                            Decrement Bin Stock                                     │
│                            (first scan → IN_PROGRESS)                             │
│                            (all picked → allow COMPLETE)                           │
│                                                                                  │
│                                                        Gate: Start Session         │
│                                                        Scan Box QR (gate)         │
│                            ◄───────────────────────────Validate vs Pick List       │
│                            (all verified → VERIFIED)                               │
│                            Create Dispatch Record                                  │
│                            Decrement Warehouse Stock                               │
│                            Generate Dispatch Number                                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## User Journeys

### Journey 1: Warehouse Manager — Layout Setup

1. Manager opens warehouse management dashboard
2. Selects a warehouse and clicks "Manage Layout"
3. Creates zones (e.g., Receiving, Bulk Storage, Cold Storage)
4. Within each zone, creates aisles (A01, A02, ...)
5. Within each aisle, creates bays (B01, B02, ...)
6. Within each bay, creates levels (L01, L02, ...)
7. Within each level, creates bins with capacity (B01, B02, ...)
8. System auto-generates location codes (e.g., Z01-A03-B02-L04-B01)
9. System rolls up capacity to all ancestor levels
10. Manager allocates specific bays/levels to item groups (fast movers near dock)

### Journey 2: Dock Worker — Inbound Receiving

1. Worker arrives at dock, opens mobile app
2. Taps "Start Inbound Session" — selects warehouse and dock location
3. System creates session (status: OPEN)
4. Worker scans each box QR code as it's unloaded from the truck
5. App shows running count: boxes scanned, quantities per SKU
6. If a box is scanned twice, app shows warning "Already scanned"
7. Worker taps "End Session" when unloading is complete
8. System generates receiving slip (status: PENDING_REVIEW)
9. Worker sees summary: total boxes, items by SKU/batch

### Journey 3: Warehouse Manager — Review & Approve Receiving Slip

1. Manager sees new receiving slip in dashboard
2. Opens slip — reviews item breakdown (SKU, qty, batch)
3. If discrepancy found: flags line items as SHORT or DAMAGED, adds notes
4. Approves slip → status transitions to PENDING_PUTAWAY
5. System automatically generates put-away list (grouped by zone/aisle, respecting allocations)
6. Put-away list assigned to available worker

### Journey 4: Worker — Put-Away with Time Tracking

1. Worker receives put-away task on mobile app
2. App shows ordered list of bins to visit (optimized route)
3. Worker picks up items, walks to first bin
4. Scans START QR at bin location → system records start time
5. Places items in bin
6. Scans FINISH QR at bin location → system records end time, calculates elapsed
7. System updates bin stock, marks item as COMPLETED
8. Capacity rolls up to all ancestors
9. Repeats for each item in the list
10. When all items placed, receiving slip → PUTAWAY_COMPLETE

### Journey 5: System — SAP Invoice Triggers Pick List

1. SAP sends sales invoice via webhook
2. System creates pick list (status: OPEN) linked to invoice
3. System resolves each line item to bin locations using FIFO (oldest stock first)
4. System optimizes route for picker (nearest-neighbor with aisle grouping)
5. Pick list assigned to worker as a task

### Journey 6: Picker — Outbound Picking

1. Picker receives pick task on mobile app
2. App shows ordered list of bins to visit
3. Picker walks to bin, picks items
4. Scans START QR at location → time tracking begins
5. Scans box QR → system matches to pick list item
6. If wrong item: app shows error "Not on pick list"
7. If over-picking: app shows error "Exceeds required quantity"
8. Scans FINISH QR → time recorded
9. First scan transitions pick list to IN_PROGRESS
10. When all items picked, picker marks list as COMPLETED

### Journey 7: Gate Security — Verification & Dispatch

1. Security person starts gate verification session
2. Enters vehicle number, driver details, selects completed pick list
3. Scans each box being loaded onto vehicle
4. System validates each scan against the pick list
5. If unauthorized item: system flags and alerts
6. App shows progress: X of Y items verified
7. When all items scanned: session → VERIFIED
8. System creates dispatch record, decrements warehouse stock
9. Generates unique dispatch number

### Journey 8: Supervisor — Worker Time Tracking Review

1. Supervisor opens worker productivity dashboard
2. Selects date range and worker
3. Views time tracking summaries: time per task, time per location
4. Identifies bottlenecks (slow locations, long travel times)
5. Can drill down to individual scan events for a task

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer (FastAPI Routers)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  LayoutEndpoints  │ CapacityEndpoints │ InboundEndpoints │ OutboundEndpoints │
│  StockEndpoints   │ TaskEndpoints     │ ScanEndpoints    │ AllocationEndpts  │
└────────┬──────────┴────────┬──────────┴────────┬─────────┴────────┬─────────┘
         │                   │                   │                   │
┌────────▼──────────────────▼──────────────────▼──────────────────▼─────────┐
│                            Service Layer                                    │
├────────────────────────────────────────────────────────────────────────────┤
│  LayoutService      │ CapacityService    │ BinStockService                  │
│  InboundService     │ PickListService    │ GateVerificationService          │
│  OutboundService    │ PutAwayService     │ RoutingOptimizer                 │
│  TaskService        │ QRScanService      │ AllocationService                │
│  ScanEventService   │                    │                                  │
└────────┬──────────────────┬──────────────────┬──────────────────────────────┘
         │                   │                   │
┌────────▼──────────────────▼──────────────────▼──────────────────────────────┐
│                          Repository Layer                                    │
├────────────────────────────────────────────────────────────────────────────┤
│  LocationRepository    │ BinStockRepository    │ ScanSessionRepository       │
│  ReceivingSlipRepo     │ PickListRepository    │ GateSessionRepository       │
│  DispatchRepository    │ WorkerTaskRepository  │ LocationScanRepository      │
│  AllocationRepository  │ ScanEventRepository   │                             │
└────────┬──────────────────┬──────────────────┬──────────────────────────────┘
         │                   │                   │
┌────────▼──────────────────▼──────────────────▼──────────────────────────────┐
│                        PostgreSQL (SQLAlchemy + Alembic)                      │
├────────────────────────────────────────────────────────────────────────────┤
│  warehouse_locations     │ bin_stock_levels      │ scan_sessions              │
│  scan_session_items      │ receiving_slips       │ receiving_slip_items       │
│  pick_lists              │ pick_list_items       │ gate_verification_sessions │
│  gate_verification_items │ dispatch_records      │ worker_tasks               │
│  location_scans          │ put_away_lists        │ put_away_list_items        │
│  location_allocations    │ qr_scan_events        │ stock_levels               │
└────────────────────────────────────────────────────────────────────────────┘
```

### Integration with Existing Systems

- **warehouses_extended** — Existing warehouse table. Locations reference it via `warehouse_id`.
- **stock_levels** — Existing warehouse-level stock. Kept in sync with bin-level changes.
- **qr_scan_events** — Existing audit table. All scan events stored here with context in `extra_data`.
- **items** — Existing item master. Referenced by bin_stock_levels and pick list items.
- **put_away_lists / put_away_list_items** — Existing tables extended with bin location assignments.
- **pick_lists / pick_list_items** — Existing tables extended with invoice reference and picked_qty.

## Components and Interfaces

### LayoutService

Manages the warehouse location hierarchy (Zone → Aisle → Bay → Level → Bin).

```python
class LayoutService:
    def create_location(self, data: CreateLocationRequest, org_id: UUID) -> WarehouseLocation
    def update_location(self, location_id: UUID, data: UpdateLocationRequest, org_id: UUID) -> WarehouseLocation
    def deactivate_location(self, location_id: UUID, org_id: UUID) -> WarehouseLocation
    def get_tree(self, warehouse_id: UUID, org_id: UUID) -> LocationTree
    def list_locations(self, filters: LocationFilters, org_id: UUID) -> PaginatedLocations
    def get_location_summary(self, location_id: UUID, org_id: UUID) -> LocationSummary
    def search_locations(self, warehouse_id: UUID, query: str, org_id: UUID) -> List[WarehouseLocation]
    def generate_location_code(self, parent: WarehouseLocation, code: str) -> str
```

**Hierarchy Enforcement:**

```python
VALID_PARENT_TYPES = {
    "zone": "warehouse",
    "aisle": "zone",
    "bay": "aisle",
    "level": "bay",
    "bin": "level",
}

def validate_parent(self, location_type: str, parent: WarehouseLocation):
    expected_parent = VALID_PARENT_TYPES[location_type]
    if parent.location_type != expected_parent:
        raise ValidationError(f"A {location_type} must have a {expected_parent} as parent")
```

### CapacityService

Computes and maintains capacity rollups through the location hierarchy.

```python
class CapacityService:
    def recalculate_ancestors(self, location_id: UUID, db: Session) -> None
    def compute_available_capacity(self, location_id: UUID, org_id: UUID) -> Decimal
    def get_capacity_summary(self, location_id: UUID, org_id: UUID) -> CapacitySummary
```

**Rollup Algorithm:**

```python
def recalculate_ancestors(self, location_id: UUID, db: Session):
    """Walk up the tree from the changed location to the warehouse root,
    recalculating total_capacity = sum(children.total_capacity) at each level."""
    location = db.get(WarehouseLocation, location_id)
    current = location.parent
    while current is not None:
        children_capacity = db.query(func.sum(WarehouseLocation.capacity)).filter(
            WarehouseLocation.parent_location_id == current.id,
            WarehouseLocation.is_active == True
        ).scalar() or 0
        current.total_capacity = children_capacity
        current.available_capacity = current.total_capacity - self._used_capacity(current.id, db)
        current = current.parent
```

### BinStockService

Tracks stock at the bin level and maintains consistency with warehouse-level stock.

```python
class BinStockService:
    def add_stock(self, bin_id: UUID, item_id: UUID, quantity: Decimal, org_id: UUID, db: Session) -> BinStockLevel
    def remove_stock(self, bin_id: UUID, item_id: UUID, quantity: Decimal, org_id: UUID, db: Session) -> BinStockLevel
    def get_bins_for_item(self, item_id: UUID, org_id: UUID) -> List[BinStockInfo]
    def get_bin_stock(self, bin_id: UUID, org_id: UUID) -> List[BinStockLevel]
```

### InboundService

Manages the inbound receiving workflow: scan sessions, receiving slips, and review.

```python
class InboundService:
    def start_session(self, data: StartSessionRequest, worker_id: UUID, org_id: UUID) -> ScanSession
    def record_scan(self, session_id: UUID, qr_payload: str, worker_id: UUID, org_id: UUID) -> ScanResult
    def end_session(self, session_id: UUID, worker_id: UUID, org_id: UUID) -> ReceivingSlip
    def get_session_summary(self, session_id: UUID, org_id: UUID) -> SessionSummary
    def approve_slip(self, slip_id: UUID, org_id: UUID) -> ReceivingSlip
    def reject_slip(self, slip_id: UUID, reason: str, org_id: UUID) -> ReceivingSlip
    def flag_line_item(self, slip_id: UUID, item_id: UUID, flag: str, notes: str, org_id: UUID) -> ReceivingSlipItem
    def decode_qr_payload(self, qr_data: str) -> QRPayload
```

**QR Payload Format (JSON):**

```json
{
  "id": "unique-qr-identifier",
  "sku": "ITEM-001",
  "qty": 50,
  "batch": "BATCH-2025-01"
}
```

### PickListService

Manages SAP-triggered pick list creation and QR-based fulfillment.

```python
class PickListService:
    def create_from_invoice(self, invoice_data: SAPInvoicePayload, org_id: UUID) -> PickList
    def resolve_bin_locations(self, pick_list_id: UUID, org_id: UUID) -> PickList
    def record_pick_scan(self, pick_list_id: UUID, qr_payload: str, worker_id: UUID, org_id: UUID) -> PickScanResult
    def complete_pick_list(self, pick_list_id: UUID, org_id: UUID) -> PickList
    def cancel_pick_list(self, pick_list_id: UUID, org_id: UUID) -> PickList
    def get_pick_list_progress(self, pick_list_id: UUID, org_id: UUID) -> PickListProgress
    def list_pick_lists(self, filters: PickListFilters, org_id: UUID) -> PaginatedPickLists
```

**FIFO Bin Resolution:**

```python
def resolve_bin_locations(self, pick_list_id: UUID, org_id: UUID):
    """For each pick list item:
    1. Query bin_stock_levels WHERE item_id = X AND quantity_on_hand > 0
    2. ORDER BY created_at ASC (oldest stock first = FIFO)
    3. Allocate from oldest bins, splitting across bins if needed
    4. Pass resolved locations to RoutingOptimizer for sort ordering
    """
```

### GateVerificationService

Manages gate verification sessions and dispatch authorization.

```python
class GateVerificationService:
    def start_session(self, data: GateSessionRequest, worker_id: UUID, org_id: UUID) -> GateVerificationSession
    def record_gate_scan(self, session_id: UUID, qr_payload: str, worker_id: UUID, org_id: UUID) -> GateScanResult
    def get_session_progress(self, session_id: UUID, org_id: UUID) -> GateSessionProgress
    def verify_session(self, session_id: UUID, org_id: UUID) -> GateVerificationSession
```

### OutboundService

Manages dispatch records and stock deduction on verified gate sessions.

```python
class OutboundService:
    def create_dispatch(self, gate_session_id: UUID, org_id: UUID) -> DispatchRecord
    def list_dispatches(self, filters: DispatchFilters, org_id: UUID) -> PaginatedDispatches
    def get_dispatch(self, dispatch_id: UUID, org_id: UUID) -> DispatchRecord
```

### PutAwayService

Generates optimized put-away lists from receiving slips, respecting allocations and capacity.

```python
class PutAwayService:
    def generate_from_slip(self, slip_id: UUID, org_id: UUID) -> PutAwayList
    def complete_item(self, put_away_item_id: UUID, worker_id: UUID, org_id: UUID) -> PutAwayListItem
    def skip_item(self, put_away_item_id: UUID, reason: str, org_id: UUID) -> PutAwayListItem
```

**Bin Assignment Logic:**

```python
def assign_bins(self, item_id: UUID, item_group_id: UUID, quantity: Decimal, warehouse_id: UUID):
    """
    1. Check location_allocations for exclusive/preferred allocations for item_group_id
    2. For exclusive allocations: only use those bins
    3. For preferred allocations: try those bins first, fall back to unallocated
    4. Filter bins by: is_active=True, available_capacity >= quantity
    5. Split across bins if single bin insufficient
    6. Pass to RoutingOptimizer for sort ordering
    """
```

### RoutingOptimizer

Calculates optimal traversal order for bin visits.

```python
class RoutingOptimizer:
    def optimize(self, locations: List[BinLocation], origin: Tuple[float, float] = (0, 0)) -> List[BinLocation]:
        """
        Nearest-neighbor heuristic with aisle grouping:
        1. Group locations by aisle
        2. Sort aisle groups by distance from origin
        3. Within each aisle, sort by position (nearest-neighbor)
        4. Assign sequential sort_order integers
        """
```

### TaskService

Manages worker task assignments for put-away and pick operations.

```python
class TaskService:
    def create_task(self, task_type: str, worker_id: UUID, reference_id: UUID, org_id: UUID) -> WorkerTask
    def start_task(self, task_id: UUID, org_id: UUID) -> WorkerTask
    def complete_task(self, task_id: UUID, org_id: UUID) -> WorkerTask
    def cancel_task(self, task_id: UUID, org_id: UUID) -> WorkerTask
    def list_worker_tasks(self, worker_id: UUID, filters: TaskFilters, org_id: UUID) -> PaginatedTasks
```

### QRScanService (Location Time Tracking)

Records start/finish scans at physical locations for time tracking.

```python
class QRScanService:
    def record_location_scan(self, data: LocationScanRequest, org_id: UUID) -> LocationScan
    def get_time_summary(self, filters: TimeSummaryFilters, org_id: UUID) -> TimeSummary
```

### AllocationService

Manages location-to-item-group allocations.

```python
class AllocationService:
    def create_allocation(self, data: CreateAllocationRequest, org_id: UUID) -> LocationAllocation
    def update_allocation(self, allocation_id: UUID, data: UpdateAllocationRequest, org_id: UUID) -> LocationAllocation
    def deactivate_allocation(self, allocation_id: UUID, org_id: UUID) -> LocationAllocation
    def list_allocations(self, filters: AllocationFilters, org_id: UUID) -> PaginatedAllocations
    def check_exclusive_overlap(self, location_id: UUID, item_group_id: UUID, org_id: UUID) -> bool
```

### ScanEventService

Unified scan event recording across all contexts (inbound, pick, gate).

```python
class ScanEventService:
    def record_event(self, data: ScanEventCreate, org_id: UUID) -> ScanEvent
    def query_events(self, filters: ScanEventFilters, org_id: UUID) -> PaginatedScanEvents
```

## Data Models

### New Tables

#### `warehouse_locations`

The core table for the location hierarchy. Each row represents one node in the tree.

```sql
CREATE TABLE warehouse_locations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    warehouse_id        UUID NOT NULL REFERENCES warehouses_extended(id),
    parent_location_id  UUID REFERENCES warehouse_locations(id),
    location_type       VARCHAR(20) NOT NULL,
    code                VARCHAR(50) NOT NULL,
    full_path           VARCHAR(255),           -- e.g., Z01-A03-B02-L04-B01
    name                VARCHAR(255),
    capacity            NUMERIC(15, 3) DEFAULT 0,
    total_capacity      NUMERIC(15, 3) DEFAULT 0,
    available_capacity  NUMERIC(15, 3) DEFAULT 0,
    capacity_uom        VARCHAR(50),
    position_x          NUMERIC(10, 2) DEFAULT 0,
    position_y          NUMERIC(10, 2) DEFAULT 0,
    is_active           BOOLEAN DEFAULT TRUE,
    version             INTEGER DEFAULT 1,      -- optimistic locking
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_location_type CHECK (location_type IN ('zone', 'aisle', 'bay', 'level', 'bin'))
);

CREATE INDEX idx_wl_org ON warehouse_locations(organization_id);
CREATE INDEX idx_wl_warehouse ON warehouse_locations(warehouse_id);
CREATE INDEX idx_wl_parent ON warehouse_locations(parent_location_id);
CREATE INDEX idx_wl_type ON warehouse_locations(location_type);
CREATE INDEX idx_wl_active ON warehouse_locations(is_active);
CREATE INDEX idx_wl_full_path ON warehouse_locations(full_path);
CREATE UNIQUE INDEX idx_wl_warehouse_path ON warehouse_locations(warehouse_id, full_path);
```

#### `bin_stock_levels`

Tracks stock at the individual bin level.

```sql
CREATE TABLE bin_stock_levels (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    bin_location_id     UUID NOT NULL REFERENCES warehouse_locations(id),
    item_id             UUID NOT NULL REFERENCES items(id),
    quantity_on_hand    NUMERIC(15, 3) DEFAULT 0,
    batch_number        VARCHAR(100),
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_bin_item_batch UNIQUE (bin_location_id, item_id, batch_number)
);

CREATE INDEX idx_bsl_org ON bin_stock_levels(organization_id);
CREATE INDEX idx_bsl_bin ON bin_stock_levels(bin_location_id);
CREATE INDEX idx_bsl_item ON bin_stock_levels(item_id);
CREATE INDEX idx_bsl_created ON bin_stock_levels(created_at);
```

#### `location_allocations`

Links locations to item groups for put-away prioritization.

```sql
CREATE TABLE location_allocations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    location_id         UUID NOT NULL REFERENCES warehouse_locations(id),
    item_group_id       UUID NOT NULL,
    priority            INTEGER DEFAULT 0,
    allocation_type     VARCHAR(20) NOT NULL DEFAULT 'preferred',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_alloc_type CHECK (allocation_type IN ('exclusive', 'preferred')),
    CONSTRAINT uq_exclusive_alloc UNIQUE (location_id, allocation_type)
        WHERE allocation_type = 'exclusive'  -- partial unique index in migration
);

CREATE INDEX idx_la_org ON location_allocations(organization_id);
CREATE INDEX idx_la_location ON location_allocations(location_id);
CREATE INDEX idx_la_item_group ON location_allocations(item_group_id);
CREATE INDEX idx_la_active ON location_allocations(is_active);
```

#### `scan_sessions`

Groups QR scans into inbound or gate sessions.

```sql
CREATE TABLE scan_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    session_type        VARCHAR(20) NOT NULL,
    worker_id           UUID NOT NULL,
    warehouse_id        UUID NOT NULL REFERENCES warehouses_extended(id),
    dock_location       VARCHAR(255),
    status              VARCHAR(20) NOT NULL DEFAULT 'open',
    total_boxes_scanned INTEGER DEFAULT 0,
    started_at          TIMESTAMPTZ DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_session_type CHECK (session_type IN ('inbound', 'gate')),
    CONSTRAINT chk_session_status CHECK (status IN ('open', 'closed'))
);

CREATE INDEX idx_ss_org ON scan_sessions(organization_id);
CREATE INDEX idx_ss_worker ON scan_sessions(worker_id);
CREATE INDEX idx_ss_status ON scan_sessions(status);
CREATE INDEX idx_ss_warehouse ON scan_sessions(warehouse_id);
```

#### `scan_session_items`

Individual QR scans within a session.

```sql
CREATE TABLE scan_session_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    session_id          UUID NOT NULL REFERENCES scan_sessions(id) ON DELETE CASCADE,
    qr_identifier       VARCHAR(255) NOT NULL,
    sku                 VARCHAR(100) NOT NULL,
    quantity            INTEGER NOT NULL,
    batch_number        VARCHAR(100) NOT NULL,
    raw_qr_data         TEXT NOT NULL,
    scanned_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_session_qr UNIQUE (session_id, qr_identifier)
);

CREATE INDEX idx_ssi_session ON scan_session_items(session_id);
CREATE INDEX idx_ssi_sku ON scan_session_items(sku);
```

#### `receiving_slips`

Formal record of goods received, generated from closed scan sessions.

```sql
CREATE TABLE receiving_slips (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    slip_number         VARCHAR(100) NOT NULL,
    session_id          UUID NOT NULL REFERENCES scan_sessions(id),
    warehouse_id        UUID NOT NULL REFERENCES warehouses_extended(id),
    status              VARCHAR(30) NOT NULL DEFAULT 'pending_review',
    total_box_count     INTEGER NOT NULL DEFAULT 0,
    total_item_count    INTEGER NOT NULL DEFAULT 0,
    purchase_receipt_id UUID,
    put_away_list_id    UUID,
    rejection_reason    TEXT,
    notes               TEXT,
    reviewed_by         UUID,
    reviewed_at         TIMESTAMPTZ,
    created_by          UUID,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_rs_status CHECK (status IN ('pending_review', 'pending_putaway', 'putaway_complete', 'rejected'))
);

CREATE INDEX idx_rs_org ON receiving_slips(organization_id);
CREATE INDEX idx_rs_status ON receiving_slips(status);
CREATE INDEX idx_rs_warehouse ON receiving_slips(warehouse_id);
```

#### `receiving_slip_items`

Line items on a receiving slip, grouped by SKU + batch.

```sql
CREATE TABLE receiving_slip_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    receiving_slip_id   UUID NOT NULL REFERENCES receiving_slips(id) ON DELETE CASCADE,
    sku                 VARCHAR(100) NOT NULL,
    item_id             UUID REFERENCES items(id),
    batch_number        VARCHAR(100) NOT NULL,
    quantity            INTEGER NOT NULL,
    flag                VARCHAR(20),
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_rsi_flag CHECK (flag IS NULL OR flag IN ('SHORT', 'DAMAGED'))
);

CREATE INDEX idx_rsi_slip ON receiving_slip_items(receiving_slip_id);
CREATE INDEX idx_rsi_sku ON receiving_slip_items(sku);
```

#### `gate_verification_sessions`

Gate security verification sessions linked to completed pick lists.

```sql
CREATE TABLE gate_verification_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    pick_list_id        UUID NOT NULL REFERENCES pick_lists(id),
    vehicle_number      VARCHAR(100) NOT NULL,
    driver_name         VARCHAR(255),
    driver_contact      VARCHAR(50),
    status              VARCHAR(20) NOT NULL DEFAULT 'open',
    total_expected      INTEGER NOT NULL DEFAULT 0,
    total_verified      INTEGER NOT NULL DEFAULT 0,
    worker_id           UUID NOT NULL,
    started_at          TIMESTAMPTZ DEFAULT now(),
    verified_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_gvs_status CHECK (status IN ('open', 'verified', 'cancelled'))
);

CREATE INDEX idx_gvs_org ON gate_verification_sessions(organization_id);
CREATE INDEX idx_gvs_pick_list ON gate_verification_sessions(pick_list_id);
CREATE INDEX idx_gvs_status ON gate_verification_sessions(status);
```

#### `gate_verification_items`

Individual items scanned at the gate.

```sql
CREATE TABLE gate_verification_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    gate_session_id     UUID NOT NULL REFERENCES gate_verification_sessions(id) ON DELETE CASCADE,
    qr_identifier       VARCHAR(255) NOT NULL,
    sku                 VARCHAR(100) NOT NULL,
    quantity            INTEGER NOT NULL,
    batch_number        VARCHAR(100),
    pick_list_item_id   UUID REFERENCES pick_list_items(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'verified',
    scanned_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_gvi_status CHECK (status IN ('verified', 'unauthorized')),
    CONSTRAINT uq_gate_qr UNIQUE (gate_session_id, qr_identifier)
);

CREATE INDEX idx_gvi_session ON gate_verification_items(gate_session_id);
CREATE INDEX idx_gvi_status ON gate_verification_items(status);
```

#### `dispatch_records`

End-to-end traceability record for outbound shipments.

```sql
CREATE TABLE dispatch_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    dispatch_number     VARCHAR(100) NOT NULL,
    pick_list_id        UUID NOT NULL REFERENCES pick_lists(id),
    gate_session_id     UUID NOT NULL REFERENCES gate_verification_sessions(id),
    invoice_reference   VARCHAR(255),
    vehicle_number      VARCHAR(100) NOT NULL,
    driver_name         VARCHAR(255),
    driver_contact      VARCHAR(50),
    dispatched_at       TIMESTAMPTZ DEFAULT now(),
    created_by          UUID,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_dr_org ON dispatch_records(organization_id);
CREATE INDEX idx_dr_pick_list ON dispatch_records(pick_list_id);
CREATE INDEX idx_dr_vehicle ON dispatch_records(vehicle_number);
CREATE INDEX idx_dr_dispatched ON dispatch_records(dispatched_at);
```

#### `worker_tasks`

Trackable units of work assigned to warehouse workers.

```sql
CREATE TABLE worker_tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    task_type           VARCHAR(20) NOT NULL,
    worker_id           UUID NOT NULL,
    reference_id        UUID NOT NULL,          -- put_away_list_id or pick_list_id
    status              VARCHAR(20) NOT NULL DEFAULT 'assigned',
    assigned_at         TIMESTAMPTZ DEFAULT now(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT chk_wt_type CHECK (task_type IN ('put_away', 'pick')),
    CONSTRAINT chk_wt_status CHECK (status IN ('assigned', 'in_progress', 'completed', 'cancelled'))
);

CREATE INDEX idx_wt_org ON worker_tasks(organization_id);
CREATE INDEX idx_wt_worker ON worker_tasks(worker_id);
CREATE INDEX idx_wt_status ON worker_tasks(status);
CREATE INDEX idx_wt_type ON worker_tasks(task_type);
```

#### `location_scans`

QR scans at physical locations for time tracking.

```sql
CREATE TABLE location_scans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    worker_task_id      UUID NOT NULL REFERENCES worker_tasks(id),
    task_item_id        UUID NOT NULL,          -- put_away_list_item_id or pick_list_item_id
    location_code       VARCHAR(255) NOT NULL,
    scan_type           VARCHAR(10) NOT NULL,
    scanned_at          TIMESTAMPTZ DEFAULT now(),
    elapsed_seconds     INTEGER,                -- calculated on finish scan

    CONSTRAINT chk_ls_type CHECK (scan_type IN ('start', 'finish'))
);

CREATE INDEX idx_ls_org ON location_scans(organization_id);
CREATE INDEX idx_ls_task ON location_scans(worker_task_id);
CREATE INDEX idx_ls_task_item ON location_scans(task_item_id);
```

### Modifications to Existing Tables

#### `pick_lists` — Add invoice reference and dispatch link

```sql
ALTER TABLE pick_lists ADD COLUMN invoice_reference VARCHAR(255);
ALTER TABLE pick_lists ADD COLUMN invoice_data JSONB;
ALTER TABLE pick_lists ADD COLUMN dispatch_record_id UUID REFERENCES dispatch_records(id);
```

#### `pick_list_items` — Add picked quantity and bin location

```sql
ALTER TABLE pick_list_items ADD COLUMN picked_qty NUMERIC(15, 3) DEFAULT 0;
ALTER TABLE pick_list_items ADD COLUMN bin_location_id UUID REFERENCES warehouse_locations(id);
ALTER TABLE pick_list_items ADD COLUMN sort_order INTEGER;
```

#### `put_away_list_items` — Add bin location and sort order

```sql
ALTER TABLE put_away_list_items ADD COLUMN bin_location_id UUID REFERENCES warehouse_locations(id);
ALTER TABLE put_away_list_items ADD COLUMN sort_order INTEGER;
ALTER TABLE put_away_list_items ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
```

#### `qr_scan_events` — Used as-is for audit trail

The existing `qr_scan_events` table stores all scan audit data. The `extra_data` JSONB field holds context:

```json
{
  "scan_context": "inbound|pick|gate",
  "session_id": "uuid",
  "pick_list_id": "uuid",
  "decoded_payload": { "sku": "...", "quantity": 10, "batch": "..." },
  "device_type": "android",
  "os": "Android 14"
}
```

## API Endpoints

### Layout & Capacity Endpoints

| Method | Path                                              | Description                                                  |
| ------ | ------------------------------------------------- | ------------------------------------------------------------ |
| POST   | `/api/v1/warehouse-locations`                     | Create a location node                                       |
| GET    | `/api/v1/warehouse-locations/tree/{warehouse_id}` | Get full hierarchy tree                                      |
| GET    | `/api/v1/warehouse-locations`                     | List locations (filtered by type, parent, active, has_stock) |
| GET    | `/api/v1/warehouse-locations/{id}`                | Get location detail                                          |
| PATCH  | `/api/v1/warehouse-locations/{id}`                | Update location (name, capacity, position)                   |
| POST   | `/api/v1/warehouse-locations/{id}/deactivate`     | Deactivate location and descendants                          |
| GET    | `/api/v1/warehouse-locations/{id}/summary`        | Get subtree summary (bins, capacity, stock)                  |
| GET    | `/api/v1/warehouse-locations/search`              | Search by code or name                                       |

### Bin Stock Endpoints

| Method | Path                               | Description                     |
| ------ | ---------------------------------- | ------------------------------- |
| GET    | `/api/v1/bin-stock/{bin_id}`       | Get stock levels for a bin      |
| GET    | `/api/v1/bin-stock/item/{item_id}` | Get all bins containing an item |
| POST   | `/api/v1/bin-stock/add`            | Add stock to a bin              |
| POST   | `/api/v1/bin-stock/remove`         | Remove stock from a bin         |

### Location Allocation Endpoints

| Method | Path                                           | Description                 |
| ------ | ---------------------------------------------- | --------------------------- |
| POST   | `/api/v1/location-allocations`                 | Create allocation           |
| GET    | `/api/v1/location-allocations`                 | List allocations (filtered) |
| GET    | `/api/v1/location-allocations/{id}`            | Get allocation detail       |
| PATCH  | `/api/v1/location-allocations/{id}`            | Update allocation           |
| POST   | `/api/v1/location-allocations/{id}/deactivate` | Deactivate allocation       |

### Inbound Endpoints

| Method | Path                                                   | Description                             |
| ------ | ------------------------------------------------------ | --------------------------------------- |
| POST   | `/api/v1/inbound/sessions`                             | Start a new inbound scan session        |
| POST   | `/api/v1/inbound/sessions/{id}/scan`                   | Record a QR scan within a session       |
| POST   | `/api/v1/inbound/sessions/{id}/end`                    | End session and generate receiving slip |
| GET    | `/api/v1/inbound/sessions/{id}`                        | Get session details with summary        |
| GET    | `/api/v1/inbound/receiving-slips`                      | List receiving slips (filtered)         |
| GET    | `/api/v1/inbound/receiving-slips/{id}`                 | Get receiving slip detail               |
| POST   | `/api/v1/inbound/receiving-slips/{id}/approve`         | Approve slip → trigger put-away         |
| POST   | `/api/v1/inbound/receiving-slips/{id}/reject`          | Reject slip with reason                 |
| PATCH  | `/api/v1/inbound/receiving-slips/{id}/items/{item_id}` | Flag line item (SHORT/DAMAGED)          |

### Put-Away Endpoints

| Method | Path                                                   | Description                    |
| ------ | ------------------------------------------------------ | ------------------------------ |
| GET    | `/api/v1/put-away-lists`                               | List put-away lists (filtered) |
| GET    | `/api/v1/put-away-lists/{id}`                          | Get put-away list with items   |
| POST   | `/api/v1/put-away-lists/{id}/items/{item_id}/complete` | Mark item as completed         |
| POST   | `/api/v1/put-away-lists/{id}/items/{item_id}/skip`     | Skip item with reason          |

### Pick List Endpoints (Outbound)

| Method | Path                                        | Description                       |
| ------ | ------------------------------------------- | --------------------------------- |
| POST   | `/api/v1/outbound/pick-lists/from-invoice`  | Create pick list from SAP invoice |
| GET    | `/api/v1/outbound/pick-lists`               | List pick lists (filtered)        |
| GET    | `/api/v1/outbound/pick-lists/{id}`          | Get pick list with progress       |
| POST   | `/api/v1/outbound/pick-lists/{id}/scan`     | Record a pick scan                |
| POST   | `/api/v1/outbound/pick-lists/{id}/complete` | Mark pick list as completed       |
| POST   | `/api/v1/outbound/pick-lists/{id}/cancel`   | Cancel pick list                  |

### Gate Verification Endpoints

| Method | Path                                         | Description                     |
| ------ | -------------------------------------------- | ------------------------------- |
| POST   | `/api/v1/outbound/gate-sessions`             | Start gate verification session |
| POST   | `/api/v1/outbound/gate-sessions/{id}/scan`   | Record a gate scan              |
| GET    | `/api/v1/outbound/gate-sessions/{id}`        | Get session with progress       |
| POST   | `/api/v1/outbound/gate-sessions/{id}/verify` | Mark session as verified        |

### Dispatch Endpoints

| Method | Path                               | Description                      |
| ------ | ---------------------------------- | -------------------------------- |
| GET    | `/api/v1/outbound/dispatches`      | List dispatch records (filtered) |
| GET    | `/api/v1/outbound/dispatches/{id}` | Get dispatch record detail       |

### Worker Task Endpoints

| Method | Path                                 | Description                                   |
| ------ | ------------------------------------ | --------------------------------------------- |
| POST   | `/api/v1/worker-tasks`               | Create/assign a task                          |
| GET    | `/api/v1/worker-tasks`               | List tasks (filtered by worker, status, date) |
| GET    | `/api/v1/worker-tasks/{id}`          | Get task detail                               |
| POST   | `/api/v1/worker-tasks/{id}/start`    | Start a task                                  |
| POST   | `/api/v1/worker-tasks/{id}/complete` | Complete a task                               |
| POST   | `/api/v1/worker-tasks/{id}/cancel`   | Cancel a task                                 |

### Location Scan (Time Tracking) Endpoints

| Method | Path                             | Description                              |
| ------ | -------------------------------- | ---------------------------------------- |
| POST   | `/api/v1/location-scans`         | Record a start/finish scan at a location |
| GET    | `/api/v1/location-scans/summary` | Get time tracking summaries (filtered)   |

### Scan Event Audit Endpoints

| Method | Path                  | Description                                                    |
| ------ | --------------------- | -------------------------------------------------------------- |
| GET    | `/api/v1/scan-events` | Query scan events (filtered by session, worker, date, context) |

## Error Handling

### Validation Errors (422)

| Scenario                              | Error Message                                                                            |
| ------------------------------------- | ---------------------------------------------------------------------------------------- |
| QR payload missing SKU                | `"Invalid QR payload: missing SKU identifier"`                                           |
| QR payload invalid quantity           | `"Invalid QR payload: quantity must be a positive integer"`                              |
| QR payload missing batch              | `"Invalid QR payload: missing batch number"`                                             |
| Duplicate QR scan in session          | `"QR code already scanned in this session (ID: {qr_identifier})"`                        |
| Scan on closed session                | `"Cannot scan: session is closed"`                                                       |
| Pick scan item not on list            | `"Scanned item (SKU: {sku}) is not on this pick list"`                                   |
| Pick scan over-picking                | `"Over-pick: scanned qty ({qty}) would exceed required qty ({required}) for item {sku}"` |
| Pick list not fully picked            | `"Cannot complete: {remaining} items still pending"`                                     |
| Gate scan unauthorized item           | `"Unauthorized item: SKU {sku} is not on the associated pick list"`                      |
| Invoice missing required fields       | `"SAP invoice missing required field: {field}"`                                          |
| Invalid parent type for location      | `"A {type} must have a {expected_parent} as parent, got {actual_parent}"`                |
| Bin capacity exceeded                 | `"Cannot add {qty} to bin {code}: available capacity is {available}"`                    |
| Stock removal exceeds on-hand         | `"Cannot remove {qty} from bin {code}: only {on_hand} on hand"`                          |
| Finish scan without start             | `"Cannot record finish scan: no start scan found for task item {id}"`                    |
| Overlapping exclusive allocation      | `"Location {code} already has an exclusive allocation for item group {group}"`           |
| Deactivated location stock assignment | `"Cannot assign stock to deactivated location {code}"`                                   |

### Not Found Errors (404)

| Scenario                  | Error Message                                        |
| ------------------------- | ---------------------------------------------------- |
| Location not found        | `"Warehouse location with ID {id} not found"`        |
| Session not found         | `"Scan session with ID {id} not found"`              |
| Receiving slip not found  | `"Receiving slip with ID {id} not found"`            |
| Pick list not found       | `"Pick list with ID {id} not found"`                 |
| Gate session not found    | `"Gate verification session with ID {id} not found"` |
| Dispatch record not found | `"Dispatch record with ID {id} not found"`           |
| Worker task not found     | `"Worker task with ID {id} not found"`               |
| Allocation not found      | `"Location allocation with ID {id} not found"`       |

### Conflict Errors (409)

| Scenario                            | Error Message                                                                 |
| ----------------------------------- | ----------------------------------------------------------------------------- |
| Session already closed              | `"Session is already closed"`                                                 |
| Pick list wrong status for scan     | `"Pick list must be OPEN or IN_PROGRESS to accept scans (current: {status})"` |
| Pick list wrong status for complete | `"Pick list must be IN_PROGRESS to be completed (current: {status})"`         |
| Gate session already verified       | `"Gate session is already verified"`                                          |
| Slip already approved/rejected      | `"Receiving slip has already been {status}"`                                  |
| Task already started                | `"Task is already in progress"`                                               |
| Task already completed              | `"Task is already completed"`                                                 |
| Concurrent capacity conflict        | `"Capacity conflict detected, please retry"`                                  |

## Status Transition Rules

### Receiving Slip Status

```
                    ┌──────────────┐
                    │ PENDING_REVIEW│
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
    ┌─────────────────┐       ┌──────────────┐
    │ PENDING_PUTAWAY │       │   REJECTED   │
    └────────┬────────┘       └──────────────┘
             │
             ▼
    ┌─────────────────┐
    │ PUTAWAY_COMPLETE│
    └─────────────────┘
```

- `pending_review` → `pending_putaway` (manager approves)
- `pending_review` → `rejected` (manager rejects with reason)
- `pending_putaway` → `putaway_complete` (all put-away items completed)

### Pick List Status

```
    ┌──────┐
    │ OPEN │
    └──┬───┘
       │
       ├──────────────────────┐
       ▼                      ▼
    ┌─────────────┐     ┌───────────┐
    │ IN_PROGRESS │     │ CANCELLED │
    └──────┬──────┘     └───────────┘
           │
           ├──────────────────┐
           ▼                  ▼
    ┌───────────┐       ┌───────────┐
    │ COMPLETED │       │ CANCELLED │
    └───────────┘       └───────────┘
```

- `open` → `in_progress` (first pick scan recorded)
- `open` → `cancelled` (manual cancel)
- `in_progress` → `completed` (all items picked, user confirms)
- `in_progress` → `cancelled` (manual cancel, releases reserved stock)

### Gate Verification Session Status

```
    ┌──────┐
    │ OPEN │
    └──┬───┘
       │
       ├──────────────────┐
       ▼                  ▼
    ┌──────────┐    ┌───────────┐
    │ VERIFIED │    │ CANCELLED │
    └──────────┘    └───────────┘
```

- `open` → `verified` (all pick list items scanned and verified)
- `open` → `cancelled` (manual cancel)

### Worker Task Status

```
    ┌──────────┐
    │ ASSIGNED │
    └────┬─────┘
         │
         ├──────────────────────┐
         ▼                      ▼
    ┌─────────────┐       ┌───────────┐
    │ IN_PROGRESS │       │ CANCELLED │
    └──────┬──────┘       └───────────┘
           │
           ├──────────────────┐
           ▼                  ▼
    ┌───────────┐       ┌───────────┐
    │ COMPLETED │       │ CANCELLED │
    └───────────┘       └───────────┘
```

- `assigned` → `in_progress` (worker starts task)
- `assigned` → `cancelled` (supervisor cancels)
- `in_progress` → `completed` (all items done)
- `in_progress` → `cancelled` (supervisor cancels)

### Put-Away List Status

```
    ┌─────────┐
    │ PENDING │
    └────┬────┘
         │
         ▼
    ┌─────────────┐
    │ IN_PROGRESS │
    └──────┬──────┘
           │
           ▼
    ┌───────────┐
    │ COMPLETED │
    └───────────┘
```

- `pending` → `in_progress` (first item completed)
- `in_progress` → `completed` (all items completed or skipped)

### Put-Away List Item Status

- `pending` → `completed` (worker places item in bin)
- `pending` → `skipped` (worker skips, flagged for review)

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Location Hierarchy Enforcement

_For any_ location creation request with a given `location_type` and `parent_location_id`, the system SHALL accept the creation only if the parent's `location_type` matches the expected parent in the hierarchy (warehouse→zone→aisle→bay→level→bin), and SHALL reject with a validation error otherwise.

**Validates: Requirements 1.2, 1.3**

### Property 2: Location Code Generation

_For any_ location node created in the hierarchy, the generated `full_path` SHALL equal the concatenation of all ancestor codes from zone down to the current node, separated by hyphens (e.g., Z01-A03-B02-L04-B01).

**Validates: Requirements 1.4**

### Property 3: Capacity Rollup Consistency

_For any_ location in the hierarchy that has children, its `total_capacity` SHALL equal the sum of all its direct active children's `total_capacity` values. When a bin's capacity is set, updated, or the bin is deactivated, all ancestor `total_capacity` values SHALL be recalculated accordingly.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6**

### Property 4: Available Capacity Invariant

_For any_ location in the hierarchy, its `available_capacity` SHALL equal `total_capacity` minus the sum of all `quantity_on_hand` values in `bin_stock_levels` within that location's subtree.

**Validates: Requirements 2.5**

### Property 5: Deactivated Location Stock Prevention

_For any_ deactivated location (or descendant of a deactivated location), any attempt to add stock SHALL be rejected with a validation error.

**Validates: Requirements 1.6**

### Property 6: Bin Stock Addition and Removal Consistency

_For any_ stock addition of quantity Q to bin B for item I, the `quantity_on_hand` in `bin_stock_levels` for (B, I) SHALL increase by Q, and the warehouse-level `stock_levels` record SHALL increase by Q. Symmetrically, for any removal of quantity Q, both SHALL decrease by Q.

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 7: Bin Capacity Overflow Prevention

_For any_ stock addition that would cause the total stock in a bin to exceed the bin's capacity, the operation SHALL be rejected and the bin's stock SHALL remain unchanged.

**Validates: Requirements 3.5**

### Property 8: QR Payload Round-Trip

_For any_ valid QR payload containing a SKU (non-empty string), positive integer quantity, and batch number, encoding the payload and then decoding it SHALL produce the original SKU, quantity, and batch values unchanged.

**Validates: Requirements 4.1**

### Property 9: Invalid Quantity Rejection

_For any_ QR payload where the quantity field is not a positive integer (zero, negative, float, null, or non-numeric), the InboundService SHALL reject the scan and return a validation error.

**Validates: Requirements 4.3**

### Property 10: Duplicate Scan Rejection Within Session

_For any_ QR code with a unique identifier scanned within a session, scanning the same QR code a second time within the same session SHALL be rejected, and the session's item count SHALL remain unchanged.

**Validates: Requirements 5.4**

### Property 11: Session Aggregation Correctness

_For any_ sequence of valid QR scans within a session, the session summary's per-SKU-and-batch quantity totals SHALL equal the sum of individual scan quantities grouped by (SKU, batch_number), and the total box count SHALL equal the number of unique QR codes scanned.

**Validates: Requirements 5.3, 5.6**

### Property 12: Receiving Slip Generation Correctness

_For any_ closed scan session with N unique scans, the generated receiving slip SHALL contain items grouped by (SKU, batch_number) where each group's quantity equals the sum of scan quantities for that group, the total_box_count equals N, and the total_item_count equals the sum of all quantities.

**Validates: Requirements 6.1, 6.4**

### Property 13: Receiving Slip to Purchase Receipt Consistency

_For any_ receiving slip, the corresponding purchase receipt SHALL have line items where each line's SKU and quantity matches a receiving slip item, and the total number of line items matches.

**Validates: Requirements 6.3**

### Property 14: Approval Triggers Put-Away Generation

_For any_ receiving slip in PENDING_REVIEW status that is approved, the status SHALL transition to PENDING_PUTAWAY and a put-away list SHALL be generated with items covering all non-flagged slip items, where the sum of assigned quantities per item equals the slip item quantity.

**Validates: Requirements 7.3, 8.1**

### Property 15: Put-Away Respects Bin Capacity

_For any_ put-away list generated from a receiving slip, no bin assignment SHALL exceed the bin's available capacity at the time of assignment.

**Validates: Requirements 8.2**

### Property 16: Put-Away Routing Groups by Aisle

_For any_ put-away list with items targeting multiple aisles, items assigned to bins in the same aisle SHALL be contiguous in the sort order.

**Validates: Requirements 8.3, 8.4**

### Property 17: Put-Away Completion Updates Stock and Slip Status

_For any_ put-away list item marked as COMPLETED with quantity Q assigned to bin B for item I, the bin_stock_levels record for (B, I) SHALL have its quantity_on_hand increased by Q. When all items in a put-away list are COMPLETED, the receiving slip status SHALL transition to PUTAWAY_COMPLETE.

**Validates: Requirements 8.5, 8.6**

### Property 18: Pick List Creation from Invoice

_For any_ SAP invoice with N line items, the created pick list SHALL have status OPEN, contain exactly N pick list items with SKUs and quantities matching the invoice lines, and have the invoice_reference field set.

**Validates: Requirements 9.1, 9.2**

### Property 19: FIFO Bin Resolution

_For any_ pick list item resolved to bin locations, the bins SHALL be selected in order of stock creation date (oldest first), and the total resolved quantity across all bins SHALL equal the required quantity.

**Validates: Requirements 9.3**

### Property 20: Pick Scan Matching and Over-Pick Prevention

_For any_ valid QR scan against a pick list where the SKU matches a pending item, the picked_qty SHALL increase by the scanned quantity. If the scanned quantity would exceed the required quantity, the scan SHALL be rejected and picked_qty SHALL remain unchanged. If the SKU does not match any pending item, the scan SHALL be rejected.

**Validates: Requirements 10.2, 10.3, 10.4, 10.5**

### Property 21: Pick List Status Transitions

_For any_ pick list in OPEN status, the first successful pick scan SHALL transition the status to IN_PROGRESS. A pick list SHALL only be completable when all items have picked_qty equal to required_qty.

**Validates: Requirements 10.6, 11.2**

### Property 22: Stock Release on Pick List Cancellation

_For any_ pick list with reserved stock that is cancelled, the warehouse stock_levels quantity_reserved SHALL be decremented and quantity_available SHALL be incremented by the previously reserved amounts.

**Validates: Requirements 11.5**

### Property 23: Gate Verification Against Pick List

_For any_ gate verification session linked to a completed pick list, scanning a QR code whose SKU matches a pick list item SHALL be marked as VERIFIED, and scanning a QR code whose SKU does not match any pick list item SHALL be flagged as UNAUTHORIZED.

**Validates: Requirements 12.3, 12.4**

### Property 24: Gate Session Completion Triggers Dispatch

_For any_ gate session where all pick list items have been verified, the session SHALL transition to VERIFIED status, and a dispatch record SHALL be created containing the pick_list_id, vehicle_number, gate_session_id, and dispatch timestamp. The warehouse stock_levels for each dispatched item SHALL be decremented.

**Validates: Requirements 12.5, 12.6, 13.1, 13.4**

### Property 25: Scan Event Audit Completeness

_For any_ QR scan performed in any context (inbound, pick, or gate), a scan event record SHALL be created in qr_scan_events containing the worker_id, scan timestamp, scan context, session_id, and decoded payload data.

**Validates: Requirements 14.1**

### Property 26: Routing Optimizer Aisle Grouping

_For any_ set of bin locations passed to the RoutingOptimizer where two or more bins share the same aisle, those bins SHALL be contiguous in the output sort order. The first location in the output SHALL be the nearest to the origin point.

**Validates: Requirements 15.1, 15.2, 15.3, 15.4**

### Property 27: Time Tracking Elapsed Calculation

_For any_ finish scan at a location that has a preceding start scan for the same task_item, the elapsed_seconds SHALL equal the difference between finish timestamp and start timestamp in seconds. A finish scan without a preceding start scan SHALL be rejected.

**Validates: Requirements 17.2, 17.3, 17.4**

### Property 28: Real-Time Capacity Update on Stock Change

_For any_ bin stock change (add or remove), the available_capacity of the bin and all ancestor locations up to the warehouse SHALL be recalculated within the same database transaction.

**Validates: Requirements 18.1, 18.2, 18.3, 18.4**

### Property 29: Exclusive Allocation Enforcement

_For any_ location with an exclusive allocation for item_group_id G, the put-away service SHALL only assign items belonging to group G to that location. Items from other groups SHALL be skipped to the next available bin.

**Validates: Requirements 20.3, 20.5, 20.6**

### Property 30: No Overlapping Exclusive Allocations

_For any_ attempt to create an exclusive allocation on a location that already has an active exclusive allocation for a different item group, the system SHALL reject the request with a validation error.

**Validates: Requirements 20.8**

### Property 31: Location Filter Accuracy

_For any_ location list query with filters (location_type, parent_location_id, is_active, has_stock), all returned locations SHALL satisfy all specified filter criteria, and no location satisfying all criteria SHALL be omitted from the results.

**Validates: Requirements 19.1, 19.2, 19.3**

### Property 32: Location Search Correctness

_For any_ search query string, all returned locations SHALL have the query string as a substring of either their `code` or `name` field (case-insensitive).

**Validates: Requirements 19.4**

## Testing Strategy

### Property-Based Testing

**Library:** [Hypothesis](https://hypothesis.readthedocs.io/) (Python)

**Configuration:** Minimum 100 iterations per property test.

**Tag format:** `Feature: warehouse-qr-inbound-outbound, Property {number}: {property_text}`

Hypothesis strategies will generate:

- Random QR payloads (valid and invalid SKUs, quantities, batches)
- Random scan sequences within sessions (with duplicates)
- Random location hierarchies (valid and invalid parent-child combinations)
- Random bin capacities and stock quantities
- Random pick list items with varying quantities
- Random gate scan sequences (matching and non-matching items)
- Random SAP invoice payloads
- Random location allocation configurations (exclusive/preferred)
- Random time tracking scan pairs (start/finish)

### Unit Tests (Example-Based)

- Location hierarchy: create full tree, verify codes and capacity rollup
- Session lifecycle: create → scan → end → slip generated
- Receiving slip review: approve/reject flows
- Put-away generation: verify bin assignments respect allocations and capacity
- Pick list from invoice: verify item mapping and FIFO resolution
- Gate verification: full happy path
- Dispatch creation: verify stock deduction
- Worker task lifecycle: assign → start → complete
- Time tracking: start scan → finish scan → elapsed calculation
- Edge cases: empty sessions, single-item pick lists, bins at capacity

### Integration Tests

- Concurrent stock updates with optimistic locking
- Full inbound flow: session → slip → approve → put-away → stock update
- Full outbound flow: invoice → pick list → pick → gate → dispatch
- Capacity rollup under concurrent bin modifications
- Transaction isolation for stock operations
