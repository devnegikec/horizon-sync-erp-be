# Warehouse Capacity vs Bin Capacity — Model & Industry Alignment

> Status: **Design reference / proposal**
> Service: `core-service` (WMS Warehouse & Capacity planning)
> Date: 2026-09-04

---

## 1. Purpose

Clarify how **warehouse-level capacity** should relate to **bin-level capacity**,
and align the current implementation with industry-standard WMS practice.

The key principle:

> Capacity belongs to the **storage location (bin)**. The warehouse total is a
> **computed roll-up**, never a free-form input.

---

## 2. Current State (two disconnected models)

Today the codebase maintains two parallel capacity concepts that are **not
linked** to each other.

| Layer | Table / Model | Fields | Where it is set |
|---|---|---|---|
| **Warehouse** | `warehouses_extended` (`app/models/warehouse.py`) | `total_capacity` (Integer), `capacity_uom`, `use_volume`, `use_weight`, `full_threshold_pct`, `almost_full_threshold_pct` | `WarehouseDialog.tsx` create/update UI — `Total Capacity` is a manual input |
| **Location tree** | `warehouse_locations` (`app/models/warehouse_location.py`) | `capacity` (per bin), `total_capacity`, `available_capacity`, `max_volume_cc`, `max_weight_grams` | Set per-bin via layout; `capacity_service.recalculate_ancestors()` rolls children up the tree |
| **Volume/weight view** | `bin_capacity_service.py`, `WarehouseCapacityCard.tsx` | `capacity_volume_pct`, `capacity_weight_pct`, `bin_state` | Derived per-bin from stock occupancy |

### What is already correct

The **location hierarchy** roll-up is correct:

- Each **bin** owns a `capacity`.
- `capacity_service.recalculate_ancestors()` walks
  `Zone → Aisle → Bay → Level → Bin` summing each child's `total_capacity`
  into its parent.

### What is wrong

The **warehouse `total_capacity`** is a free-form integer entered in the
warehouse create/update UI. It is **never derived from the layout** — nothing
syncs `warehouse.total_capacity` from `warehouse_locations`.

`layout_service.py:451` already computes the correct derived total
(`SUM(WarehouseLocation.capacity)`) — but it is exposed read-only and is not
persisted back onto the warehouse record.

Result: the UI lets an operator type "10,000" while the real layout sums to
8,240 — the two drift.

---

## 3. Correct Model

Warehouse capacity must **derive from the layout**, where each bin carries its
own capacity:

```
bin.capacity  ──┐
bin.capacity  ──┤  sum → level → bay → aisle → zone → WAREHOUSE total
bin.capacity  ──┘
```

- The warehouse is a *container of containers*; it has no intrinsic capacity of
  its own.
- A manually-typed warehouse capacity is an anti-pattern because it can disagree
  with the physical layout the moment a bin is added, removed, or resized.

---

## 4. Industry Practice

1. **Capacity lives on the location/bin**, expressed in one or more dimensions:
   - **Volume** — m³ / ft³
   - **Weight** — kg / lb
   - **Unit count** — pallets / cases / eaches
   - Often a mix, e.g. "this bin = 1 pallet = 1.2 m³ = 500 kg".

2. **Roll-up is always computed, never entered.** Zone / area / warehouse totals
   are `SUM(children)`, recalculated on demand or after any bin change.

3. **Multi-dimension with a binding constraint.** A bin can be full by volume,
   by weight, or by unit count — whichever fills first is the binding one.
   (Already modelled via `use_volume` / `use_weight` + the threshold fields.)

4. **Warehouse-level fields that *do* belong in the UI are planning settings,
   not capacity numbers:**
   - volume vs weight mode (`use_volume`, `use_weight`)
   - utilization thresholds (`full_threshold_pct`, `almost_full_threshold_pct`)
   - capacity UOM convention (`capacity_uom`)
   These tune *how* capacity is measured, not *how much*.

5. **Acceptable exceptions where warehouse capacity may be manually entered:**
   - **No detailed layout yet** (bulk/ambient storage, floor-stack warehouses) —
     a planning capacity is kept as a fallback until a layout is drawn.
   - **Regulatory / manual overrides** (e.g. fire-code maximum) — kept as a
     separate, clearly-labelled "declared capacity" that caps the computed total.
   - In all cases, once a bin layout exists, **the layout-derived figure wins**
     and the manual field is read-only or hidden.

---

## 5. Recommendation for this Codebase

Make `warehouses_extended.total_capacity` a **derived, read-only** value:

1. **Remove `Total Capacity` from the warehouse create/update UI**
   (`apps/inventory/src/app/components/warehouses/WarehouseDialog.tsx`),
   or mark it read-only/disabled. `capacity_uom` should also stop accepting
   free-form values (or become a planning setting).

2. **Compute warehouse capacity from the location tree.**
   Reuse the `SUM(WarehouseLocation.capacity)` logic already present in
   `layout_service.py:451`, and either:
   - expose it through the existing warehouse capacity summary endpoint
     (already consumed by `WarehouseCapacityCard.tsx`), or
   - persist it back to `warehouse.total_capacity` as a denormalized cache
     after every `recalculate_ancestors()` / bin-capacity change.

3. **Keep as editable planning settings:**
   - `use_volume`
   - `use_weight`
   - `full_threshold_pct`
   - `almost_full_threshold_pct`

### Minimal change

- Stop treating `total_capacity` as user input.
- In the bin-capacity update path (`capacity_service.update_location_capacity`
  / `recalculate_ancestors`), also write
  `SUM(active bin capacity)` back onto the warehouse row so the warehouse total
  always equals the sum of its bins.

---

## 6. References

- Warehouse model: `core-service/app/models/warehouse.py`
- Location model: `core-service/app/models/warehouse_location.py`
- Roll-up logic: `core-service/app/services/capacity_service.py`
- Derived sum already computed: `core-service/app/services/layout_service.py:451`
- Bin capacity state: `core-service/app/services/bin_capacity_service.py`
- Warehouse UI (manual capacity input):
  `horizon-sync/apps/inventory/src/app/components/warehouses/WarehouseDialog.tsx`
- Derived capacity display:
  `horizon-sync/apps/inventory/src/app/components/wms/WarehouseCapacityCard.tsx`
