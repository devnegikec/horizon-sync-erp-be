# Session Changes Log

> **Date:** 2026-06-17  
> **Scope:** WMS 3D View, Layout Designer, Worker Management, UI Reorganization, Bug Fixes

---

## 1. 3D Warehouse View — Analysis & Fixes

### Issues Identified
- No item details on bin click (only aggregate counts shown)
- No hover tooltip on bins
- No expiry dates in bin detail panel
- 3D rotation distortion (isometric canvas approach)

### Fixes Applied

**Backend — New endpoint `GET /api/v1/wms-3d/bin/{bin_id}/stock`:**
- Returns individual item records (name, code, SKU, quantity, UOM, batch, expiry)
- Ordered by expiry (FEFO) then arrival (FIFO)
- Schema: `BinStockDetailResponse` with `BinStockItem[]`

**Frontend — Enhanced `BinDetailPanel`:**
- Fetches stock details from new endpoint on bin click
- Shows each item with name, code, SKU, quantity, batch, expiry
- Items expiring within 30 days highlighted in orange

**Frontend — Hover tooltip:**
- Canvas `mousemove` hit-test shows floating tooltip (bin code, fill %, item count)
- Cursor changes to pointer when hovering a bin

**Frontend — Migration to React Three Fiber:**
- Replaced custom canvas isometric projection with proper 3D WebGL
- `OrbitControls` for smooth 360° rotation (left-drag), pan (right-drag), zoom (scroll)
- Every bin is a `<mesh>` with `onPointerOver` for consistent hover at any angle
- Pulse animation on reserved/suggested bins
- Fill-level visual indicator inside each bin cube
- Added `three`, `@react-three/fiber`, `@react-three/drei` to dependencies

---

## 2. Layout Designer — Management Features

### Single Active Layout Enforcement
- Only one layout is active at a time per warehouse
- Applying/updating any layout deactivates all others
- Removed "Deactivate existing locations" checkbox (now automatic)

### Saved Layouts Panel
- Shows all saved layouts (active, inactive, templates) with badges:
  - **Active** (green) — currently rendered in 3D View
  - **Template** (purple) — pre-seeded, never applied
- **Edit** button loads config into form for modification
- **Delete** button with confirmation — soft-deletes plan + deactivates locations
- **"New Layout"** button resets form

### Update/Delete API
- `PUT /api/v1/floor-plans/{id}` — update config + regenerate locations
- `DELETE /api/v1/floor-plans/{id}?deactivate_locations=true` — soft-delete

### Floor Plan Apply Fix (409 Conflict)
- Root cause: `UNIQUE(warehouse_id, full_path)` constraint violated when re-applying
- Fix: `_deactivate_existing()` now hard-deletes stockless locations; soft-deletes + renames locations with stock
- Also fixed: `bins_per_level=1` generated duplicate `full_path` (bin code = level code) — now always appends `-01`

### `full_path` Population
- `FloorPlanGeneratorService._make_loc()` now sets `full_path = code` on all generated locations

---

## 3. Preloaded Layout Templates

### Templates Seeded on Warehouse Creation
- 4 templates auto-seeded when a new warehouse is created:
  - Small Warehouse (1 zone, 2 aisles, 24 bins)
  - Medium Warehouse (2 zones, 4 aisles, 96 bins)
  - Large Warehouse (3 zones, 6 aisles, 216 bins)
  - Cross-Dock Facility (2 zones, 4 aisles, 48 bins)
- Saved as inactive floor plans (`is_active=false`, `generated_at=null`)
- Idempotent — calling seed multiple times doesn't duplicate

### Seed Endpoint for Existing Warehouses
- `POST /api/v1/floor-plans/seed-templates?warehouse_id={id}`

### Frontend Templates
- Also available as client-side presets in `LAYOUT_TEMPLATES` constant
- Shown in Layout Designer when no saved layouts exist (or as collapsible section)

---

## 4. Location Tree — Active-Only Filtering

- `LayoutService.get_tree()` now filters `is_active=True`
- `Warehouse3DService.get_layout()` now filters `is_active=True`
- Deleted/replaced locations never appear in tree or 3D view

---

## 5. UI Reorganization

### Sidebar Changes
- **Inventory module:** Removed "WMS" tab (Items, Warehouses, Item Groups, Stock, QSeal)
- **WMS module:** Removed "3D View" from sub-navigation bar

### 3D View Moved Into Layout
- Layout tab now has 3 sub-tabs: **Location Tree** | **Layout Designer** | **3D View**
- 3D View is logically grouped with layout tools

### Revenue — Payments Hidden
- "Payments" tab hidden from Revenue navigation for all users
- Code preserved (commented) for future re-enabling

