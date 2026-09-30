# MC (Master Carton) Packaging-Aware Bin & Warehouse Capacity — Manual Test Cases

> Status: **Manual test plan**
> Scope: `core-service` (FastAPI + SQLAlchemy + PostgreSQL)
> Source design: `MC_PACKAGING_CAPACITY_DESIGN.md`
> Coverage: **Phases 1–5** (implemented). Phase 6 (gross/net column split, `loose_fill_factor`, MC-break endpoint) is **not** implemented and is excluded.

---

## 1. Reference numbers used in the tests

| Symbol | Meaning | Example value |
|---|---|---|
| `V_ic` | Base-unit (Each) volume | 100 × 100 × 100 mm = **1,000 cc** (0.001 m³) |
| `W_ic` | Base-unit weight | **100 g** |
| `V_mc` | MC outer volume | 320 × 240 × 220 mm = **16,896 cc** (0.016896 m³) |
| `W_mc` | MC gross weight | **1,300 g** |
| `c` | `conversion_factor` (Eaches per MC) | **12** |

Bins:

| Bin | `capacity` (count) | `max_volume_cc` | `max_weight_grams` |
|---|---|---|---|
| BIN-A | 100 | 50,000 | 5,000 |
| BIN-B | 100 | 20,000 | 10,000 |
| BIN-C | 100 | 5,000 | 1,000 |
| BIN-D | 0 (unlimited) | NULL | NULL |

---

## 2. Prerequisites (one-time setup)

1. Create item **SKU-A** with a base packaging unit `Each` (`conversion_factor=1`, dims 100×100×100 mm, weight 100 g).
2. Create MC packaging unit **"Carton of 12"** for SKU-A (`conversion_factor=12`, outer dims 320×240×220 mm, weight 1,300 g, `is_base_unit=false`).
3. Create bins BIN-A…BIN-D under one warehouse, with limits per the table above. Set warehouse `use_volume=true`.
4. Authenticate as a user with `WAREHOUSE_READ` + `STOCK_ENTRY_CREATE` permissions for the org.

> **Important wiring note:** `packaging_unit_id` is only carried into bin stock through the **receiving → put-away → complete-item** flow (non-serialized items). The standalone `POST /bin-stock/add` endpoint does **not** accept `packaging_unit_id`. Use the put-away flow for the MC tests below.

---

## 3. Test cases

### AC-1 — Intact MC occupies `1 × V_mc`, not `12 × V_mc`

#### TC-1.1 Receive one intact master carton
- **Objective:** Verify a received MC records `packaging_unit_id` on bin stock and occupancy = one carton.
- **Preconditions:** BIN-A empty. SKU-A has MC "Carton of 12" (12/ctn, V_mc = 16,896 cc).
- **Steps:**
  1. Create a receiving slip for SKU-A with quantity **12** (non-serialized), scanned against the MC packaging unit.
  2. Approve the slip → `pending_putaway`.
  3. Generate the put-away list: `POST /put-away/generate-from-slip/{slip_id}` (auto or manual), assign to BIN-A.
  4. Complete the item: `POST /put-away/{list_id}/items/{item_id}/complete` with BIN-A.
  5. Read bin capacity: `GET /capacity/bins/{bin_a_id}`.
- **Expected:**
  - Bin stock row has `packaging_unit_id` = MC row id and `quantity_on_hand` = **12** (Eaches).
  - `volume.occupied_m3` = **0.016896** (≈16,896 cc), **not** 12 × 0.016896.
  - `unit_count` = 12, `master_pack_count` = 1.
- **Pass criteria:** `occupied_m3 ≈ 0.016896` and `master_pack_count == 1`.

#### TC-1.2 One MC + loose remainder (14 Eaches)
- **Objective:** Verify full carton + loose split.
- **Preconditions:** BIN-B empty.
- **Steps:** Receive/put-away **14** Eaches of SKU-A (MC-scanned, non-serialized) into BIN-B; read `GET /capacity/bins/{bin_b_id}`.
- **Expected:**
  - `occupied_m3` = `(1 × 16,896 + 2 × 1,000)/1e9` = **0.018896**.
  - `unit_count` = 14, `master_pack_count` = 1.
