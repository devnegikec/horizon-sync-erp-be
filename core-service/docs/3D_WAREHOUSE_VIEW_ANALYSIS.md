# 3D Warehouse View — Analysis & Issue Report

> **Date:** 2026-06-17  
> **Scope:** Review of design docs, implementation code, and identified gaps  
> **Files Reviewed:**  
> - `docs/3D_WAREHOUSE_VIEW_DESIGN.md`  
> - `docs/3D_WAREHOUSE_IMPLEMENTATION.md`  
> - `app/services/warehouse_3d_service.py`  
> - `app/api/v1/endpoints/wms_3d.py`  
> - Frontend: `Warehouse3DView.tsx`, `LocationTreeView.tsx`, `WarehouseLayoutDesigner.tsx`, `useWarehouse3D.ts`, `wms3d.types.ts`

---

## 1. Document Quality Assessment

Both the design document and implementation document are well-structured and comprehensive. They cover:

- Full architecture (frontend canvas, backend FastAPI, real-time WebSocket + Redis)
- Multi-tenant dynamic layout configuration
- Scoring algorithms for put-away and pick suggestions
- Concurrency model with TTL-based bin reservations
- Phased implementation plan (Phase 0–4)
- Performance considerations (LOD, polling intervals, transaction batching)

**Overall quality: Good** — the documents provide a clear roadmap from design to implementation.

---

## 2. Issues Found

### 2.1 CRITICAL: Stock Details Not Showing on Bin Click

**Design Requirement (FR-3D-04):**
> Clicking a bin shall display a detail panel showing:
> - Bin code and full path
> - **Items stored (name, SKU, quantity, batch number, expiry date)**
> - Available capacity vs total capacity
> - Current reservation status (locked by whom, time remaining)

**Current Implementation:**
The `BinDetailPanel` component only displays **aggregate data**:
- Fill percentage (single number)
- Available capacity / total capacity
- Items count (a count, not a list of items)
- Zone / Aisle / Bay / Level codes
- Reservation status badge + expiry countdown

**What's Missing:**
- No individual item names, SKUs, or item codes
- No per-item quantity breakdown
- No batch numbers
- No expiry dates per item

**Root Cause — Backend (`warehouse_3d_service.py`):**

The `_bin_stock_map()` method only computes aggregates:

```python
def _bin_stock_map(self, warehouse_id, org_id):
    rows = (
        self.db.query(
            BinStockLevel.bin_location_id,
            func.sum(BinStockLevel.quantity_on_hand),      # total qty only
            func.count(func.distinct(BinStockLevel.item_id)),  # item count only
        )
        .group_by(BinStockLevel.bin_location_id)
        .all()
    )
```

The `build_bin()` method maps this to:
```python
return {
    ...
    "items_count": agg["items"],   # just a number (e.g. 3)
    ...
}
```

There is **no query** that fetches individual `BinStockLevel` records joined with the `items` table to get item names, SKUs, batch numbers, or expiry dates.

**Root Cause — Frontend (`Warehouse3DView.tsx`):**

- The `FlatBin` TypeScript type (extends `LayoutBin`) has no field for item details — only `items_count: number`
- The `BinDetailPanel` renders only the aggregate values it receives
- No separate API call is made when a bin is clicked to fetch detailed stock

**Root Cause — No Hover/Tooltip:**

- The canvas only has an `onClick` handler (`handleCanvasClick`)
- There is no `onMouseMove`-based hit-test for hover detection
- No tooltip component is rendered on hover

---

### 2.2 MEDIUM: No Hover Tooltip on Bins

**Design implication:** The design document describes an interactive 3D view where users can explore bins. A hover tooltip showing quick info (bin code, fill %) before clicking would significantly improve UX.

**Current state:** Only click-to-select is implemented. The user must click a bin to see any information — there's no visual feedback on hover indicating which bin the cursor is over.

---

### 2.3 MEDIUM: Expiry Date Not Shown in Detail Panel

The backend does compute `has_expiring_items` (boolean flag per bin) and the `BinDetailPanel` shows an "Expiring items" badge, but:
- No specific expiry dates are displayed
- No breakdown of which items are expiring and when
- The `_expiring_bin_ids()` helper only returns a set of bin UUIDs, not expiry details

---

