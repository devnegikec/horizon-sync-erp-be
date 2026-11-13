# WMS Zone / Slotting / Capacity Design — HLD & LLD

- **Status:** Draft — for review before implementation
- **Date:** 2026-10-20
- **Scope:** core-service
- **Related docs:** [3D_WAREHOUSE_VIEW_DESIGN.md](./3D_WAREHOUSE_VIEW_DESIGN.md), [LAYOUT_JSON_DESIGNER_PLAN.md](./LAYOUT_JSON_DESIGNER_PLAN.md), [WMS_STOCK_CONCURRENCY_LOCKING.md](./WMS_STOCK_CONCURRENCY_LOCKING.md)

---

## 1. Summary

We already have a `Zone → Aisle → Bay → Level → Bin` location hierarchy and
bin-level stock. What is missing for a standard WMS is:

1. **A purpose/type on zones** so a zone can be *"the fast-moving zone"*.
2. **Velocity classification (ABC)** on items so "fast-moving" is data, not a
   template name.
3. **Slotting** — a first-class SKU ↔ bin/lane assignment (home slot, overflow,
   min/max) instead of the current item-group-only allocation.
4. **Pre-aggregated capacity** — cached occupied volume/weight/units on each bin,
   updated incrementally, so capacity reads and put-away scoring stop doing
   per-bin occupancy queries.

This document gives the High-Level Design (HLD) and Low-Level Design (LLD) for
those four capabilities and their supporting flows (put-away scoring, pick
filtering, replenishment).

---

## 2. Goals / Non-goals

### Goals

- Tag a **SKU/item** to a **bin** or to a **lane** (aisle) level.
- Assign **fast-moving items to a dedicated fast zone** automatically, using a
  computed velocity class with manual override.
- Make **capacity calculation fast enough** for per-request use in the 3D view,
  status polling, and bin suggestion, by serving reads from cached columns.
- Keep existing behaviour (layout apply, 3D view, reservations, FEFO/FIFO)
  intact.

### Non-goals (out of scope for v1)

- Full slotting optimization engine (e.g. genetic / LP re-slotting).
- Wave picking / multi-order batch optimization.
- Hardware automation (AGV/ASRS) integration.
- Multi-warehouse velocity pooling.

---

## 3. Current state analysis

### 3.1 What exists

| Concept | Where | Notes |
|---|---|---|
| Location hierarchy | [`../app/models/warehouse_location.py`](../app/models/warehouse_location.py) | `parent_location_id` + `location_type` (`zone/aisle/bay/level/bin/staging`), `full_path`, `max_volume_cc`, `max_weight_grams`, thresholds, `bin_state`, `is_pickable` |
| Bin-level stock | [`../app/models/bin_stock_level.py`](../app/models/bin_stock_level.py) | `(bin × item × batch × inventory_status) → quantity_on_hand` |
| SKU ↔ location (indirect) | [`../app/models/location_allocation.py`](../app/models/location_allocation.py) | location ↔ **item group** only, `exclusive/preferred` + priority |
| Put-away rules | [`../app/models/put_away_rule.py`](../app/models/put_away_rule.py) | item/group + warehouse → priority/min/max |
| Capacity math | [`../app/services/capacity_math.py`](../app/services/capacity_math.py) | volume (cc) + weight (g), master-pack aware |
| Capacity service | [`../app/services/bin_capacity_service.py`](../app/services/bin_capacity_service.py) | `refresh_bin` (cache), `get_capacity_tree`, `get_available_bins` |
| Suggestion engine | [`../app/services/location_suggestion_service.py`](../app/services/location_suggestion_service.py) | put-away/pick scoring, allocation resolution |
| Movement audit | [`../app/models/stock_movement.py`](../app/models/stock_movement.py) | `product_id`, `movement_type`, `quantity`, `performed_at` |

### 3.2 Bottlenecks (confirmed in code)

