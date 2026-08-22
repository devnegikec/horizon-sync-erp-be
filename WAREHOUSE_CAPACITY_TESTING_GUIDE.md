# Warehouse Capacity Feature — Manual End-to-End Testing Guide

> Feature: Bin Volume Capacity Service (`BIN_VOLUME_CAPACITY_SERVICE_DESIGN.md`)
> Date: 2026-08-14
> Backend: `horizon-sync-erp-be/core-service` · Frontend: `horizon-sync/apps/inventory`

This guide walks through **manual end-to-end testing** of the warehouse capacity feature — capacity computation, colour states, availability, config toggles, trigger points, suggestion wiring, and the dashboard UI.

---

## 0. Prerequisites

1. **Migration applied** (new columns):
   ```bash
   cd core-service
   python -m alembic upgrade head
   ```
2. **Core service running** (and identity service for auth):
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```
3. **Frontend** (inventory app) running: `nx serve inventory` (or the app's dev server).
4. **Auth token** for API calls (login → access token). Use it as `$TOKEN` in the examples below.
5. Optional: **Redis** running to observe real-time events (`docker run -p 6379:6379 redis:7-alpine`).

### Test data constants (used throughout)

| Entity                       | Value                                                                  | Effect                          |
| ---------------------------- | ---------------------------------------------------------------------- | ------------------------------- |
| Packaging unit (item "Each") | 100 × 100 × 100 mm, 200 g                                              | **0.001 m³ / 0.2 kg per unit**  |
| Bin `max_volume_cc`          | 100000 cc                                                              | **0.1 m³ = 100 units capacity** |
| Bin `max_weight_grams`       | 1000 g                                                                 | **1 kg capacity**               |
| Warehouse defaults           | `use_volume=true`, `use_weight=false`, `full=0.90`, `almost_full=0.70` | volume-only, 70/90 bands        |

> Quick math: `N units → N × 0.001 m³ → N% of a 0.1 m³ bin`.

### Helper env for curl examples

```bash
CORE=http://localhost:8001/api/v1
AUTH="Authorization: Bearer $TOKEN"
```

---

## 1. Setup (create test data)

```bash
# 1. Create item (via UI or API)
curl -X POST "$CORE/items" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"item_code":"SNOOKI-001","item_name":"Snooki Body Spray","item_type":"stock","uom":"Nos","maintain_stock":true}'
# → note ITEM_ID

# 2. Add packaging unit (base unit) for the item
curl -X POST "$CORE/items/$ITEM_ID/packaging-units" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"unit_name":"Each","conversion_factor":1,"length_mm":100,"width_mm":100,"height_mm":100,"weight_grams":200,"is_base_unit":true}'

# 3. Create/use a warehouse (note WAREHOUSE_ID) and set capacity settings
#    In DB or via admin: use_volume=true, use_weight=false,
#    full_threshold_pct=0.90, almost_full_threshold_pct=0.70