### 2.4 LOW: WebSocket Not Fully Wired

The implementation document notes WebSocket as Phase 3 with "if implemented" caveats. Currently:
- The `useWarehouse3D` hook attempts a WebSocket connection and handles `bin_reserved`/`bin_released` events
- The backend WebSocket endpoint may or may not be deployed
- HTTP polling every 5 seconds serves as the fallback and works reliably

This is a Phase 3 item and not blocking core functionality.

---

### 2.5 LOW: Design Doc Lists React Three Fiber but Implementation Uses 2D Canvas

**Design document (Section 6.1)** specifies:
- `@react-three/fiber` (React renderer for Three.js)
- `@react-three/drei` (helpers)
- `three` (core 3D engine)

**Actual implementation** uses a native HTML5 `<canvas>` with a custom isometric projection (2D rendering that simulates 3D). This is a valid alternative that's lighter weight and performs better, but the documentation should be updated to reflect this decision.

---

## 3. How the Location Tree Works

### 3.1 Overview

The **Location Tree** (`LocationTreeView.tsx`) displays the warehouse's physical hierarchy as an expandable data table. It shows the full structure from zones down to individual bins.

### 3.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  WMSManagement.tsx                                           │
│    └── LayoutView                                            │
│          └── "Location Tree" tab                             │
│                └── LocationTreeView (warehouseId)            │
│                      └── useLocationTree(warehouseId)        │
│                            → GET /api/v1/wms/warehouses/{id}/locations/tree │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow

1. `useLocationTree(warehouseId)` fetches the full nested tree from the backend
2. Backend returns `LocationTree[]` with recursive `children[]` arrays:
   ```
   Zone → children: [Aisle → children: [Bay → children: [Level → children: [Bin]]]]
   ```
3. `computeDerived()` walks the tree **bottom-up**:
   - Leaf bins use their own `total_capacity` and `available_capacity`
   - Parent nodes roll up: `derived_capacity = sum(children.derived_capacity)`
4. `@tanstack/react-table` renders with `getExpandedRowModel()` for nested expandable rows

### 3.4 Columns Displayed

| Column | Description |
|---|---|
| Type / Code | Location type badge + code (e.g. `ZN-A`, `A01`, `B01`, `L1`, `BIN-001`) |
| Name | Human-readable name |
| Full Path | Complete hierarchy path (e.g. `WH1-A-A01-B01-L1`) |
| Own Capacity | The capacity defined directly on this node |
| Derived Capacity | Roll-up capacity with color bar (green/yellow/red) |
| Available | Remaining capacity with color-coded number |
| Status | Active / Inactive badge |

### 3.5 Key Features

- **Expand/Collapse All** buttons in toolbar
- **Bottom-up capacity aggregation** — zones show total capacity of all contained bins
- **Color-coded capacity bars** — green (<70%), yellow (70–90%), red (>90%)
- **Row click callback** — optional `onSelect` prop for integration with other views
- **Auto-expand** on first load (all rows start expanded)

### 3.6 How to Test

| Step | Action | Expected Result |
|---|---|---|
| 1 | Navigate to WMS module, select a warehouse | Warehouse appears in sidebar/dropdown |
| 2 | Go to "Layout" tab → "Location Tree" sub-tab | Tree table loads with hierarchy |
| 3 | Verify hierarchy levels | Zone → Aisle → Bay → Level → Bin visible when expanded |
| 4 | Check derived capacities | Zone capacity = sum of all its bins' capacities |
| 5 | Check capacity bars | Bars show correct fill percentage with appropriate color |
| 6 | Click "Collapse All" | All rows collapse to zone level only |
| 7 | Click "Expand All" | Full tree is visible again |
| 8 | Test with empty warehouse | Shows "No locations defined for this warehouse yet" |
| 9 | Test loading state | Shows "Loading warehouse layout..." with pulse animation |
| 10 | Test error state | Shows error message with "Retry" link |

---

## 4. How the Layout Designer Works

### 4.1 Overview

The **Layout Designer** (`WarehouseLayoutDesigner.tsx`) allows warehouse managers to define a complete location hierarchy through a form-based UI. It generates all `warehouse_locations` records with correct 3D coordinates in a single transaction.