1. **`LocationSuggestionService._score_put_away`** loads *all* bins, then per
   bin calls `get_bin_capacity()` (which recomputes occupancy) **and**
   `_bin_contains_item()` / `_bin_contains_item_group()` — N+1 queries per
   request.
2. **`BinCapacityService.get_available_bins`** loads all bins and calls
   `compute_bin_occupancy()` once per bin.
3. **`_descendant_bin_ids`** resolves a zone/aisle-level allocation to bins with
   a BFS that issues one query per node.
4. **`get_capacity_tree`** recomputes whole-warehouse occupancy from
   `bin_stock_levels` on every call, even though `capacity_volume_pct`,
   `capacity_weight_pct` and `bin_state` are already cached on the bin row.
5. **No velocity model** — "Fast Movers" appears only as a template zone name in
   [`../app/services/floor_plan_generator_service.py`](../app/services/floor_plan_generator_service.py).

---

## 4. High-Level Design (HLD)

### 4.1 Guiding principles (standard WMS)

- **Fixed-depth hierarchy** — `Zone → Aisle → Bay → Level → Bin`. A bin is the
  smallest addressable slot; everything above is a grouping for routing,
  zoning and rollups.
- **Denormalized path** — every bin carries its `zone/aisle/bay/level` ids so
  ancestor questions are indexed lookups, never tree walks.
- **Velocity drives zoning** — ABC class decides *where* an item lives.
- **Slotting** — a SKU has a *home slot* (fixed face) and optional *secondary /
  overflow* slots, with min/max for replenishment.
- **Capacity is a cached, incrementally-maintained fact**, recomputed only on
  stock movement or layout change, never on read.

### 4.2 Conceptual model

```
Item (velocity_class, velocity_score)
  └─ ProductSKU (product_sku_id)
  └─ ItemGroup (fallback affinity)

Zone (zone_purpose: fast_moving | slow_moving | reserve | oversize | quarantine | staging)
  └─ Aisle ("lane")
       └─ Bay
            └─ Level
                 └─ Bin  (denormalized zone/aisle/bay/level ids,
                           cached occupied_volume_cc/weight/units,
                           bin_state, is_pickable)

ItemLocationSlot (item/sku/group → location at bin OR aisle/lane level,
                  slot_type: home|secondary|overflow, min_qty, max_qty, priority)
```

### 4.3 Zone purpose

Add a `zone_purpose` to zone rows. Standard split:

| Purpose | Characteristics | Pickable? |
|---|---|---|
| `fast_moving` | forward-pick area, near dock, shallow bins | yes |
| `slow_moving` | normal pick area | yes |
| `reserve` | bulk/overflow, deep racks | no |
| `oversize` | large items | conditional |
| `quarantine` | hold/quality | no |
| `staging` | inbound/outbound staging lanes | no |

Assignment rule (v1, configurable later):

```
velocity A  → fast_moving zone (home slot)
velocity B  → slow_moving zone
velocity C/N → reserve zone
```

### 4.4 Velocity classification (ABC)

- `velocity_score` = outbound units (picked/shipped) over the last 30 days,
  aggregated from `stock_movements` where `movement_type` is outbound.
- Class assignment by score share (cumulative Pareto) or fixed thresholds —
  configurable per warehouse via `system_config`.
- `velocity_class` is persisted on `items`; manual override wins until cleared.

### 4.5 Slotting

- A slot binds **item** (or `product_sku_id`, or item group as a default) to a
  **location**, where location may be:
  - a **bin** → exact SKU↔bin tag, or
  - an **aisle** → "lane-level" tag; resolves to the lane's bins via the
    denormalized `aisle_id`.
- Resolution priority: **item > SKU > item group**.
- `slot_type`:
  - `home` — the item's fixed pick face (one per zone per item).
  - `secondary` — alternate pick face.
  - `overflow` — spill-over storage.
- `min_qty` / `max_qty` on `home` slots drive replenishment from `reserve`.

#### 4.5.1 Slotting in plain language (the library analogy)