# 4. Create bins under the warehouse with max_volume_cc=100000 (0.1 m³)
curl -X POST "$CORE/warehouse-locations" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"warehouse_id":"<WAREHOUSE_ID>","location_type":"bin","code":"BIN-01","max_volume_cc":100000}'
# → note BIN_ID (repeat for BIN-02, BIN-03, BIN-04)
```

---

## 2. Capacity computation & colour states (backend)

### TC-01 — Empty bin reports "empty" and available

- **Preconditions:** `BIN-01` created, no stock.
- **Steps:** `GET /capacity/bins/{BIN_ID}`
- **Expected:** `binding_pct = 0`, `bin_state = "empty"`, `is_available = true`, `volume.pct = 0`.

### TC-02 — Volume % calculation

- **Steps:** Add 50 units to BIN-01 via `/bin-stock/add`.
- **Expected:** `volume.occupied_m3 ≈ 0.050`, `volume.capacity_m3 = 0.100`, `volume.pct = 50`, `binding_pct = 50`, `bin_state = "available"`.

### TC-03 — Four colour states

- **Steps:** Set stock in four bins and read `bin-state` from `/capacity/warehouses/{id}/bin-states`:
  - 0 units → `empty`
  - 50 units → `available`
  - 75 units → `almost_full`
  - 95 units → `full`
- **Expected:** states match exactly; `binding_pct` = 0 / 50 / 75 / 95.

### TC-04 — Weight excluded by default

- **Preconditions:** warehouse `use_weight=false` (default). Bin has `max_weight_grams=1000`.
- **Steps:** Add 2 units (each 200 g) and read bin capacity.
- **Expected:** `weight.capacity_kg = null`, `weight.pct = null`; `binding_pct` equals volume pct only.

### TC-05 — Weight included when enabled

- **Preconditions:** set warehouse `use_weight=true`, `max_volume_cc=null` (volume unconstrained).
- **Steps:** Add 2 units (400 g) to a bin with `max_weight_grams=1000`.
- **Expected:** `weight.pct = 40`, `binding_pct = 40`.

### TC-06 — Item without dimensions contributes zero

- **Steps:** Add stock for an item with no packaging unit.
- **Expected:** occupied volume/weight = 0; bin still reports empty (no crash).

---

## 3. Configurable toggles & thresholds

### TC-07 — Dimension toggles

- **Steps:** Toggle `use_volume`/`use_weight` on the warehouse record and re-read capacity.
- **Expected:** disabled dimension is omitted from the response and ignored in `binding_pct`.

### TC-08 — Warehouse threshold defaults

- **Preconditions:** warehouse `full=0.90`, `almost=0.70`.
- **Steps:** 75 units → `almost_full`; 95 units → `full`.
- **Expected:** band boundaries at 70% and 90%.

### TC-09 — Bin-level threshold override

- **Steps:** set `full_threshold_pct=0.50` on one bin; add 60 units (60%).
- **Expected:** that bin reports `full` (60% ≥ its 50% override), while other bins stay `available`.

---

## 4. API endpoints

### TC-10 — `GET /capacity/bins/{bin_id}`

- **Expected:** 200; body has `bin_id`, `warehouse_id`, `code`, `volume`, `weight`, `binding_pct`, `bin_state`, `is_available`.

### TC-11 — `GET /capacity/warehouses/{id}/tree`

- **Expected:** 200; root `level = "warehouse"`; `volume.occupied_m3` = sum of all bins; nested `children` down to `bin` nodes with per-bin `bin_state`.

### TC-12 — `GET /capacity/warehouses/{id}/bin-states`

- **Expected:** 200; array of all bins with `position_x/y/z`, `qr_code`, `bin_state`, `binding_pct`, `is_available`.

### TC-13 — `GET /capacity/bins/available?warehouse_id=..&task_type=put_away`

- **Expected:** 200; only bins with free space (full bins excluded); with `item_id`+`qty`, bins that can't fit the required volume are also excluded.

### TC-14 — `GET /capacity/bins/available?task_type=pick`

- **Expected:** only bins that currently hold stock of the item.

### TC-15 — `POST /capacity/bins/{bin_id}/refresh`

- **Expected:** 200; recomputes and persists `bin_state` / `is_available` / cached %; (optionally) emits a Redis event.

---

## 5. Trigger points (mobile app flows)

### TC-16 — Put-away completion updates capacity

- **Steps:** complete a put-away item into BIN-01 (95 units).
- **Expected:** BIN-01 becomes `full` and `is_available=false` immediately (no manual refresh).

### TC-17 — Direct stock entry updates capacity

- **Steps:** `POST /bin-stock/add` (95 units) to BIN-01.
- **Expected:** BIN-01 `bin_state=full`.

### TC-18 — Stock decrease updates capacity

- **Steps:** `POST /bin-stock/remove` (45 units) from BIN-01.
- **Expected:** 50 units remain → `bin_state=available`, `is_available=true`.

### TC-19 — Redis event emitted (real-time)

- **Preconditions:** Redis running; subscribe to the channel.
- **Steps:** `redis-cli --raw SUBSCRIBE warehouse:3d:<WAREHOUSE_ID>` then add/remove stock.
- **Expected:** a JSON message arrives with `"type":"bin.state.changed"`, `bin_state`, `binding_pct`, `is_available`.

---

## 6. Suggestion service (P3 wiring)

### TC-20 — Put-away excludes full bins

- **Preconditions:** BIN-01 full (95%), BIN-02 empty.
- **Steps:** request a put-away suggestion for 1 unit.
- **Expected:** suggestion list excludes BIN-01 and includes BIN-02.

### TC-21 — Put-away excludes bins that can't fit the volume

- **Preconditions:** BIN-01 `max_volume_cc=5000` (0.005 m³), item needs 10 units (0.010 m³).
- **Expected:** BIN-01 excluded from put-away suggestions.

### TC-22 — Pick respects FIFO

- **Preconditions:** same item in two bins with different receipt dates.
- **Expected:** older stock (earlier `created_at`, or expiry FEFO) ranked first.

### TC-23 — Pick respects admin priority

- **Preconditions:** set `LocationAllocation.priority` (or `PutAwayRule.priority`) higher for BIN-02.
- **Expected:** BIN-02 ranked first (reasons include "Admin priority …").

---

## 7. Frontend dashboard

### TC-24 — WMS Dashboard shows capacity card

- **Steps:** open Inventory app → WMS → **Dashboard** tab (default) → select a warehouse.
- **Expected:** a "Warehouse Capacity" card shows Volume `occupied/capacity m³` + %, Weight (if configured), overall utilisation % and a colour status badge (Empty/Available/Almost Full/Full).

### TC-25 — Card reflects a stock change

- **Steps:** perform a put-away/stock add in the mobile app or backend, then reopen/refresh the Dashboard.
- **Expected:** the capacity % and status badge update to match the new occupancy.

### TC-26 — Empty warehouse UX

- **Steps:** select a warehouse with no bins/data.
- **Expected:** card shows either 0% / "Empty" or the "No capacity data available" / "Select a warehouse" message (no crash).

---

## 8. Sign-off checklist

| Area                                                           | Pass |
| -------------------------------------------------------------- | ---- |
| Migration 072 applied, no duplicate columns                    | ☐    |
| Volume % math correct (50 → 50%)                               | ☐    |
| 4 colour states correct                                        | ☐    |
| Weight/volume toggles respected                                | ☐    |
| Thresholds (warehouse default + bin override) respected        | ☐    |
| All 5 `/capacity` endpoints return correct shapes              | ☐    |
| Put-away / stock entry / stock decrease auto-refresh capacity  | ☐    |
| Redis `bin.state.changed` emitted                              | ☐    |
| Put-away & pick suggestions use volume / FIFO / admin priority | ☐    |
| Dashboard capacity card renders and updates                    | ☐    |