### 4.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  WMSManagement.tsx                                           │
│    └── LayoutView                                            │
│          └── "Layout Designer" tab                           │
│                └── WarehouseLayoutDesigner (warehouseId)     │
│                      ├── ZoneCard (per zone)                 │
│                      │     └── AisleRow (per aisle)          │
│                      ├── SummaryBox (preview/apply result)   │
│                      └── floorPlanApi                         │
│                            ├── POST /floor-plans/preview     │
│                            └── POST /floor-plans/apply       │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Configuration Model (`FloorPlanConfig`)

```typescript
FloorPlanConfig {
  grid_unit: number           // Scale factor (default 1.0)
  zones: ZoneSpec[] {
    code: string              // e.g. "A", "B"
    name: string              // e.g. "Fast Movers"
    grid_x: number            // Zone X offset in world units
    grid_y: number            // Zone Y offset in world units
    aisles: AisleSpec[] {
      code: string            // e.g. "A01"
      orientation: "x" | "y"  // Bay spacing direction
      grid_x: number          // Aisle X offset within zone
      grid_y: number          // Aisle Y offset within zone
      num_bays: number        // How many bays along this aisle
      bay_spacing: number     // Distance between bays
      num_levels: number      // Vertical levels per bay
      bins_per_level: number  // Bins per level
      bin_capacity: number    // Capacity per bin
      bay_width: number       // Bay width in world units
      level_height: number    // Vertical spacing between levels
    }
  }
}
```

### 4.4 User Workflow

```
Step 1: Set grid unit (scale) — default 1.0
    │
Step 2: Add zones (A, B, C…)
    │   Each zone has a grid_x/grid_y offset so zones don't overlap
    │
Step 3: Per zone, add aisles
    │   Each aisle defines: orientation, num_bays, bay_spacing,
    │   num_levels, bins_per_level, bin_capacity
    │
Step 4: Click "Preview"
    │   → POST /floor-plans/preview (non-destructive)
    │   → Returns: zone_count, aisle_count, bay_count, level_count,
    │              bin_count, sample_codes, total_locations
    │
Step 5: Review summary — verify counts and sample codes
    │
Step 6: Enter a plan name + optionally check "Deactivate existing locations"
    │
Step 7: Click "Apply Layout"
        → POST /floor-plans/apply
        → Backend generates full hierarchy with 3D coordinates
        → Returns: floor_plan_id, locations_created, locations_deleted
```

### 4.5 Position Calculation (Backend Logic)

The `FloorPlanGeneratorService.apply()` computes 3D positions as follows:

| Element | X Position | Y Position | Z Position |
|---|---|---|---|
| Zone | `zone.grid_x` | `zone.grid_y` | 0 |
| Aisle | zone offset + `aisle.grid_x` | zone offset + `aisle.grid_y` | 0 |
| Bay (X-orientation) | aisle origin + `bay_index × bay_spacing` | aisle Y | 0 |
| Bay (Y-orientation) | aisle X | aisle origin + `bay_index × bay_spacing` | 0 |
| Level | bay X | bay Y | `level_index × level_height` |
| Bin | level X + bin offset | level Y | level Z |

### 4.6 Backend Behavior

- **Preview** — validates config, counts nodes recursively, returns summary. No database writes.
- **Apply** — creates all locations in one transaction:
  1. If `replace_existing=True`: soft-deletes all existing locations (`is_active = false`)
  2. Creates Zone → Aisle → Bay → Level → Bin hierarchy with correct parent references
  3. Assigns `position_x`, `position_y`, `position_z` per the calculation above
  4. Generates codes following `{wh_code}-{zone}-{aisle}-{bay}-{level}` pattern
  5. Persists config to `warehouse_floor_plans` table for future reference

### 4.7 How to Test

