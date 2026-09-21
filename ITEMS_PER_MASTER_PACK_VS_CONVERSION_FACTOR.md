# `items_per_master_pack` vs `conversion_factor` — when they differ

> Status: **Reference / clarification**
> Scope: `core-service` (`item_packaging_units`)
> Related: `MC_PACKAGING_CAPACITY_DESIGN.md` §1c, `CONVERSION_FACTOR_PACKAGING_VS_UOM.md`

Both are columns on `item_packaging_units`, often equal in value but different in
purpose. This document covers the cases where they **differ**, and what each
consumer does with each value.

---

## 1. The two questions a single MC row answers

On a single **non-base (MC) row**, the two fields answer two different
questions, so they diverge whenever the *physical container* and the
*serialized grouping unit* are not the same size.

| Field | Question it answers | Drives |
|---|---|---|
| `conversion_factor` | "How many Eaches does this **physical container** hold?" | volume / weight capacity |
| `items_per_master_pack` | "How many **serialized** Eaches are tracked as one master pack?" | serial grouping / case-split |

---

## 2. Scenario 1 — serialized sub-packaging inside a larger case (main case)

**Item:** serialized medical battery cells.

- Physical shipping case = **"Case of 20"** → `conversion_factor = 20`
  (20 cells per case; volume = `1 × V_case`).
- Cells are serialized and tracked in inner **foam trays of 5**, which is the
  "master pack" for serial grouping → `items_per_master_pack = 5`.

MC row `"Case of 20"`:

| Field | Value | Meaning |
|---|---|---|
| `conversion_factor` | **20** | 1 physical case = 20 Eaches (volume/weight bridge) |
| `items_per_master_pack` | **5** | serials grouped 5 per master pack → 4 master packs per case |

**What each consumer does with this row:**

| Consumer | Reads | Result |
|---|---|---|
| `capacity_math.py` / volumetric assignment | `conversion_factor = 20` | full case = `1 × V_case`, loose remainder in Eaches |
| `put_away_service._items_per_master_pack` | prefers `items_per_master_pack = 5` | chunks slip serials into groups of **5** |
| `outbound_order_service._resolve_packaging` | base/master `items_per_master_pack = 5` | case = ⌊qty/5⌋, loose = qty % 5 |
| QSeal / QR master-pack auto-link | `master_pack_size = 5` | creates a QSeal parent every **5** serials |

So one physical case (20) contains **four** serialized master packs of 5.
The volume engine counts 1 carton; the serialization engine counts 4 groups.

---

## 3. Scenario 2 — non-serialized item (value vs NULL)

**Item:** non-serialized screws.

- `"Carton of 500"` → `conversion_factor = 500` (physical quantity/volume).
- `items_per_master_pack = NULL` — no serials to group, so the field is
  intentionally empty.

| Field | Value |
|---|---|
| `conversion_factor` | 500 |
| `items_per_master_pack` | NULL |

They differ by design: `items_per_master_pack` only exists for **serialized**
identity grouping. For batch-tracked items it stays NULL and consumers fall
back to `conversion_factor`.

---

## 4. Scenario 3 — pallet vs carton tier (larger grouping)

**Item:** serialized phones, two packaging levels.

- `"Carton of 12"` (MC) → `conversion_factor = 12`, `items_per_master_pack = 12`
  (one master pack per carton).
- `"Pallet of 48"` (another non-base row) → `conversion_factor = 48`
  (4 cartons), but serialized "master packs" are still the individual cartons →
  `items_per_master_pack = 12`.

The pallet row has `conversion_factor = 48` but `items_per_master_pack = 12`,
because serials travel in cartons, not on the pallet as one unit.

---

## 5. Bottom line

`conversion_factor` and `items_per_master_pack` differ whenever:

1. The physical pack size ≠ the serialized tracking group size (Scenario 1 —
   the most realistic case).
2. The item isn't serialized, so `items_per_master_pack` is NULL (Scenario 2).
3. A packaging tier groups multiple lower-level master packs (Scenario 3).

When they *are* equal (the common case in this deployment), it is simply because
**one physical carton == one serialized master pack** — which is why the design
doc recommends maintaining `conversion_factor` as the single source of truth and
setting `items_per_master_pack` only when a pack size genuinely differs.

---

## 6. Consumer lookup order (code reference)

- `put_away_service._items_per_master_pack`:
  1. any active row with `items_per_master_pack > 1` → returns that value.
  2. else the active row with the smallest `conversion_factor > 1`.
- `outbound_order_service._resolve_packaging`:
  1. base "Each" row with `items_per_master_pack > 1`.
  2. else non-base row with `conversion_factor > 1` or `items_per_master_pack > 1`
     (prefers `items_per_master_pack`, then `conversion_factor`).
- `capacity_math.py` / `volumetric_assignment_service.py` use **only**
  `conversion_factor` (volume/weight); they ignore `items_per_master_pack`.
