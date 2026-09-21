# `conversion_factor`: `item_packaging_units` vs `uom_conversions`

> Status: **Reference / clarification**
> Scope: `core-service` (FastAPI + SQLAlchemy + PostgreSQL)
> Related: `MC_PACKAGING_CAPACITY_DESIGN.md` §1b/§1c

Both tables have a column named `conversion_factor`, but they serve completely
different purposes and must not be confused or merged.

---

## 1. Summary

| | `item_packaging_units` | `uom_conversions` |
|---|---|---|
| What it describes | **Physical packaging level** of an item | **Quantity translation** between two units of measure |
| Factor semantics | "1 pack = N base Eaches" (base-relative) | "N units of `to_uom` per 1 unit of `from_uom`" (pair-directed) |
| One row per… | packaging level | `(item, from_uom, to_uom)` pair |
| Physical dims/weight | ✅ yes (`length_mm`, `width_mm`, `height_mm`, `weight_grams`) | ❌ no |
| Base-unit flag | ✅ `is_base_unit` | ❌ no |
| Item required | ✅ always (each level belongs to an item) | ❌ optional (`item_id` nullable → org-global fallback) |
| Used for | Capacity/volume/weight, put-away, receiving → Eaches | Stock entries, quantity conversion to base UOM |
| Conversion math | `n_full = qty // c`, `n_loose = qty % c` | `qty × factor` (forward) or `qty / factor` (reverse) |

---

## 2. `item_packaging_units.conversion_factor` — physical packaging hierarchy

This is about **how items are physically packed**, and it feeds the
**capacity / volume / weight engine**.

- **Meaning:** how many base units (Eaches/IC) are inside **one** of this
  packaging level.
- **Direction:** always **relative to the base unit** — "1 Carton = N Eaches".
  There is no `from`/`to` pair; the base unit is identified by `is_base_unit`.
- **Carries physical data:** `length_mm`, `width_mm`, `height_mm`,
  `weight_grams`, `is_base_unit`, `items_per_master_pack`, `qr_identifier`.
- **Consumers:**
  - `capacity_math.py` §4 occupancy formula
  - `volumetric_assignment_service.py` (`_calc_volume` / `_calc_weight`)
  - put-away master-pack grouping (`put_away_service._items_per_master_pack`)
  - receiving approval (`inbound_service`: `eaches = raw_qty × factor`)

```
item_packaging_units
├─ "Each"          conversion_factor = 1   (base, net dims/weight)
└─ "Carton of 12"  conversion_factor = 12  (MC, outer/gross dims/weight)
```

---

## 3. `uom_conversions.conversion_factor` — unit-of-measure arithmetic

This is about **converting a quantity between two units of measure**
(kg ↔ g, Box ↔ pcs, L ↔ ml). It is pure quantity math — no physical dimensions.

- **Meaning:** multiply a quantity in `from_uom` by this factor to obtain
  `to_uom`.
- **Direction:** directional — `from_uom` → `to_uom`; supports forward
  (`× factor`) and reverse (`÷ factor`) lookup.
- **Carries:** only the factor + the pair (`from_uom_id`/`to_uom_id`, plus
  legacy string columns `from_uom`/`to_uom`).
- **Scope:** item-specific (`item_id` set) or org-wide fallback
  (`item_id IS NULL`).
- **Consumers:**
  - `UOMConversionService.convert_quantity`
  - `StockEntryService._get_conversion_factor`
  - quantity normalization to the item's base UOM

```
uom_conversions
├─ (item=SKU-A, from="Kg", to="g")  conversion_factor = 1000
└─ (item=SKU-A, from="Box", to="pcs") conversion_factor = 12
```

---

## 4. Why they are intentionally separate

They answer different questions, even when the numbers happen to match:

- **Packaging `conversion_factor = 12`** answers: *"how much space/weight does
  one carton occupy?"* — it is only meaningful together with outer dimensions
  and gross weight.
- **UOM conversion `Carton → Each = 12`** answers: *"how many Eaches equal one
  Carton in quantity arithmetic?"* — it is just a multiplier between two named
  units.

A "Carton of 12" could conceptually be modeled either way, but the system keeps
them separate because:

1. The packaging table carries the **physical dimension data** the capacity
   engine needs (`capacity_math.py`, `volumetric_assignment_service.py`).
2. UOM conversions only carry **arithmetic factors** with a direction.

Overloading them into a single field would lose the dimension/weight context
and the directional pair semantics.

---

## 5. Concrete examples

### Example A — numbers coincide, but meaning differs

| System | Record | Factor | Meaning |
|---|---|---|---|
| Packaging | `Carton of 12` | `12` | 1 carton = 12 Eaches, outer dims 320×240×220 mm, gross 1,300 g |
| UOM conversion | `Carton → Each` | `12` | `quantity_in_eaches = quantity_in_cartons × 12` |

### Example B — UOM conversion has no packaging counterpart

| System | Record | Factor | Meaning |
|---|---|---|---|
| UOM conversion | `Kg → g` | `1000` | `g = kg × 1000` — no packaging level involved |

---

## 6. Where each is read in code

- Packaging factor:
  - `app/services/capacity_math.py` → `_row_occupied`, `compute_bin_counts`
  - `app/services/volumetric_assignment_service.py` → `_factor`, `_calc_volume`
  - `app/services/inbound_service.py` → receiving approval (`eaches_qty`)
  - `app/services/put_away_service.py` → `_items_per_master_pack`
- UOM conversion factor:
  - `app/services/uom_conversion_service.py` → `convert_quantity`
  - `app/services/stock_entry_service.py` → `_get_conversion_factor`