Think of the warehouse as a library:

| Warehouse concept | Library analogy |
|---|---|
| **Zone** | A *section* — e.g. the "Bestsellers" shelf kept right next to the entrance (the fast zone) |
| **Aisle / lane** | One particular *shelf unit / row* |
| **Bay** | A *column* of that shelf unit |
| **Level** | A *shelf* within the column |
| **Bin** | One *cubby / slot* on the shelf |
| **SKU** | One specific *book title* |

- *Tagging a SKU to a bin* = writing a permanent label: **"Red Mug always
  lives in cubby #3, shelf 2, row A01."**
- *Tagging a SKU to a lane* = a looser label: **"Blue Mug lives somewhere in
  row A01 — any free cubby there."**

The "tag" is just a **stored instruction about where an item should go**, so the
system does not search the whole warehouse on every put-away. It is a **row in
`item_location_slots`** — nothing more.

#### 4.5.2 What a tag row means

```
┌ item_location_slots ───────────────────────────────────────────────┐
│ item_id (or sku)   ← WHICH product                                  │
│ location_id        ← WHERE (a bin, or an aisle/lane, or a zone)     │
│ slot_type          ← home | secondary | overflow                    │
│ min_qty, max_qty   ← replenishment bounds                           │
│ priority           ← if several tags match, which one wins          │
└─────────────────────────────────────────────────────────────────────┘
```

This is a strict superset of today's
[`location_allocation`](../app/models/location_allocation.py): today you can only
say *"item **group** → location (preferred/exclusive)"*. The new table adds
three things — you can tag a **single item/SKU**, you can tag a **bin or a
lane**, and you get **home/secondary/overflow + min/max**.

**Bin-level tag (exact address)** — `location_id` points at a bin:

> Red Mug → bin `A01-02-03` (home slot, min 5, max 20)

**Lane-level tag (flexible address)** — `location_id` points at an aisle:

> Blue Mug → aisle `A01` (home slot)

The lane tag works because of the denormalized path columns (§5.2): every bin
carries its `zone_id` / `aisle_id` / `bay_id` / `level_id`. So *"all bins in
aisle A01"* is one indexed query, replacing the current BFS in
`_descendant_bin_ids` (§3.2):

```sql
SELECT id FROM warehouse_locations
WHERE warehouse_id = 'WH1' AND location_type = 'bin'
  AND aisle_id = 'A01' AND is_active = true;
```

#### 4.5.3 Worked example

Warehouse `WH1`:

```
Zone Z1 (fast_moving)        Zone Z2 (reserve)
 └ Aisle A01                  └ Aisle A09
    ├ bin A01-01                 ├ bin A09-01
    ├ bin A01-02                 └ bin A09-02
    └ bin A01-03
```

Items:

```
item 100 = Red Mug  (SKU RM-100)  velocity A → fast zone
item 200 = Blue Mug (SKU BM-200)  velocity B → slow zone
```

Tags (rows in `item_location_slots`):

```
row 1: item 100 → bin   A01-01   home     min=5  max=20
row 2: item 200 → aisle A01      home     min=10 max=50
row 3: item 200 → bin   A01-02   overflow
```

**Put-away: a carton of Red Mug (item 100) arrives**

1. Velocity → **A** → fast zone `Z1`.
2. Tag lookup → row 1 says **home slot = bin `A01-01`**.
3. Capacity check on `A01-01` (cached `occupied_volume_cc` vs `max_volume_cc`).
   - **Fits** → suggest `A01-01` with the top score (home slot = +100).
   - **Full** → fall back to other non-full bins in `Z1`, or an overflow slot.
4. Put away → `refresh_bin` updates the cached occupancy.

**Put-away: a carton of Blue Mug (item 200) arrives**

1. Velocity → **B** → slow zone.
2. Tag lookup → row 2 says **home slot = aisle `A01`** (lane-level).
3. Resolve the lane: `aisle_id = A01` → `[A01-01, A01-02, A01-03]`.
4. Score them; `A01-03` is empty → suggest `A01-03`.

