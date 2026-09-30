# Capacity Calculation Fixes — Deployment Log

> Purpose: a single record of every capacity-related code/data change made so the
> changes can be reviewed and deployed to production in one pass.
> Date: 2026-09-21
> Scope: `core-service` (FastAPI + SQLAlchemy + PostgreSQL)

---

## 0. TL;DR — what was wrong and what changed

The WMS had **two disconnected capacity systems** (count vs volume) that disagreed
with each other, plus several data-quality gaps. This log covers:

1. Phantom "% filled" from inactive bins counted as "used" (`layout_service`).
2. Volume capacity leaking from **inactive** bins (`bin_capacity_service`).
3. Master-pack count always `0` and MC volume never applied for serialized stock
   (`capacity_math` + `put_away_service`).
4. `max_volume_cc` / `max_weight_grams` not exposed via the API, so bin volume
   capacity could never be configured (`warehouse_location` schemas/service/endpoint).
5. MC estimation fields (fill factor / void fill / wall thickness) not persisted or
   returned (`item_packaging_unit` model/schema/service + migration 120).
6. Orphaned stock in inactive bins + duplicate warehouse rows (remediation scripts).

---

## 1. Code fixes (no schema change — deploy via code only)

### FIX-1 — Count summary no longer counts inactive bins
- **File:** `core-service/app/services/layout_service.py` → `get_location_summary`
- **Before:** `used_capacity`, `occupied_bins`, `distinct_items` summed stock across
  **all** descendant bins; `total_capacity` summed **active** bins only → phantom
  utilization (e.g. "0.01% filled" while the Location Tree was empty).
- **After:** all five metrics use a single `active_bin_ids` set
  (`location_type='bin'` AND `is_active=true`), so used and total measure the same bins.
- **Affects:** `GET /warehouse-locations/{id}/summary` (dashboard count card).

### FIX-2 — Capacity tree / 3-D view / refresh exclude inactive bins
- **File:** `core-service/app/services/bin_capacity_service.py`
  - `get_capacity_tree` → `locations` query now filters `is_active = true`.
  - `get_bin_states` → bins query now filters `is_active = true`.
  - `refresh_warehouse` → bins query now filters `is_active = true`.
- **Before:** `get_capacity_tree` computed `volume.capacity_m3` / `count_capacity`
  from **active + inactive** bins (occupancy was already active-only), so
  deactivated bins' `max_volume_cc` leaked into the warehouse total (e.g. a false
  "210.00 m³" for EcityTTK).
- **After:** capacity and occupancy both derive from **active** bins only.
- **Affects:** `GET /capacity/warehouses/{id}/tree`, 3-D view, capacity refresh.

### FIX-3 — Master-pack count + MC volume for serialized stock
- **Files:**
  - `core-service/app/services/capacity_math.py` → `_iter_bin_stock_rows`
  - `core-service/app/services/put_away_service.py` → `complete_item`
- **Before:** serialized master-pack stock was stored as **one bin-stock row per
  serial** (`quantity_on_hand=1`) with no `packaging_unit_id`. The `floor(qty/c)`
  math ran per row → `1 // 4 = 0` → `master_pack_count = 0` and MC outer volume
  never applied (each phone counted as base "Each" volume).
- **After:**
  - `_iter_bin_stock_rows` now **aggregates** `quantity_on_hand` per
    `(bin, item, packaging_unit)` before the `floor(qty/c)` math, and falls back to
    the item's active master-pack unit (`conversion_factor > 1`) when a row has no
    explicit `packaging_unit_id`.
  - `complete_item` now passes `packaging_unit_id` to `add_stock` in the serialized
    branch (previously only the non-serialized branch did).
- **Verified (live DB):** a bin with 6 master packs of IPH-17/IPH-18 reported
  `unit_count=24, master_pack_count=0` before; after the fix `master_pack_count=6`
  and MC weight `7.2 kg`.

### FIX-4 — Expose `max_volume_cc` / `max_weight_grams` on the location API
- **Files:**
  - `core-service/app/schemas/warehouse_location.py`
  - `core-service/app/services/layout_service.py` (`create_location`, `update_location`)
  - `core-service/app/api/v1/endpoints/warehouse_locations.py`
- **Before:** the columns existed in the model but were absent from
  `CreateLocationRequest`, `UpdateLocationRequest`, `LocationResponse`, and
  `LocationTree` → no way to set a bin's volume/weight capacity from the UI/API.
- **After:** both fields are accepted on create/update and returned on read. When a
  bin's limit changes, `update_location` re-runs `BinCapacityService.refresh_bin`
  so the dashboard state updates immediately.
- **Affects:** `POST /warehouse-locations`, `PATCH /warehouse-locations/{id}`,
  `GET /warehouse-locations`, `GET /warehouse-locations/tree/{warehouse_id}`.

