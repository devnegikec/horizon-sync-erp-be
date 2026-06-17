# WMS Layout — Feature Guide

> **Scope:** Layout tab in the WMS module — covers Location Tree, Layout Designer, and their relationship  
> **Last updated:** 2026-06-17

---

## Overview

The **Layout** tab in WMS has two sub-tabs:

| Sub-tab | Role |
|---|---|
| **Location Tree** | Read-only view of the warehouse's physical location hierarchy |
| **Layout Designer** | Form-based tool to define and apply warehouse layouts |

They are two sides of the same coin. The Layout Designer is the **input** — you use it to describe your warehouse structure. The Location Tree is the **output** — it shows what was actually created in the database.

---

## How They Relate

```
Layout Designer
  (configure zones / aisles / bays / levels / bins)
          │
          │  Click "Apply Layout"
          ▼
FloorPlanGeneratorService
  (generates WarehouseLocation rows with 3D positions)
          │
          ▼
Database: warehouse_locations table
  (Zone → Aisle → Bay → Level → Bin)
          │
          ▼
Location Tree                    3D View
  (expandable hierarchy,         (isometric canvas,
   capacity rollups)              bin colors, hover/click)
```

A single "Apply" action creates all the `warehouse_locations` rows that both the Location Tree and the 3D View read from.

---

## Location Tree

### What It Shows

An expandable, hierarchical table of every location in the warehouse — from the top-level zone down to individual bins.

```
Zone A — Main Storage
  └── Aisle A01
        └── Bay B01
              ├── Level L1
              │     └── Bin WH1-A-A01-B01-L1
              ├── Level L2
              │     └── Bin WH1-A-A01-B01-L2
              └── Level L3
                    └── Bin WH1-A-A01-B01-L3
```

### Columns

| Column | Description |
|---|---|
| Type / Code | Location type badge (Zone/Aisle/Bay/Level/Bin) + location code |
| Name | Human-readable name (optional) |
| Full Path | Fully qualified path (e.g. `WH1-A-A01-B01-L1`) |
| Own Capacity | Capacity defined directly on this node (only bins have capacity) |
| Derived Capacity | Rolled-up capacity from all children — a zone shows the sum of all its bins |
| Available | Remaining capacity, color-coded: green (>30%), yellow (10–30%), red (<10%) |
| Status | Active (green) or Inactive (grey — soft-deleted by a layout replacement) |

### Derived Capacity

The tree computes capacity bottom-up:
- **Bin** → uses its own `total_capacity` value
- **Level** → sum of its bins
- **Bay** → sum of its levels
- **Aisle** → sum of its bays
- **Zone** → sum of its aisles

This lets managers see at a glance how full each zone or aisle is, not just individual bins.

### Key Behaviors

- Only **active** locations are shown (`is_active = true`). Deactivated locations from old layouts are never visible.
- Starts fully expanded on first load.
- **Expand All / Collapse All** buttons in the toolbar.
- Automatically refreshes after a layout is applied or updated in the Layout Designer.
- Read-only — no editing from this view.

### When to Use

- After applying a layout, to verify the hierarchy looks correct
- To check capacity rollups (how full is Zone A?)
- To find a specific bin's full path or code
- To confirm a location is active before scanning

---

## Layout Designer

### What It Does

Lets warehouse managers define a complete zone/aisle/bay/level/bin hierarchy through a form UI. On apply, the system **auto-generates** all `warehouse_locations` rows with correct 3D positions (x, y, z) in one transaction.

### Configuration Model

```
FloorPlanConfig
  └── grid_unit (scale factor, display only)
  └── zones[]
        └── ZoneSpec
              ├── code (e.g. "A")
              ├── name (e.g. "Fast Movers")
              ├── grid_x / grid_y (world position offset)
              └── aisles[]
                    └── AisleSpec
                          ├── code (e.g. "A01")
                          ├── orientation: "x" or "y"
                          ├── num_bays
                          ├── bay_spacing
                          ├── num_levels
                          ├── bins_per_level
                          └── bin_capacity
```

### Position Calculation

The generator computes 3D coordinates so bins appear in the correct place in the 3D View:

| Element | X | Y | Z |
|---|---|---|---|
| Zone | `grid_x` | `grid_y` | 0 |
| Aisle | zone X + `aisle.grid_x` | zone Y + `aisle.grid_y` | 0 |
| Bay (X-orientation) | aisle X + `bay_index × bay_spacing` | aisle Y | 0 |
| Bay (Y-orientation) | aisle X | aisle Y + `bay_index × bay_spacing` | 0 |
| Level | bay X | bay Y | `level_index × level_height` |
| Bin | level X + bin offset | level Y | level Z |

### Location Codes

Codes follow a predictable pattern:

```
Warehouse code: WH1
Zone:           WH1-A
Aisle:          WH1-A-A01
Bay:            WH1-A-A01-B01
Level:          WH1-A-A01-B01-L1
Bin:            WH1-A-A01-B01-L1     (when bins_per_level = 1)
                WH1-A-A01-B01-L1-01  (when bins_per_level > 1)
```

### Workflow