The tag **steers** the system to the preferred location; the **capacity check**
still uses the item's own dimensions against the bin's remaining volume/weight.
The tag never enters the capacity math (see §4.6).

#### 4.5.4 What a tag is NOT

- **Not a capacity rule** — capacity is `bin limit` vs `sum of actual items'
  volume/weight`; the tag never enters that computation.
- **Not a hard lock** — `home`/`secondary` are *preferences* with score weights;
  `overflow` is a fallback. The put-away scorer may choose another bin when the
  tagged bin is full or reserved.

#### 4.5.5 When tagging happens (lifecycle)

Tagging is **neither** an item-creation step **nor** a layout-design step — it
is its own, ongoing operational activity that requires both to already exist.

| Activity | When | Produces | Where |
|---|---|---|---|
| Location design | one-off / occasional | zones, aisles, bays, levels, bins + zone *purpose* — geometry only, **no SKUs** | [`layout_design_service.py`](../app/services/layout_design_service.py) (`apply`) |
| Item creation | at product onboarding | the item/SKU master (code, dims, weight, packaging) — **no location** | [`sku_service.py`](../app/services/sku_service.py) |
| Velocity classification | periodic job / manual | `velocity_class` (A/B/C) on the item | new `VelocityService` (§5.5) |
| **SKU tagging (slotting)** | **ongoing, as needed** | the *"this SKU → that bin/lane"* rule | new `SlottingService` (§5.4) |