### FIX-5 — Persist + return MC estimation knobs
- **Files:**
  - `core-service/app/models/item_packaging_unit.py` (3 new columns)
  - `core-service/app/schemas/item_packaging_unit.py` (Create/Update/Response)
  - `core-service/app/services/item_service.py` → `_upsert_master_pack_unit`
  - `core-service/app/services/item_packaging_unit_service.py` → `create_packaging_unit`
  - `core-service/alembic/versions/120_add_master_carton_estimation_fields.py`
- **Before:** `master_pack_fill_factor`, `master_pack_void_fill_pct`,
  `master_pack_wall_thickness_mm` were used transiently to *estimate* MC dims and
  then discarded — the item GET response and the UI showed null/"—".
- **After:** values are persisted on the MC packaging-unit row (defaults `0.75` /
  `0.10` / `3`) and returned in `ItemPackagingUnitResponse`. Migration 120 adds the
  columns and backfills existing non-base rows with the defaults.
- **Requires migration:** `alembic upgrade head` (revision 120).

---

## 2. Migration

| Revision | File | Purpose |
|---|---|---|
| `120_add_master_carton_estimation_fields` | `core-service/alembic/versions/120_add_master_carton_estimation_fields.py` | Add `master_pack_fill_factor`, `master_pack_void_fill_pct`, `master_pack_wall_thickness_mm` to `item_packaging_units` + backfill defaults on non-base rows |

> All other fixes (FIX-1…FIX-4) are pure code — no new columns, no migration.
> `max_volume_cc` / `max_weight_grams` already existed from revision
> `072_add_bin_capacity_columns`.

---

## 3. Data remediation (one-off scripts, run against the target DB)

| Script | Purpose | Command |
|---|---|---|
| `cleanup_capacity_discrepancies.py` | Report orphaned stock / missing limits / missing packaging units; `--zero-orphaned-stock` zeroes stock left in inactive/non-bin locations and reconciles `stock_levels`. | `python cleanup_capacity_discrepancies.py` / `--zero-orphaned-stock` |
| `merge_duplicate_warehouses.py` | Merge the duplicate "Mother Warehouse" stub into the canonical row (deactivate empty stub locations, repoint users, trim trailing-space name, deactivate stub). | `python merge_duplicate_warehouses.py` / `--apply` |
| `backfill_bin_volume_capacity.py` | Set `max_volume_cc` on active bins (default 1 m³/bin) so the dashboard Volume populates. `--factor` derives from `capacity`. | `python backfill_bin_volume_capacity.py --warehouse "Mother Warehouse" --apply` |

> These scripts are **dry-run by default**; they only write with an explicit flag.

---

## 4. Deployment checklist

1. Run migration: `alembic upgrade head` (applies revision 120).
2. Deploy code (FIX-1…FIX-5).
3. Restart `core-service`.
4. Data remediation (as applicable, review dry-runs first):
   - `merge_duplicate_warehouses.py --apply` (if duplicate warehouses exist).
   - `cleanup_capacity_discrepancies.py --zero-orphaned-stock` (if orphaned stock in inactive bins).
   - `backfill_bin_volume_capacity.py --apply` (to set `max_volume_cc` on active bins).
5. Correct MC outer dims/weights on items (IPH-17/IPH-18 "Master Pack" rows had
   `10×12×12 mm` — a data typo; enter real carton dimensions).

---

## 5. Verification

- `GET /capacity/warehouses/{id}/tree`:
  - `count_capacity` and `volume.capacity_m3` reflect **active bins only**.
  - `master_pack_count` reflects full master cartons (`floor(total_qty / c)`).
  - `volume` block is non-empty once a bin has `max_volume_cc`.
- `GET /warehouse-locations/{id}/summary`: `used_capacity` no longer includes
  inactive-bin stock (no phantom %).
- Item GET returns `master_pack_fill_factor` / `master_pack_void_fill_pct` /
  `master_pack_wall_thickness_mm` on MC packaging units.
- `PATCH /warehouse-locations/{id}` accepts `max_volume_cc` / `max_weight_grams`.

---

## 6. Known remaining items (not yet addressed)

1. **Serialized stock is still stored per-serial** (`qty=1` per row). FIX-3 makes
   capacity math correct by aggregation + MC fallback, but serial traceability and
   MC identity are not yet carried as an explicit `packaging_unit_id` from the QR
   scan (`packaging_unit_qr_id`) — a separate receiving-scan wiring gap.
2. **MC outer dims** for some items are mis-entered (e.g. `10×12×12 mm`) — data fix.
3. **`_find_best_bin` volumetric SQL** (bin assignment) still computes *occupied*
   volume with the old `qty × dims` formula; only the incoming *required* volume is
   MC-aware.
