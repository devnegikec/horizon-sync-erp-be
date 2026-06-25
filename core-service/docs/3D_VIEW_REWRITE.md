# 3D Warehouse View & Layout System — Complete Documentation

> **Last updated:** 2026-06-17  
> **Scope:** 3D View, Layout Designer, Location Tree, Aisle Corridor Model, Worker Management, and all related changes  
> **Reference project:** `warehouse-digital-twin-`

---

## Table of Contents

1. [Warehouse Hierarchy Model](#1-warehouse-hierarchy-model)
2. [Layout Designer](#2-layout-designer)
3. [3D View](#3-3d-view)
4. [Location Tree](#4-location-tree)
5. [Worker Management](#5-worker-management)
6. [UI Reorganization](#6-ui-reorganization)
7. [API Reference](#7-api-reference)
8. [Bug Fixes & Performance](#8-bug-fixes--performance)
9. [Files Modified](#9-files-modified)

---

## 1. Warehouse Hierarchy Model

### Corridor-Based Aisle Design

```
Zone (e.g. "Fast Movers")
  └── Aisle (corridor with a driving lane between racks)
        ├── Bay L (Left Row — rack on left side of corridor)
        │     ├── Level 1
        │     │     ├── Bin 01  (depth position 1)
        │     │     ├── Bin 02  (depth position 2)
        │     │     └── ...
        │     ├── Level 2
        │     └── Level N
        │
        └── Bay R (Right Row — rack on right side of corridor)
              ├── Level 1
              │     ├── Bin 01
              │     └── ...
              └── Level N
```

### Key Rules

| Rule | Detail |
|---|---|
| Max bays per aisle | **2** (Left Row + Right Row). Never more. |
| Edge aisles | Auto-detected: first aisle → `right_only`, last → `left_only`. User can override. |
| Levels | Stack vertically (Z direction) with configurable `level_height` |
| Bins per level | Multiple slots along the aisle depth (configurable `num_bays_per_row`) |
| Direction | `horizontal` (runs left-to-right) or `vertical` (runs front-to-back) |

### Position Calculation

```
Aisle center:
  horizontal: x = zone.offset_x + position_start, y = zone.offset_y + aisleIndex * aisle_spacing
  vertical:   x = zone.offset_x + aisleIndex * aisle_spacing, y = zone.offset_y + position_start

Bay offset (perpendicular to aisle):
  Left Bay:  offset = -corridor_width / 2
  Right Bay: offset = +corridor_width / 2

Levels: z = levelIndex * level_height

Bins (along aisle depth):
  horizontal: bin_x = bay_x + binDepthIndex * bay_depth
  vertical:   bin_y = bay_y + binDepthIndex * bay_depth
```

### Data Schema (AisleSpec)

| Field | Type | Default | Description |
|---|---|---|---|
| `code` | string | — | Aisle identifier (e.g. "A01") |
| `name` | string | "New Aisle" | Human-readable name |
| `direction` | "horizontal" / "vertical" | "horizontal" | Which axis the aisle runs along |
| `position_along` | float | 0 | Offset perpendicular to aisle direction |
| `position_start` | float | 0 | Offset along aisle direction from zone origin |
| `corridor_width` | float | 3.0 | Meters between left and right rack rows |
| `rows` | "both" / "left_only" / "right_only" | "both" | Which rack rows to create |
| `num_levels` | int | 5 | Rack height (vertical levels) |
| `level_height` | float | 1.4 | Meters between levels |
| `bins_per_level` | int | 1 | Bin slots per level per depth position |
| `bin_capacity` | float | 100 | Storage capacity per bin |
| `num_bays_per_row` | int | 10 | Bin depth positions along the aisle |
| `bay_depth` | float | 1.8 | Meters between depth positions |

### Data Schema (ZoneSpec)

| Field | Type | Default | Description |
|---|---|---|---|
| `code` | string | — | Zone identifier (e.g. "A") |
| `name` | string | null | Zone name (e.g. "Fast Movers") |
| `offset_x` | float | 0 | Distance from left wall (meters) |
| `offset_y` | float | 0 | Distance from front wall (meters) |
| `aisle_spacing` | float | 6.5 | Meters between aisle centers |
| `aisles` | AisleSpec[] | — | Aisles in this zone |

---

## 2. Layout Designer

### Two-Step Flow

**Step 1 — Landing Screen:**
- Active layout summary (if one exists) with "Edit" button
- Template cards (4 preloaded corridor layouts) — click to start
- Saved layouts list with Edit/Delete
- "Start from Scratch" button
- "Reset Warehouse Layout" button (deletes everything for fresh start)

**Step 2 — Editor (only after choosing what to work on):**
- "← Back" button to return to landing
- Zone/aisle configuration form with user-friendly labels
- Preview + Apply/Update actions

### User-Friendly Labels

| Technical field | UI label |
|---|---|
| `offset_x` | Distance from left wall (m) |
| `offset_y` | Distance from front wall (m) |
| `aisle_spacing` | Spacing between aisles (m) |
| `corridor_width` | Corridor width (m) |
| `num_bays_per_row` | Bin slots along depth |
| `bay_depth` | Slot spacing (m) |
| `num_levels` | Rack height (levels) |
| `level_height` | Level height (m) |
| `direction` | Aisle Direction (Horizontal/Vertical) |
| `rows` | Rack Rows (Both sides / Left only / Right only) |

### Smart Auto-Fill

**Adding an aisle:**
- Copies ALL settings from the previous aisle in the zone
- Auto-names: "Aisle 2", "Aisle 3", etc.
- Auto-sets `rows: 'left_only'` for new last aisle (edge detection)

**Adding a zone:**
- Copies `aisle_spacing` from previous zone
- Calculates `offset_y` based on previous zone's actual depth extent
- Copies entire aisle configuration from previous zone
- Auto-names: "Zone B", "Zone C", etc.

### Number Input Fix
- Fields accept empty/backspace (local string state)
- Only updates parent on valid number input
- Resets to min/0 on blur if empty

### Permission Gating
- Layout Designer tab: visible only to `warehouse.manage` or `*.*`
- Other users see only Location Tree + 3D View

### Tab Order
1. Layout Designer (admin only)
2. Location Tree (all)
3. 3D View (all)

---

## 3. 3D View

### Technology
- React Three Fiber v9 + drei v10 + Three.js v0.184
- GPU-instanced bins (1000+ at 60fps)
- OrbitControls for smooth 360° rotation

### Visual Elements

| Element | Implementation |
|---|---|
| Rack frames | Steel uprights + beams per aisle (dynamic from data) |
| Bins | `instancedMesh` with per-instance color |
| Floor | Dark plane (`#0f172a`) + Grid overlay |
| Walls | Colored boundary strips with direction labels |
| Lighting | Ambient + 2× directional + point light with shadows |

### Wall Direction Indicators

| Wall | Color | Layout Designer Reference |
|---|---|---|
| Front (Z-min) | Blue | `offset_y = 0` direction |
| Back (Z-max) | Orange | Far Y edge |
| Left (X-min) | Green | `offset_x = 0` direction |
| Right (X-max) | Purple | Far X edge |

Each wall has a floating label that always faces the camera.

### Hover Tooltip
- Uses `onPointerOver` + `onPointerMove` + `onPointerOut` for reliable detection
- Dark themed tooltip showing: bin code, fill %, items, zone/aisle/bay/level, status
- Blue highlight on hovered bin

### Selected Bin
- Amber pulsing glow effect
- Opens BinDetailPanel with stock items (name, SKU, qty, batch, expiry)

### Filter Overlay (top-left)
- All Bins / In Stock / Low Stock / Expiring / Empty / Reserved
- Non-matching bins dimmed to near-invisible

### Status Colors

| Status | Color | Condition |
|---|---|---|
| In Stock (0-30%) | Green `#10b981` | Low fill percentage |
| Moderate (31-70%) | Amber `#f59e0b` | Medium fill |
| Expiring | Red `#ef4444` | Has items expiring within 30 days |
| Empty | Slate `#475569` | 0% fill |
| Reserved | Blue `#3b82f6` | Currently reserved by a worker |
| Suggested | Amber `#f59e0b` | Highlighted by suggestion engine |

### WebSocket
- **Disabled** (will re-enable with future requirements)
- Status polling every 5 seconds remains active

---

## 4. Location Tree

### Hover Tooltip
Native browser tooltip on each row showing:
- Location type (ZONE/AISLE/BAY/LEVEL/BIN)
- Name and full path
- Derived capacity (used / total, % used)
- Available capacity
- Active/Inactive status

### Decreasing Font Sizes

| Depth | Type | Size |
|---|---|---|
| 0 | Zone | `text-sm` + semibold |
| 1 | Aisle | `text-sm` |
| 2 | Bay | `13px` |
| 3 | Level | `text-xs` (12px) |
| 4+ | Bin | `11px` |

### Active-Only Filtering
- Only `is_active = true` locations shown
- Deleted/replaced layouts never appear

---

## 5. Worker Management

### Role-Based Access

| Permission | Can do |
|---|---|
| `warehouse.manage` (Owner/Admin/WMS Admin) | Create, edit, delete workers; import/export; regenerate QR |
| `warehouse.read` (WMS Manager) | View workers; print QR codes (single + batch) |
| Others | View-only (no action buttons) |

### QR Code Content
- Encodes full login URL: `https://<apiHost>/api/v1/wms-workers/login/qr?code=WRK-XXXX`
- When scanned, phone opens URL → backend returns JWT token
- Print label shows "Scan to Login" with barcode ID below

### Worker Login Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/wms-workers/login/qr?code=XXX` | GET | QR scan (phone opens URL) |
| `/wms-workers/login/credentials` | POST | Username/password fallback |
| `/wms-workers/login/barcode` | POST | Legacy barcode login (JSON body) |

### Token Configuration
- TTL: `WMS_WORKER_TOKEN_EXPIRE_HOURS` env var (default: 20 hours)
- Claims: `token_use: "wms_worker"`, `client_type: "mobile"`, `warehouse_id`, `role`, `permissions`

### Workers Table (DataTable)
- Matches Customers table pattern (DataTable + columns + row action dropdowns)
- Columns: Worker (avatar+name+code), Contact, Username, Role, QR Code, Status, Actions
- GPU pagination, sorting, search, column visibility

---

## 6. UI Reorganization

### Sidebar Changes
- Removed "WMS" tab from Inventory module
- WMS accessed via dedicated sidebar entry

### Layout Tab Structure
- Moved 3D View INTO Layout tab (was standalone)
- Sub-tabs: Layout Designer | Location Tree | 3D View

### Revenue
- Payments tab hidden (will re-enable later)

---

## 7. API Reference

### Floor Plans

| Method | Path | Description |
|---|---|---|
| POST | `/floor-plans/preview` | Dry-run (no DB writes) |
| POST | `/floor-plans/apply` | Generate locations + save plan |
| GET | `/floor-plans?warehouse_id=` | List plans |
| GET | `/floor-plans/{id}` | Get single plan |
| PUT | `/floor-plans/{id}` | Update + regenerate |
| DELETE | `/floor-plans/{id}` | Soft-delete plan |
| POST | `/floor-plans/seed-templates` | Seed preloaded templates |
| POST | `/floor-plans/reset?warehouse_id=` | **Delete ALL** plans + locations (fresh start) |

### 3D View

| Method | Path | Description |
|---|---|---|
| GET | `/wms-3d/layout?warehouse_id=` | Full 3D geometry tree |
| GET | `/wms-3d/status?warehouse_id=` | Live bin fill/reservations |
| GET | `/wms-3d/bin/{bin_id}/stock` | Item details for a bin |
| POST | `/wms-3d/suggest` | Ranked bin suggestions |
| POST | `/wms-3d/reserve` | Reserve a bin (TTL) |
| POST | `/wms-3d/release` | Release reservation |

### Workers

| Method | Path | Description |
|---|---|---|
| POST | `/wms-workers` | Create worker (warehouse.manage required) |
| GET | `/wms-workers` | List workers |
| GET | `/wms-workers/login/qr?code=` | QR scan login |
| POST | `/wms-workers/login/credentials` | Username/password login |
| POST | `/wms-workers/login/barcode` | Barcode login |

---

## 8. Bug Fixes & Performance

### Floor Plan Apply (409 Conflict)
- **Cause:** `UNIQUE(warehouse_id, full_path)` violated when re-applying
- **Fix:** Hard-delete stockless locations; rename `full_path` for stock locations
- **Also:** `bins_per_level=1` no longer creates duplicate codes (always appends `-01`)

### Performance (Slow Apply/Update)
- **Cause:** Per-row Python loop with individual `db.delete()` calls
- **Fix:** Bulk SQL operations: single `COUNT`, single stock check query, bulk `UPDATE`, bulk `DELETE`

### CORS/ngrok Issues
- **Cause:** axios explicit headers overriding `defaults.headers.common`
- **Fix:** Added `axios.interceptors.request.use()` to inject ngrok header on every request

### Stock Entry CSV
- Removed "From Warehouse Code" column (caused parse errors)
- Sample auto-populated with real items from user's item list
- Warehouse code resolved from ID (was showing UUID)

### Suggestion Panel
- `bin_code` now shows `full_path or code` (was null → showed UUID)

### Invitation & Roles
- WMS Manager no longer sees all warehouses (removed `warehouse.manage` from global access check)
- Invited user role shows correctly (was hardcoded as "regular")
- User detail dialog shows assigned warehouse info

---

## 9. Files Modified

### Backend (core-service)

| File | Purpose |
|---|---|
| `app/config.py` | Added `wms_worker_token_expire_hours` |
| `app/schemas/floor_plan.py` | New corridor model (AisleSpec + ZoneSpec) |
| `app/schemas/wms_3d.py` | Added `BinStockItem`, `BinStockDetailResponse` |
| `app/schemas/wms_worker.py` | Added `CredentialsLoginRequest` |
| `app/services/floor_plan_generator_service.py` | Corridor generation, bulk operations, templates, reset |
| `app/services/warehouse_3d_service.py` | `get_bin_stock_detail()`, active-only filter |
| `app/services/location_suggestion_service.py` | `bin_code` fallback fix |
| `app/services/layout_service.py` | Active-only tree filter |
| `app/services/wms_worker_service.py` | `authenticate_by_credentials()` |
| `app/api/v1/endpoints/floor_plans.py` | PUT, DELETE, seed-templates, reset |
| `app/api/v1/endpoints/wms_3d.py` | `GET /bin/{id}/stock` |
| `app/api/v1/endpoints/wms_workers.py` | `GET /login/qr`, `POST /login/credentials` |
| `app/api/v1/endpoints/warehouse_users.py` | Fixed global access check |
| `app/api/v1/endpoints/warehouses.py` | Seeds templates on creation |

### Frontend (horizon-sync)

| File | Purpose |
|---|---|
| `components/wms/Warehouse3DView.tsx` | Full 3D view (R3F + walls + instanced bins) |
| `components/wms/WarehouseLayoutDesigner.tsx` | Two-step flow, user-friendly labels, smart auto-fill |
| `components/wms/LocationTreeView.tsx` | Hover tooltip, decreasing font sizes |
| `components/wms/WMSManagement.tsx` | Tab reorder, permission gate, 3D in Layout tab |
| `components/wms/WorkerColumns.tsx` | DataTable column definitions |
| `components/wms/WorkersTable.tsx` | DataTable wrapper |
| `components/wms/WorkersManagementPanel.tsx` | Role-based UI, QR login URL, DataTable |
| `components/stock/StockEntryDialog.tsx` | Dynamic CSV sample |
| `utility/stockEntryCsvParser.ts` | Removed From Warehouse column |
| `utility/api/floorplan.ts` | update, delete, reset methods |
| `utility/api/wms3d.ts` | `getBinStock()` |
| `types/floorplan.types.ts` | New corridor schema + templates |
| `types/wms3d.types.ts` | `BinStockItem`, `BinStockDetailResponse` |
| `hooks/useWarehouse3D.ts` | WebSocket disabled |
| `app.tsx` | Removed WMS tab from Inventory |
| `pages/RevenuePage.tsx` | Hidden Payments |
| `ngrok-headers.ts` | axios interceptor |
| `package.json` | Three.js v0.184, R3F v9, drei v10 |

### Platform

| File | Purpose |
|---|---|
| `hooks/useUsers.ts` | Fixed invitation role mapping |
| `types/user.types.ts` | Added `extra_data` |
| `components/users/UserViewDialog.tsx` | Warehouse assignment display |
| `components/users/UsersTable.tsx` | Removed warehouses column |
| `components/InviteUserModal.tsx` | WMS Operator in SCOPED roles |

---

## Preloaded Templates

| Template | Zones | Aisles | Levels | Bins | Use Case |
|---|---|---|---|---|---|
| Small Warehouse | 1 | 2 (corridor) | 5 | 100 | Small stockroom |
| Medium Warehouse | 2 | 4 (corridors) | 3-5 | 400 | Standard distribution |
| Large Warehouse | 3 | 6 (corridors) | 4-6 | 900 | High-density racking |
| Cross-Dock Facility | 2 | 4 (corridors) | 3 | 240 | Transit hub |

All templates use the corridor model with edge aisles auto-set to single-sided.

---

*Document updated: June 17, 2026*