You cannot tag at item-creation time (bins may not exist yet; the item has no
velocity history), and you cannot tag at layout-design time (layout is pure
geometry — you don't know which SKUs will arrive). Tagging is the glue applied
**after** both exist.

End-to-end, with item 100 / SKU RM-100 (Red Mug):

1. **Design layout** — admin creates fast zone `Z1` with bins `A01-01..03` and
   reserve zone `Z2`. Space and purpose known; no SKU involved.
2. **Create item** — admin creates Red Mug (item 100, SKU RM-100) with
   dimensions and packaging. Product known; no location.
3. **Classify velocity** — job (or manual override) sets `velocity_class=A`.
4. **Tag (slot)** — admin creates: `item 100 → bin A01-01, home, min=5, max=20`.
   The system may *suggest* this slot; an admin confirms it.
5. **Inbound** — a Red Mug receipt triggers put-away; the engine reads the tag
   and suggests `A01-01` first (home slot = top score), then runs the capacity
   check with the mug's own dimensions.
6. **Replenish** — a nightly job tops `A01-01` up from reserve `Z2` when stock
   drops below `min=5`.

#### 4.5.6 Re-tagging (admin maintenance)

A slot is a **mutable row**, not a frozen fact. Warehouse admins can re-tag at
any time via `PATCH /wms/slots/{id}` / `DELETE /wms/slots/{id}`:

- **Change the bin** — new `location_id` (Red Mug `A01-01` → `A01-05`).
- **Change the level** — point the tag at an **aisle** instead of a bin, making
  it "any free cubby in lane A01".
- **Change the role** — `home` ↔ `secondary` ↔ `overflow`.
- **Change the bounds** — `min_qty`, `max_qty`, `priority`.
- **Disable / remove** — `is_active=false` (soft-delete) or DELETE.

Typical triggers: seasonality, velocity reclassification, a bin becoming
damaged/unavailable, or a periodic slotting review.

**Important nuance:** re-tagging changes **future put-away routing only**. It
does **not** physically move stock already sitting in the old bin. If Red Mugs
are in `A01-01` and the tag moves to `A01-05`:

- new receipts go to `A01-05`;
- existing stock stays in `A01-01` until a **move / replenishment task**
  relocates it (same mechanism as step 6 above).

The tag is a *plan*; physical movement is a separate *task* — exactly how
production WMS systems behave.

```
Layout design ──► defines SPACE + zone purpose
Item creation ──► defines PRODUCT (no location)
Velocity job  ──► labels the product (A/B/C)
Slotting      ──► glues product ↔ space   ◄── re-tagged any time by admin
Inbound flow  ──► reads the tag to route put-away
Replenishment ──► keeps tagged home faces stocked (and relocates on re-tag)
```

### 4.6 Capacity model

- Keep the existing per-bin limit columns (`max_volume_cc`, `max_weight_grams`,
  `capacity_uom`, thresholds).
- **Add raw occupied cache columns** on the bin row:
  `occupied_volume_cc`, `occupied_weight_grams`, `unit_count_eaches`,
  `master_pack_count`.
- `BinCapacityService.refresh_bin` already recomputes these; persist them and
  recompute **incrementally** (add the movement delta) rather than from scratch.
- Zone/aisle rollups sum the cached per-bin columns — no join to
  `bin_stock_levels`.

### 4.7 End-to-end flows

**Put-away**
1. Look up item velocity + slot.
2. Candidate bins = bins in the slot's zone/aisle (denormalized filter) with
   `bin_state != 'full'` and `is_pickable`.
3. Score (unchanged dimensions, but using cached capacity + resolved slot):
   slot match > consolidation (same item) > empty home slot > distance.
4. Reserve bin → move stock → `refresh_bin` updates cache + publishes event.

**Pick**
1. Candidate bins = bins containing the item in pickable zones (FEFO/FIFO as
   today), optionally restricted to the item's slot lanes.

**Replenishment (background job)**
1. For each active `home` slot in `fast_moving`/`slow_moving` zones, if
   `qty_on_hand < min_qty`, create a replenishment move from a `reserve` bin.

### 4.8 Component / module view

```
                 ┌─────────────────────────────────────────────┐
                 │              API (wms endpoints)            │
                 │  /wms/slots  /wms/velocity  /wms-3d/*       │
                 └───────┬──────────────┬──────────────┬───────┘
                         │              │              │
              ┌──────────▼───┐  ┌───────▼────────┐  ┌──▼──────────────────┐
              │ SlottingSvc  │  │ VelocitySvc    │  │ LocationSuggestion  │
              │ (slot CRUD,  │  │ (classify job, │  │ (put-away/pick      │
              │  resolution) │  │  override)     │  │  scoring)           │
              └──────┬───────┘  └───────┬────────┘  └──┬──────────────────┘
                     │                  │               │
              ┌──────▼──────────────────▼───────────────▼──────┐
              │        BinCapacityService (cached capacity)      │
              │        + denormalized path + occupancy cache     │
              └──────────────────────┬───────────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ warehouse_locations │ + bin_stock_levels
                          │ items / slots       │ + stock_movements
                          └─────────────────────┘
```

---

## 5. Low-Level Design (LLD)

### 5.1 Database changes (migrations)

Migrations live in [`../alembic/versions/`](../alembic/versions/). Use the next
available numeric prefix. Proposed sequence:

| Migration | Purpose |
|---|---|
| `13x_add_location_path_columns.py` | denormalized `zone_id/aisle_id/bay_id/level_id` + `zone_code/aisle_code` + `zone_purpose` on `warehouse_locations` |
| `13x_add_item_velocity_fields.py` | `velocity_class`, `velocity_score`, `velocity_source`, `velocity_computed_at` on `items` |
| `13x_create_item_location_slots.py` | new `item_location_slots` table |
| `13x_add_bin_occupancy_cache.py` | `occupied_volume_cc`, `occupied_weight_grams`, `unit_count_eaches`, `master_pack_count` on `warehouse_locations` |

### 5.2 `warehouse_locations` new columns

```python
# denormalized path — populated at layout apply / reconcile
zone_id   = Column(UUID(as_uuid=True), nullable=True, index=True)
aisle_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
bay_id    = Column(UUID(as_uuid=True), nullable=True, index=True)
level_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
zone_code = Column(String(50), nullable=True)
aisle_code = Column(String(50), nullable=True)

# zone purpose (only meaningful on zone-type rows)
zone_purpose = Column(String(30), nullable=True)  # fast_moving | slow_moving | reserve | oversize | quarantine | staging

# cached raw occupancy (written by BinCapacityService)
occupied_volume_cc    = Column(Numeric(15, 2), nullable=True)
occupied_weight_grams = Column(Numeric(15, 2), nullable=True)
unit_count_eaches     = Column(Numeric(15, 3), nullable=True)
master_pack_count     = Column(Numeric(15, 3), nullable=True)
```

Population: in [`layout_design_service.py`](../app/services/layout_design_service.py)
`_reconcile`/`_adopt`, while linking `parent_location_id`, also copy the parent
chain ids/codes onto each child (parents-first ordering already exists there).

### 5.3 `items` new columns

```python
velocity_class     = Column(String(1), nullable=True)      # A | B | C | N
velocity_score     = Column(Numeric(18, 3), nullable=True) # outbound units 30d
velocity_source    = Column(String(10), nullable=True)     # auto | manual
velocity_computed_at = Column(DateTime(timezone=True), nullable=True)
```

Index: `(organization_id, velocity_class)`.

### 5.4 New table `item_location_slots`

```sql
CREATE TABLE item_location_slots (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL,
    warehouse_id      UUID NOT NULL REFERENCES warehouses_extended(id) ON DELETE CASCADE,
    item_id           UUID NULL REFERENCES items(id) ON DELETE CASCADE,
    product_sku_id    UUID NULL REFERENCES product_skus(id) ON DELETE CASCADE,
    item_group_id     UUID NULL REFERENCES item_groups(id) ON DELETE CASCADE,
    location_id       UUID NOT NULL REFERENCES warehouse_locations(id) ON DELETE CASCADE,
    slot_type         VARCHAR(20) NOT NULL DEFAULT 'home',   -- home | secondary | overflow
    min_qty           NUMERIC(15,3) NULL,
    max_qty           NUMERIC(15,3) NULL,
    priority          INTEGER NOT NULL DEFAULT 0,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_by        UUID NULL,
    updated_by        UUID NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_slot_scope UNIQUE (organization_id, warehouse_id, item_id, product_sku_id, item_group_id, location_id, slot_type),
    CHECK (item_id IS NOT NULL OR product_sku_id IS NOT NULL OR item_group_id IS NOT NULL)
);

CREATE INDEX ix_slots_item   ON item_location_slots (organization_id, warehouse_id, item_id, is_active);
CREATE INDEX ix_slots_sku    ON item_location_slots (organization_id, warehouse_id, product_sku_id, is_active);
CREATE INDEX ix_slots_group  ON item_location_slots (organization_id, warehouse_id, item_group_id, is_active);
CREATE INDEX ix_slots_loc    ON item_location_slots (organization_id, warehouse_id, location_id, is_active);
```

Resolution (item > SKU > group) implemented in a new `SlottingService`:

```python
class SlottingService:
    def resolve_slots(self, *, org_id, warehouse_id, item_id=None,
                      product_sku_id=None, item_group_id=None) -> list[ItemLocationSlot]:
        # query by item_id; if none, by product_sku_id; if none, by item_group_id
        ...

    def bins_for_slot(self, slot) -> set[UUID]:
        # if slot.location_id is a bin -> {bin_id}
        # else -> SELECT id FROM warehouse_locations
        #          WHERE warehouse_id=? AND is_active AND location_type='bin'
        #            AND (<level column> = slot.location_id)   # zone_id / aisle_id / bay_id / level_id
        ...
```

`bins_for_slot` uses the denormalized column matching the slot location's
`location_type` — this is the replacement for `_descendant_bin_ids`.

### 5.5 Velocity classification job

Scheduled job (Celery beat / existing scheduler pattern):

```python
def classify_velocity(org_id, warehouse_id):
    cutoff = now() - timedelta(days=30)
    rows = (db.query(StockMovement.product_id,
                     func.sum(StockMovement.quantity))
              .filter(StockMovement.organization_id == org_id,
                      StockMovement.warehouse_id == warehouse_id,
                      StockMovement.movement_type.in_(OUTBOUND_TYPES),
                      StockMovement.performed_at >= cutoff)
              .group_by(StockMovement.product_id)
              .all())
    # rank by score, assign A/B/C via cumulative share (Pareto) or thresholds
    # write items.velocity_score / velocity_class / velocity_source='auto'
```

- Manual override: `PATCH /wms/velocity` sets `velocity_source='manual'`; the
  auto job skips manually-overridden rows until cleared.
- Thresholds stored in `system_config` (e.g. `wms.velocity.a_share=0.70`,
  `wms.velocity.b_share=0.20`).

### 5.6 Capacity caching & incremental refresh

`BinCapacityService.refresh_bin` already computes metrics, state and counts.
Persist the raw numbers on the bin row:

```python
bin_loc.occupied_volume_cc   = metrics["occupied_m3"] * CC_PER_M3
bin_loc.occupied_weight_grams = metrics["occupied_kg"] * G_PER_KG
bin_loc.unit_count_eaches    = units
bin_loc.master_pack_count    = packs
```

Incremental variant for stock movements:

```python
def apply_delta(bin_id, *, d_volume_cc, d_weight_g, d_units, d_packs):
    # UPDATE warehouse_locations SET
    #   occupied_volume_cc = COALESCE(occupied_volume_cc,0) + :dv, ...
    # THEN recompute pct / bin_state from the new totals (cheap arithmetic)
```

Reads then avoid `compute_bin_occupancy`:

- `get_available_bins` → one query on
  `location_type='bin' AND is_pickable AND bin_state != 'full'` plus optional
  `zone_id = :fast_zone` / `aisle_id = :lane`; no per-bin occupancy loop.
- `get_capacity_tree` → roll up cached columns up the tree in memory (the tree
  walk already happens; it just stops joining `bin_stock_levels`).

Full recompute (`refresh_warehouse`) stays for layout apply and as a nightly
reconciliation job to heal drift.

### 5.7 Suggestion engine changes

`LocationSuggestionService._score_put_away` changes:

1. Replace `_allocated_location_ids` / `_descendant_bin_ids` BFS with
   `SlottingService.resolve_slots(...)` + `bins_for_slot(...)`.
2. Candidate query filters by denormalized zone/aisle:
   ```python
   q = db.query(WarehouseLocation).filter(
       WarehouseLocation.warehouse_id == warehouse_id,
       WarehouseLocation.organization_id == org_id,
       WarehouseLocation.location_type == "bin",
       WarehouseLocation.is_active.is_(True),
       WarehouseLocation.is_pickable.is_(True),
       WarehouseLocation.bin_state != "full",
   )
   if fast_zone_id: q = q.filter(WarehouseLocation.zone_id == fast_zone_id)
   ```
3. Capacity check reads cached `occupied_volume_cc` / `occupied_weight_grams`
   (one row read) instead of `get_bin_capacity()` (occupancy recompute).
4. Scoring weight adds slot match:
   - `home` slot match: +100
   - `secondary`: +50
   - `overflow` / lane fallback: +25
   - existing: consolidation +20, group affinity +15, proximity (unchanged).

`_score_pick` optionally restricts candidates to slot lanes and keeps FEFO/FIFO.

### 5.8 New API endpoints (proposed)

| Method | Path | Purpose |
|---|---|---|
| POST | `/wms/slots` | create SKU↔bin/lane slot |
| GET | `/wms/slots?warehouse_id&item_id&location_id` | list slots |
| PATCH | `/wms/slots/{id}` | update slot (min/max, priority, type, active) |
| DELETE | `/wms/slots/{id}` | deactivate slot |
| POST | `/wms/velocity/classify` | trigger velocity job for a warehouse |
| PATCH | `/wms/velocity/{item_id}` | manual velocity override |

Permissions: `WAREHOUSE_MANAGE` for writes, `WAREHOUSE_READ` for reads (reuse
[`app/core/authorization.py`](../app/core/authorization.py)).

### 5.9 Indexes summary

- `warehouse_locations (organization_id, warehouse_id, location_type, zone_id, is_pickable, bin_state)`
- `warehouse_locations (organization_id, warehouse_id, location_type, aisle_id, is_pickable)`
- `items (organization_id, velocity_class)`
- `item_location_slots` — see §5.4.
- `stock_movements (organization_id, warehouse_id, movement_type, performed_at)` (if not present).

### 5.10 Concurrency & locking

- **Slot CRUD**: low contention; standard optimistic lock via `updated_at`.
- **Capacity cache updates**: single-writer per bin through `BinCapacityService`;
  use the existing row `version` column for optimistic locking and
  `SELECT ... FOR UPDATE` where a movement and a layout apply race on the same
  bin (consistent with [WMS_STOCK_CONCURRENCY_LOCKING.md](./WMS_STOCK_CONCURRENCY_LOCKING.md)).
- **Layout apply** continues using `pg_advisory_xact_lock('layout-apply:<wid>')`.

---

## 6. Rollout / migration plan

1. **Phase 1 — path denormalization + occupancy cache** (no behaviour change)
   - migrations + populate at apply + persist in `refresh_bin`
   - switch `get_available_bins` / `get_capacity_tree` to read cache
   - backfill via one `refresh_warehouse` run per warehouse
2. **Phase 2 — velocity fields + job** (behaviour-neutral until wired)
3. **Phase 3 — slotting table + service + API**
4. **Phase 4 — wire into suggestion engine + replenishment job**
5. **Phase 5 — UI** (zone purpose editor, slot manager, velocity override)

Each phase is independently shippable and reversible (feature-flag the scoring
changes if desired, using the existing feature-flag infra).

---

## 7. Performance targets & verification

| Read path | Current | Target |
|---|---|---|
| `/wms-3d/status` (bin states) | N bins × occupancy query | 1 query on cached columns |
| `/wms-3d/layout` tree rollup | recompute whole warehouse | cached per-bin + in-memory rollup |
| `/wms-3d/suggest` put-away | all-bins scan + N+1 | indexed candidate query + cached capacity |
| Ancestor resolution (zone→bins) | BFS, 1 query/node | 1 indexed query on `zone_id/aisle_id` |

Verification: SQL `EXPLAIN ANALYZE` on the new candidate queries; load test the
three endpoints before/after; assert `refresh_bin` cache equals a full
`compute_bin_occupancy` recompute in a reconciliation test.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Cached occupancy drifts from truth | Nightly `refresh_warehouse` reconciliation; cache rebuild on layout apply |
| Velocity misclassification (seasonality) | Manual override + configurable window/thresholds; classify in background, not on hot path |
| Slot conflicts (two SKUs same home bin) | Unique constraint on `(item, location, slot_type)`; resolution priority documented |
| Incremental updates lost on crash | Derive cache from `bin_stock_levels` if `NULL`; reconciliation job heals |
| Fast zone becomes full → put-away starved | Fall back to `slow_moving`/`reserve` when fast zone has no non-full bins |

---

## 9. Open questions

1. Should **SKU** slotting key on `item_id` (1:1 with `product_sku_id` via
   `Item.product_sku_id`) or on `product_sku_id` directly? Proposed: key on
   `item_id`, with `product_sku_id` as an alternate key for catalog-first UX.
2. Velocity window (30/60/90 days) and class thresholds — fixed or
   per-warehouse via `system_config`?
3. Does "lane" map to `aisle` or `bay` in the customer's terminology? The design
   works for either via the denormalized column chosen by slot `location_type`.
4. Replenishment trigger — purely `min_qty`, or also a fixed cadence?