---

## 6. Stock Entry CSV Sample Fix

- Removed "From Warehouse Code" column (caused parse errors for material_receipt)
- Sample CSV now populated with actual items from user's item list
- Warehouse code resolved from ID (was showing UUID instead of code)

---

## 7. Bin Suggestion — UUID Fix

- `LocationSuggestionService._build_suggestion()` now returns `bin_location.full_path or bin_location.code` instead of `full_path` alone (which was `None` for bins without it)
- Suggestions now show physical location paths (e.g., `WH1-A-A01-B01-L1-01`)

---

## 8. Barcode → QR Code Migration

- All user-facing text changed: "Barcode" → "QR Code" throughout worker management
- `buildCode128SVG()` (1D barcode) replaced with `buildQRCodeSVG()` (2D QR matrix)
- Removed `CODE128_PATTERNS` constant (no longer needed)
- Print labels now show QR code instead of barcode
- API field name `barcode` preserved (non-breaking)

---

## 9. Worker Management — DataTable Refactor

### New Files
- `WorkerColumns.tsx` — Column definitions matching Customer pattern
- `WorkersTable.tsx` — DataTable wrapper with sorting, pagination, row actions

### Table Features (matches Customers table)
- Serial numbers, sortable columns, search/filter, pagination (20/page)
- Row actions via dropdown menu (Edit, Print QR, Regenerate QR, Disable)
- TableSkeleton loading state, EmptyState for no workers
- ConfirmationDialog for destructive actions

---

## 10. Worker Creation — Role-Based Access

### Backend
- `POST /wms-workers` requires `warehouse.manage` permission (unchanged)

### Frontend
- Permission check: `warehouse.manage` or `*.*` required to see:
  - "Add Worker" button
  - "Import/Export" dropdown
  - Row actions: Edit, Delete, Regenerate QR
- `warehouse.read` (WMS Manager) can see:
  - "Print All QR Codes" button
  - "Print QR Code" per-worker action
  - View-only table access

---

## 11. Worker QR Code — Full Login URL

### QR Content Changed
- **Before:** `WRK-CA2E10D448FF` (just the ID)
- **After:** `https://<apiCoreUrl>/api/v1/wms-workers/login/qr?code=WRK-CA2E10D448FF`

### How It Works
1. Worker scans QR with phone camera
2. Phone opens the URL in browser
3. Backend authenticates worker, returns JWT token
4. Mobile client uses token for the shift session

### Print Label Updated
- Title: "Scan to Login" (was "Worker QR Code")
- QR encodes full URL
- Barcode ID shown below for manual reference

---

## 12. Worker Login Endpoints

### New Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/wms-workers/login/qr?code=XXX` | GET | QR scan login (phone opens URL directly) |
| `/wms-workers/login/credentials` | POST | Username/password fallback |
| `/wms-workers/login/barcode` | POST | Existing barcode login (JSON body) |

### Token Configuration
- TTL configurable via `WMS_WORKER_TOKEN_EXPIRE_HOURS` env var (default: 20 hours)
- All tokens include `client_type: "mobile"` claim
- Token payload: `sub`, `token_use`, `client_type`, `organization_id`, `warehouse_id`, `role`, `permissions`

### Credentials Login Schema
```json
POST /api/v1/wms-workers/login/credentials
{ "username": "johndoe", "password": "securePass123" }
```

---

## 13. Invitation & Warehouse Access Fixes

### Issue: WMS Manager Sees All Warehouses
- **Root cause:** `/my-warehouses` checked `warehouse.manage` permission for global access
- **Fix:** Removed `warehouse.manage` from `has_global_access` check — only `system_admin`, `organization_admin`, and `*.*` get all warehouses

### Issue: Invited User Role Shows as "Regular"
- **Root cause:** `useUsers.ts` hardcoded `user_type: 'regular'` for pending invitations
- **Fix:** Now uses `invitation.role_name` from API response; populates `roles` array

### Issue: User Details Don't Show Warehouse Assignments
- **Fix:** Added "Assigned Warehouses" section to `UserViewDialog` under "Assigned Roles"
- Shows warehouse IDs and warehouse role from `extra_data`
- Only visible for users with WMS warehouse assignments

---

## 14. CORS/ngrok Fixes

### Root Cause
- Services using axios with explicit `{ headers: {...} }` override `axios.defaults.headers.common`
- The `ngrok-skip-browser-warning` header from defaults never reached these requests

### Fix
- Added `axios.interceptors.request.use()` in `ngrok-headers.ts` — injects header on EVERY request regardless of explicit headers
- Also added header directly to affected services: `brandService.ts`, `qrBlockService.ts`, `useQRCredits.ts`