| Step | Action | Expected Result |
|---|---|---|
| 1 | Navigate to WMS → select warehouse → "Layout" → "Layout Designer" | Designer form loads with one default zone |
| 2 | Verify default zone | Zone A with 1 aisle: 4 bays, 3 levels, 2 bins/level = 24 bins |
| 3 | Modify aisle params | "X bins total" badge updates in real-time |
| 4 | Add a second zone | Zone B appears with grid_y offset of 10 (no 3D overlap) |
| 5 | Click "Preview" without plan name | Preview summary appears (counts + sample codes) |
| 6 | Verify preview is non-destructive | No new locations in Location Tree after preview |
| 7 | Enter plan name + click "Apply Layout" | Success message with locations_created count |
| 8 | Switch to "Location Tree" tab | New hierarchy is visible and expandable |
| 9 | Switch to "3D View" tab | Bins render with correct spatial positions |
| 10 | Test "Deactivate existing" checkbox | Old locations become inactive, new ones active |
| 11 | Test with no zones | "Apply" button should be disabled |
| 12 | Test with empty plan name | "Apply" button should be disabled |
| 13 | Add zone, remove it | Zone disappears, bin count updates |
| 14 | Add multiple aisles to one zone | Aisles render at different grid offsets in 3D |

---

## 5. Recommended Fixes

### 5.1 Fix: Stock Details on Bin Click (High Priority)

**Backend changes needed:**

1. Add a new endpoint `GET /api/v1/wms-3d/bin/{bin_id}/stock`:

```python
@router.get("/bin/{bin_id}/stock", summary="Get bin stock details")
async def get_bin_stock(bin_id: UUID, ...):
    """Return individual item records stored in a specific bin."""
    rows = (
        db.query(
            BinStockLevel.item_id,
            Item.item_name,
            Item.item_code,
            BinStockLevel.quantity_on_hand,
            BinStockLevel.batch_number,
            BinStockLevel.expiry_date,
            BinStockLevel.created_at,
        )
        .join(Item, BinStockLevel.item_id == Item.id)
        .filter(
            BinStockLevel.bin_location_id == bin_id,
            BinStockLevel.organization_id == org_id,
            BinStockLevel.quantity_on_hand > 0,
        )
        .order_by(BinStockLevel.expiry_date.asc().nullslast(), BinStockLevel.created_at.asc())
        .all()
    )
    return {"items": [...]}
```

2. Response schema:
```python
class BinStockItem(BaseModel):
    item_id: UUID
    item_name: str
    item_code: str
    quantity_on_hand: Decimal
    batch_number: str | None
    expiry_date: date | None
    created_at: datetime

class BinStockDetailResponse(BaseModel):
    bin_id: UUID
    items: list[BinStockItem]
```

**Frontend changes needed:**

1. Add API method: `wms3dApi.getBinStock(token, binId)` → calls `GET /wms-3d/bin/{binId}/stock`
2. Update `BinDetailPanel` to fetch stock on selection change and render item list:
   - Item name + code
   - Quantity per item
   - Batch number (if any)
   - Expiry date (if any, with "expiring soon" highlight)

### 5.2 Fix: Hover Tooltip (Medium Priority)

Add a `mousemove` handler to the canvas that:
1. Runs `hitTest()` on mouse position
2. If a bin is hit, shows a lightweight floating tooltip with: bin code + fill %
3. Changes cursor to `pointer` when hovering over a bin
4. Hides tooltip when not hovering any bin

```typescript
const handleMouseMoveHover = (e: React.MouseEvent<HTMLCanvasElement>) => {
  if (dragRef.current) return; // don't tooltip while dragging
  const rect = e.currentTarget.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const hit = hitTest(mx, my, sorted, offset.x, offset.y, TW, TH, ZH);
  setHoveredBin(hit);
  e.currentTarget.style.cursor = hit ? 'pointer' : 'grab';
};
```

### 5.3 Fix: Update Implementation Doc (Low Priority)

Update Section 6.1 of the design document to reflect that the implementation uses native HTML5 Canvas with isometric projection rather than React Three Fiber. The canvas approach is lighter and performs well for the current use case.

---

## 6. Summary Table

| # | Issue | Severity | Status | Fix Complexity |
|---|---|---|---|---|
| 1 | No item details on bin click | **High** | Not implemented | ~2-3 hours (BE endpoint + FE panel update) |
| 2 | No hover tooltip | Medium | Not implemented | ~1 hour (mousemove + tooltip component) |
| 3 | Expiry dates not shown in detail | Medium | Not implemented | Included in fix #1 |
| 4 | WebSocket not fully wired | Low | Phase 3 (planned) | ~1 day |
| 5 | Design doc says React Three Fiber, impl uses Canvas | Low | Documentation drift | ~10 min doc update |

---

*Analysis performed: June 17, 2026*