- **Pass criteria:** `occupied_m3 ≈ 0.018896`; `master_pack_count == 1`.

#### TC-1.3 No packaging unit → base-unit fallback
- **Objective:** Stock without `packaging_unit_id` is counted at base-unit volume.
- **Steps:** Add 12 loose Eaches to BIN-D (e.g., legacy receiving that never carried the MC pointer).
- **Expected:** `occupied_m3` = `12 × 0.001` = **0.012**; `master_pack_count` = 0.
- **Pass criteria:** `occupied_m3 ≈ 0.012` and `master_pack_count == 0`.

---

### AC-2 — Put-away assigns MC to a bin with enough free volume

#### TC-2.1 MC assigned to bin with sufficient free volume
- **Objective:** Auto put-away picks a bin whose free `max_volume_cc` ≥ V_mc.
- **Preconditions:** BIN-A empty (free 50,000 cc), BIN-C nearly full (free < 16,896 cc).
- **Steps:** Generate put-away (auto) for 1 MC of SKU-A; inspect the assigned `bin_location_id`.
- **Expected:** BIN-A is selected (required 16,896 cc fits), BIN-C is not.
- **Pass criteria:** assigned bin has `max_volume_cc − occupied ≥ 16,896 cc`.

#### TC-2.2 No suitable bin → item left unassigned
- **Objective:** Verify graceful behaviour when no bin fits (Req 7.7).
- **Preconditions:** Only BIN-C available, already occupied so free volume < V_mc.
- **Steps:** Auto-generate put-away for 1 MC.
- **Expected:** `bin_location_id` = null, no exception, item remains `pending`.
- **Pass criteria:** no 500 error; item unassigned with a warning.

> ⚠️ **Known caveat:** the bin *assignment* SQL (`_find_best_bin`) still computes a bin's **existing occupied volume** as `quantity_on_hand × MC_dims` (old formula). So a bin that already holds MC stock may have its free space under-reported. The *incoming* required volume is MC-aware (`_calc_volume`). Test TC-2.1 with empty bins to avoid this; flag any wrong assignment when bins already contain MCs.

---

### AC-3 — `add_stock` rejects on count **or** volume **or** weight

#### TC-3.1 Volume-limit rejection
- **Objective:** Adding an MC that exceeds `max_volume_cc` is rejected with a clear message.
- **Preconditions:** BIN-C `max_volume_cc = 5,000`, currently empty.
- **Steps:** Put-away/complete 1 MC (needs 16,896 cc) into BIN-C.
- **Expected:** Rejected with "Volume capacity exceeded… occupied … + required 16,896 cc > limit 5,000 cc". No bin stock created.
- **Pass criteria:** error names **volume** as the binding dimension; `quantity_on_hand` unchanged.

#### TC-3.2 Weight-limit rejection
- **Objective:** Weight constraint blocks stock even when count and volume pass.
- **Preconditions:** BIN-C `max_weight_grams = 1,000`, volume/weight math otherwise fine.
- **Steps:** Put-away/complete 1 MC (gross 1,300 g) into BIN-C.
- **Expected:** Rejected with "Weight capacity exceeded… > limit 1,000 g".
- **Pass criteria:** error names **weight**; no stock written.

#### TC-3.3 Count-limit rejection (existing behaviour retained)
- **Preconditions:** BIN with `capacity=5`, already holding 4 Eaches.
- **Steps:** Add 2 Eaches.
- **Expected:** Rejected with count-capacity message ("Available capacity is 1…").
- **Pass criteria:** rejection is count-based.

#### TC-3.4 Null limits = unconstrained
- **Preconditions:** BIN-D (`max_volume_cc=NULL`, `max_weight_grams=NULL`, `capacity=0`).
- **Steps:** Add a large MC quantity.
- **Expected:** Accepted (no volume/weight/count rejection).
- **Pass criteria:** stock added successfully.

---

### AC-4 — Rollup returns units + m³ at every level