```
1. Choose a template (or start from scratch)
         │
2. Add / modify zones and aisles
         │
3. Click "Preview" — see counts + sample codes (no DB changes)
         │
4. Review summary (bins, aisles, zones, sample codes)
         │
5. Enter a plan name and click "Apply Layout"
         │
6. System deactivates all existing locations,
   generates new hierarchy, saves plan record
         │
7. Designer auto-switches to Location Tree — verify the result
```

### Single Active Layout Rule

Only **one layout is active at a time** per warehouse:
- When any layout is applied or updated, all existing locations are deactivated first
- The newly applied layout becomes the only active one
- Old layout records are kept for history but marked inactive
- The 3D View and Location Tree **only show active locations**

### Saved Layouts Panel

The designer shows all saved layout plans (active and inactive) in a panel at the top:

| Badge | Meaning |
|---|---|
| **Active** (green) | Currently applied — this is what the 3D View shows |
| **Template** (purple) | Pre-seeded template, never applied — ready to customize |
| (no badge) | Previously applied layout, now superseded |

Actions per saved layout:
- **Edit** — loads the config into the form for modification
- **Delete** — soft-deletes the plan and deactivates its locations

### Preloaded Templates

When a new warehouse is created, 4 starter templates are automatically seeded:

| Template | Zones | Aisles | Bins | Best for |
|---|---|---|---|---|
| Small Warehouse | 1 | 2 | 24 | Small stockrooms |
| Medium Warehouse | 2 (Fast Movers + Bulk) | 4 | 96 | Standard distribution |
| Large Warehouse | 3 (Picking + Reserve + Cold) | 6 | 216 | High-density racking |
| Cross-Dock Facility | 2 (Inbound + Outbound) | 4 | 48 | Transit hubs |

Templates appear with a purple "Template" badge. Click **Edit** to load one, customize it, then **Apply Layout** to activate it.

For warehouses created before templates were introduced, use:
```
POST /api/v1/floor-plans/seed-templates?warehouse_id={id}
```

---

## Data Flow Summary

```
User action                    What happens in DB
─────────────────────────────────────────────────────────────────────
Click "Preview"              → No DB writes. Returns counts + sample codes.

Click "Apply Layout"         → 1. All existing warehouse_locations marked is_active=false
(new layout)                    2. All existing floor_plans marked is_active=false
                                3. New warehouse_locations created (Zone/Aisle/Bay/Level/Bin)
                                4. New warehouse_floor_plans record saved (is_active=true)
                                5. Location Tree refreshes → shows new hierarchy
                                6. 3D View refreshes → shows new bins

Click "Update Layout"        → Same as Apply, but the existing floor_plan record is
(editing saved layout)          updated in-place (same ID preserved)

Click "Delete" on a plan     → floor_plan.is_active = false
                                All warehouse_locations for that warehouse deactivated
```

---

## API Reference

### Floor Plan Endpoints (`/api/v1/floor-plans`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/preview` | Dry-run: compute counts without writing to DB |
| `POST` | `/apply` | Generate locations + save floor plan record |
| `GET` | `/` | List all floor plans for a warehouse |
| `GET` | `/{id}` | Get a specific floor plan |
| `PUT` | `/{id}` | Update config + regenerate locations |
| `DELETE` | `/{id}` | Soft-delete plan + deactivate locations |
| `POST` | `/seed-templates` | Seed preloaded templates for an existing warehouse |

### Location Tree Endpoint

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/wms/warehouse-locations/tree/{warehouse_id}` | Returns active locations as a nested tree |

---

## Key Files

### Backend

| File | Purpose |
|---|---|
| `app/services/floor_plan_generator_service.py` | Generates `WarehouseLocation` rows from config; enforces single active layout; seeds templates |
| `app/services/layout_service.py` | Builds the location tree (active locations only) |
| `app/schemas/floor_plan.py` | Pydantic schemas for all floor plan API requests/responses |
| `app/models/warehouse_floor_plan.py` | SQLAlchemy model for saved layout configs |
| `app/models/warehouse_location.py` | SQLAlchemy model for individual locations |
| `app/api/v1/endpoints/floor_plans.py` | FastAPI router for floor plan CRUD |
| `app/api/v1/endpoints/warehouse_locations.py` | FastAPI router including the tree endpoint |
| `app/api/v1/endpoints/warehouses.py` | Calls `seed_templates()` on new warehouse creation |

### Frontend

| File | Purpose |
|---|---|
| `components/wms/WarehouseLayoutDesigner.tsx` | Layout Designer UI (zones, aisles, templates, apply) |
| `components/wms/LocationTreeView.tsx` | Location Tree UI (expandable table with capacity rollups) |
| `components/wms/WMSManagement.tsx` | Wires the two sub-tabs; refreshes tree after layout changes |
| `types/floorplan.types.ts` | TypeScript types + `LAYOUT_TEMPLATES` presets |
| `utility/api/floorplan.ts` | API client for all floor plan endpoints |
| `hooks/useWMS.ts` | `useLocationTree` hook — fetches and caches the location hierarchy |

---

*Document created: June 17, 2026*