---

## 15. Miscellaneous Fixes

- `QSealProductDialog.tsx` — Fixed `icon: React.ElementType` → `React.ComponentType<{className?: string}>` (TS error with Three.js types)
- `WarehouseLayoutDesigner.tsx` — Default plan name changed from `''` to `'Initial layout v1'` (Apply button was disabled because placeholder text looked like a value)

---

## Files Modified (Summary)

### Backend (core-service)
| File | Changes |
|---|---|
| `app/config.py` | Added `wms_worker_token_expire_hours` setting |
| `app/api/v1/endpoints/wms_3d.py` | Added `GET /bin/{id}/stock` endpoint |
| `app/api/v1/endpoints/wms_workers.py` | Added `GET /login/qr`, `POST /login/credentials`; configurable TTL; `client_type` claim |
| `app/api/v1/endpoints/floor_plans.py` | Added `PUT /{id}`, `DELETE /{id}`, `POST /seed-templates` |
| `app/api/v1/endpoints/warehouse_users.py` | Fixed `has_global_access` check |
| `app/api/v1/endpoints/warehouses.py` | Calls `seed_templates()` on warehouse creation |
| `app/services/warehouse_3d_service.py` | Added `get_bin_stock_detail()`; filtered active-only |
| `app/services/floor_plan_generator_service.py` | Added `update()`, `delete()`, `seed_templates()`; fixed `full_path`; fixed bin code uniqueness |
| `app/services/location_suggestion_service.py` | Fixed `bin_code` fallback to `code` when `full_path` is None |
| `app/services/layout_service.py` | Filtered `is_active=True` in `get_tree()` |
| `app/services/wms_worker_service.py` | Added `authenticate_by_credentials()` |
| `app/schemas/wms_3d.py` | Added `BinStockItem`, `BinStockDetailResponse` |
| `app/schemas/floor_plan.py` | Added `FloorPlanUpdateRequest/Response`, `FloorPlanDeleteResponse` |
| `app/schemas/wms_worker.py` | Added `CredentialsLoginRequest` |

### Frontend (horizon-sync)
| File | Changes |
|---|---|
| `apps/inventory/src/app/components/wms/Warehouse3DView.tsx` | Rewritten with React Three Fiber |
| `apps/inventory/src/app/components/wms/WorkerColumns.tsx` | New — DataTable column definitions |
| `apps/inventory/src/app/components/wms/WorkersTable.tsx` | New — DataTable wrapper |
| `apps/inventory/src/app/components/wms/WorkersManagementPanel.tsx` | Role-based UI; QR login URL; DataTable integration |
| `apps/inventory/src/app/components/wms/WarehouseLayoutDesigner.tsx` | Saved layouts panel; templates; single-active enforcement |
| `apps/inventory/src/app/components/wms/WMSManagement.tsx` | Moved 3D View into Layout tab; removed from sub-nav |
| `apps/inventory/src/app/components/stock/StockEntryDialog.tsx` | Dynamic sample CSV with real items + warehouse code |
| `apps/inventory/src/app/utility/stockEntryCsvParser.ts` | Removed From Warehouse column; `buildStockEntrySampleCsv()` |
| `apps/inventory/src/app/utility/api/wms3d.ts` | Added `getBinStock()` |
| `apps/inventory/src/app/utility/api/floorplan.ts` | Added `update()`, `delete()` |
| `apps/inventory/src/app/types/wms3d.types.ts` | Added `BinStockItem`, `BinStockDetailResponse` |
| `apps/inventory/src/app/types/floorplan.types.ts` | Added update/delete types + `LAYOUT_TEMPLATES` |
| `apps/inventory/src/app/hooks/useWarehouse3D.ts` | Unchanged (reused by new 3D component) |
| `apps/inventory/src/app/app.tsx` | Removed WMS tab |
| `apps/inventory/src/app/pages/RevenuePage.tsx` | Hidden Payments tab |
| `apps/inventory/src/ngrok-headers.ts` | Added axios interceptor |
| `apps/platform/src/app/hooks/useUsers.ts` | Fixed invitation role mapping |
| `apps/platform/src/app/types/user.types.ts` | Added `extra_data` to User type |
| `apps/platform/src/app/components/users/UserViewDialog.tsx` | Added warehouse assignments display |
| `apps/platform/src/app/components/users/UsersTable.tsx` | No column added (reverted) |
| `apps/platform/src/app/components/sidebar.tsx` | Unchanged (WMS already in sidebar) |
| `package.json` | Added `three`, `@react-three/fiber`, `@react-three/drei` |

---

*Document created: June 17, 2026*