#### TC-4.1 Warehouse tree rollup
- **Objective:** `GET /capacity/warehouses/{wh}/tree` reports `unit_count`, `master_pack_count`, `occupied_m3`, `capacity_m3`, `count_capacity`, `count_pct` at bin and aggregate levels.
- **Preconditions:** BIN-A has 1 MC (12 Eaches), BIN-B has 14 Eaches (1 MC + 2 loose).
- **Steps:** Call the tree endpoint.
- **Expected:**
  - BIN-A node: `unit_count=12`, `master_pack_count=1`, `volume.occupied_m3=0.016896`.
  - BIN-B node: `unit_count=14`, `master_pack_count=1`, `volume.occupied_m3=0.018896`.
  - Warehouse root: `unit_count=26`, `master_pack_count=2`, `volume.occupied_m3=0.035792`.
- **Pass criteria:** all three fields present and numerically correct at every level (bin → … → warehouse).

#### TC-4.2 Single-bin response shape
- **Objective:** `GET /capacity/bins/{bin_id}` returns the new count fields alongside volume/weight.
- **Steps:** Read BIN-A.
- **Expected:** Response contains `unit_count`, `master_pack_count`, `count_capacity`, `count_pct`, plus `volume`/`weight` blocks and `binding_pct`, `bin_state`, `is_available`.
- **Pass criteria:** schema matches `BinCapacityResponse`.

---

### AC-5 — Partial pick re-cubes MC → loose (self re-cubing, Option A)

#### TC-5.1 Pick 2 of 12 re-cubes from `1×V_mc` to `10×V_ic`
- **Objective:** Verify automatic re-cubing as `quantity_on_hand` drops.
- **Preconditions:** BIN-A holds 1 intact MC (12 Eaches, `packaging_unit_id` = MC).
- **Steps:**
  1. Pick 2 Eaches (bin-stock remove) → `quantity_on_hand` = 10.
  2. Read `GET /capacity/bins/{bin_a_id}`.
- **Expected:** `occupied_m3` = `10 × 0.001` = **0.010** (no longer 0.016896); `master_pack_count` = 0.
- **Pass criteria:** `occupied_m3 ≈ 0.010`, `master_pack_count == 0`.

#### TC-5.2 Pick to a clean multiple stays MC-counted
- **Preconditions:** BIN-A holds 24 Eaches (2 MCs).
- **Steps:** Pick 12 (one full carton) → 12 remain.
- **Expected:** `occupied_m3` = **0.016896**, `master_pack_count` = 1.
- **Pass criteria:** exactly one carton worth remains.

#### TC-5.3 No explicit "break" operation exists (Option B not shipped)
- **Steps:** Look for `POST /bin-stock/{id}/break-pack`.
- **Expected:** Endpoint does not exist (404). Re-cubing is purely formula-driven.
- **Pass criteria:** no break endpoint present; behaviour matches Option A.

---

## 4. Cross-cutting / regression

#### TC-6.1 Pick scan must not break warehouse on-hand (single-decrement rule)
- **Steps:** After TC-5.1, verify warehouse-level `stock_levels.quantity_on_hand` decremented **once** at dispatch only (not again by the pick scan).
- **Expected:** no double decrement; `quantity_available = max(0, on_hand − reserved)`.
- **Pass criteria:** warehouse aggregate consistent with bin-level totals.

#### TC-6.2 MC outer dims are never overwritten by re-estimate on item update
- **Preconditions:** MC row has operator-entered outer dims.
- **Steps:** Update SKU-A's item (e.g., rename) without changing `master_pack_*` overrides.
- **Expected:** MC `length/width/height/weight` unchanged.
- **Pass criteria:** outer dims preserved.

---

## 5. Known limitations to be aware of while testing

1. **Serialized master-pack items** (`serial_nos` present) are stored one row per serial with `quantity=1` and **no** `packaging_unit_id` — so MC outer volume is **not** applied to serialized flows. AC-1/AC-5 currently only hold for **non-serialized** items.
2. **Bin assignment occupied-volume SQL** is not yet MC-aware (only the incoming required volume is). Bin fit for already-occupied bins may be off until the `bin_usage` CTE uses the §4 formula.
3. **`POST /bin-stock/add`** does not accept `packaging_unit_id`; MC wiring is only via receiving → put-away → complete.
