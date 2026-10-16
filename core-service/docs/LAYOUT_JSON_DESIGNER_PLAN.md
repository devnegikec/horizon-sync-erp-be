# JSON Layout Designer — Backend Implementation Plan

> Status: **Implementation in progress**
> Scope: `core-service` (FastAPI + SQLAlchemy 2.0 + PostgreSQL/Alembic)
> Related: `docs/3D_WAREHOUSE_VIEW_DESIGN.md`, `docs/WMS_LAYOUT_GUIDE.md`, `WMS_IMPLEMENTATION_PLAN.md`
> Companion doc (frontend): `horizon-sync/docs/LAYOUT_JSON_DESIGNER_PLAN.md`

---

## 1. Goal

Let a warehouse be **designed by importing a single JSON document** — building dimensions,
zones, aisles (with cross-aisles), rack lanes, levels, reserved bays, pillars/obstacles and
per-level capacity — then **validate it, preview it, and persist it** as the WMS location
hierarchy (`WarehouseLocation`, zone → aisle → bay → level → bin) with real 3D coordinates.

Everything that already consumes locations — the 3D view, capacity rollups, putaway
assignment, QR labels, reservations — must keep working unchanged.

### Non-goals

- Replacing the existing form-based designer (`FloorPlanConfig` / `AisleSpec`). It stays and
  remains the default. JSON import is an **additional authoring front-end** into the same
  `WarehouseLocation` outcome.
- Editing the layout document incrementally on the server (the document is authored
  client-side; the server validates, previews and applies it).

---

## 2. What already exists (reuse, don't rebuild)

| Concern | Existing asset |
|---|---|
| Hierarchy | `WarehouseLocation` (`parent_location_id`, `location_type`, `code`, `full_path`), `LocationType` enum |
| Plan storage | `WarehouseFloorPlan` (`config` JSONB, `is_active`, `generated_at`) |
| Code generation | `LayoutService` (`_build_raw_code`, `_generate_location_code`, `_generate_qr_code`) |
| Bulk generation | `FloorPlanGeneratorService` (`preview` / `apply` / soft-deactivate / QR batch) |
| 3D read model | `Warehouse3DService.get_layout()` reads `position_x/y/z` |
| Bin capacity | `BinCapacityService`, `capacity_math` (cc ⇄ m³), `max_volume_cc`, `max_weight_grams` |
| Live events | `app/core/redis_pubsub.py` → channel `warehouse:3d:{warehouse_id}` |
| Permissions | `WAREHOUSE_READ`, `WAREHOUSE_MANAGE` in `app/core/authorization.py` |

**The gap this plan fills:** there is no document format, no compiler, and no
diagnostics — geometry today is produced by a Python generator from a form-shaped config, so
nothing can be validated *before* it is written, and complex geometry (cross-aisles, pillars,
skipped bays, double-deep lanes) cannot be expressed at all.

---

## 3. The layout document (contract v1)

The document is the **input format**. It is authored by the frontend, hand-written by a
warehouse engineer, or exported from an existing design. Units are **metres everywhere**
(matching `position_x/y/z`). Field names are **camelCase** so the same JSON can be compiled by
the TypeScript engine in the frontend and this Python engine without translation.

```jsonc
{
  "schemaVersion": 1,
  "layout": { "namingScheme": "wms_typed", "defaultZoneCode": "01" },
  "warehouse": { "code": "WH1", "name": "…", "lengthM": 48, "widthM": 36, "heightM": 10,
                 "origin": { "x": 0, "z": 0 }, "metadata": {} },
  "rackTypes": [ { "id": "rt-std", "code": "STD", "bayWidthM": 2.7, "depthM": 1.1, "…": "…" } ],
  "obstacles":  [ { "kind": "PILLAR", "x": 6, "z": 18.7, "widthM": 0.8, "depthM": 0.8, "heightM": 10 } ],
  "aisles":     [ { "code": "A01", "zoneCode": "01", "orientation": "X",
                    "centerline": { "x1": 4, "z1": 6, "x2": 44, "z2": 6 },
                    "widthM": 3.4, "travelDirection": "BOTH",
                    "lanes": [ { "code": "A01-L", "side": "LEFT", "rackTypeId": "rt-std",
                                 "startOffsetM": 0, "lengthM": 40,
                                 "segments": [ { "kind": "RACK", "startM": 0, "endM": 16.2 },
                                               { "kind": "GAP",  "startM": 16.2, "endM": 21.6 } ],
                                 "levels": [ { "clearHeightM": 1.4, "binDepthM": 1.0,
                                               "beamHeightM": 0.08, "maxWeightKg": 800 } ],
                                 "skipBays": [3, 9],
                                 "binCodePattern": "{warehouse}/{aisle}/{side}/B{bay:03}/L{level}" } ] } ]
}
```

| Block | Meaning | WMS destination |
|---|---|---|
| `warehouse` | building envelope (`lengthM` along X, `widthM` along Z, `heightM` up) | `warehouses_extended` (matched by `code`) |
| `rackTypes[]` | bay pitch + rack depth; the physical racking | derived (bay/level sizing) |
| `obstacles[]` | `COLUMN \| PILLAR \| WALL \| OFFICE \| CUSTOM`, **minimum corner** `x,z` + box | stored in the plan JSON (no location rows) |
| `aisles[]` | a corridor: axis-aligned `centerline`, `widthM`, `travelDirection`, optional `zoneCode` | `WarehouseLocation(location_type='aisle')` |
| `lanes[]` | one rack row on one side of an aisle | `WarehouseLocation(location_type='bay')` |
| `levels[]` | a shelf level with clear height, usable depth and beam limit | `WarehouseLocation(location_type='level')` |
| **bins** | **derived, never authored** | `WarehouseLocation(location_type='bin')` |
| `metadata` | arbitrary per-entity fields | `WarehouseFloorPlan.config` |

### 3.1 Geometry rules the compiler enforces

1. **Bay count** = `floor(lane.lengthM / rackType.bayWidthM)`.
2. **A bay produces bins only when a `RACK` run covers the bay's centre**
   (`startOffsetM + (b + 0.5) × bayWidthM`). A `GAP` between two centres removes nothing —
   this is how a cross-aisle is expressed. Put the gap on a bay boundary and keep
   `endM − startM` a multiple of `bayWidthM`.
3. **Rack footprint** spans `widthM/2 … widthM/2 + depthM` perpendicular to the centreline on
   the lane's own side. `LEFT`/`RIGHT` follow the centreline direction, not the compass.
4. **Everything must be inside the footprint** — corridor and every bay.
5. **Level stack** `Σ(beamHeightM + clearHeightM) ≤ warehouse.heightM`.
6. Obstacles must not touch a corridor or a bay (error, not warning).

### 3.2 Diagnostics contract

A closed registry, single-sourced in Python and mirrored in TypeScript
(`apps/inventory/src/app/features/layout-designer/layout-core/rules.ts`). Each entry is
`{code, severity, description}`; **errors block apply, warnings do not.**

`NO_RACK_TYPES_DEFINED`, `AISLE_CODE_DUPLICATE`, `LANE_UNKNOWN_RACK_TYPE`,
`AISLE_ZERO_LENGTH`, `AISLE_NOT_AXIS_ALIGNED`, `AISLE_ORIENTATION_MISMATCH`,
`AISLE_OUT_OF_FOOTPRINT`, `AISLE_OBSTACLE_OVERLAP`, `LANE_RUN_EXCEEDS_AISLE`,
`LANE_OVERLAP`, `LEVEL_STACK_EXCEEDS_HEIGHT`, `BIN_OUT_OF_FOOTPRINT`,
`BAY_OBSTACLE_OVERLAP`, `BIN_CODE_DUPLICATE`, `SCHEMA_VERSION_UNSUPPORTED`,
`ZONE_CODE_DUPLICATE`, `LOCATION_PATH_ALREADY_EXISTS`
— plus warnings `AISLE_TOO_NARROW`, `AISLE_WITHOUT_LANES`, `LANE_ZERO_BAYS`,
`LANE_HAS_NO_RACK_SEGMENT`, `LEVEL_DEPTH_EXCEEDS_RACK`, `DIAGNOSTICS_TRUNCATED`.

Repeated instances of one code are capped (flood control) and summarised by
`DIAGNOSTICS_TRUNCATED`, mirroring how the WMS already caps repeated diagnostics.

---

## 4. Naming system (WMS-aligned)

The whole point of the import is that it produces **WMS codes**, not a parallel scheme.
`location_type` and `code` are written exactly as `LayoutService` would write them.

### Default scheme — `wms_typed` (LayoutService)

```
zone  Z01        code = "Z01"        full_path = "Z01"
aisle A03        code = "A03"        full_path = "Z01-A03"
bay   B02        code = "B02"        full_path = "Z01-A03-B02"
level L04        code = "L04"        full_path = "Z01-A03-B04-L04"
bin   BN001      code = "BN001"      full_path = "Z01-A03-B02-L04-BN001"
```

`TYPE_CODE_PREFIX = {zone: Z, aisle: A, bay: B, level: L, bin: BN}`, dash-joined, digits
zero-padded to 2 (bins to 3), display formatting (inserting the last dash, `BN-001`) stays a
read-time concern exactly as `LayoutService._format_full_path` does today.

### Mapping JSON → WMS hierarchy

| Document | WMS row | Code |
|---|---|---|
| `aisle.zoneCode` (default from `layout.defaultZoneCode`) | zone | `Z{nn}` |
| `aisle` (in document order) | aisle | `A{nn}` |
| `lane` (document order within its aisle) | bay | `B{nn}` — **lane 1 = LEFT = B01, lane 2 = RIGHT = B02** |
| `level` (array order) | level | `L{nn}` |
| each bay of each lane, per level | bin | `BN{nn}` — enumerates **along the row** |

> **The word "bay" means two different things, and this is the one place they meet.**
> In the *document*, a bay is a position along an aisle. In the *WMS*, a `bay` location is
> the **rack row itself** — that is how `FloorPlanGeneratorService` assigns its `B01`/`B02`
> side codes, and how it numbers bins (`BN{b:02d}` over the row's positions). So a document
> bay becomes a **bin** under a level, and a document **lane** becomes the WMS **bay**.
> That mapping is what makes the document's bin count equal the WMS bin count (240 bins in →
> 240 bin locations out), and it is verified by `test_layout_design_materialize.py`.

Lane order → bay number is deliberate: it reproduces both the current generator's
`B01`/`B02` rack-side convention *and* `LayoutService`'s numbered-bay convention, so no
existing consumer sees a different shape.

Level codes have **no authored analogue** in the document (levels are an array), so they are
always positional: `L01`, `L02`, … Both schemes agree on this.

### Columns populated per row

| Column | Value |
|---|---|
| `position_x`, `position_y` | plan-plane coordinates in metres (`x`, `z` of the compiler) |
| `position_z` | height in metres — the existing 3D view already reads this |
| `max_volume_cc` | `bayWidthM × binDepthM × clearHeightM × utilization` (85%), m³ → cc, bins only |
| `max_weight_grams` | `level.maxWeightKg × 1000`, bins only |
| `qr_code` | unique 5-char code from the existing alphabet, checked against the table in batches (bins only) |
| `is_pickable` | `true` for every rack bin (a `skipBays` entry yields no bin at all) |
| `is_active` | `true` on (re-)apply; `replace_existing` soft-deactivates the rest |
| `version` | bumped by 1 when an existing location is re-used, so the optimistic lock stays honest |

`capacity_uom` is set to `volume` to match the physical limits, keeping `total_capacity` /
`available_capacity` (unit-count semantics) at `0` so `CapacityService` is unaffected.

### Upsert semantics

Locations are matched by `full_path` — **never delete-and-recreate**, because placements and
`BinStockLevel` rows point at bin ids:

| Situation | Behaviour |
|---|---|
| path exists, same `location_type` | **updated in place**, id preserved, `is_active` restored |
| path absent | inserted |
| path exists, different `location_type` | blocked with `LOCATION_PATH_ALREADY_EXISTS` (400) |
| existing path not in the new document | left alone, or soft-deactivated when `replace_existing=true` |

---

## 5. Architecture

```
app/layout_design/                 # NEW pure package — no DB, no FastAPI
  schema.py        # Pydantic v2 models for LayoutDoc v1 + normalisation/defaults
  rules.py         # rule registry (code, severity, description)
  geometry.py      # axis-aligned AABB helpers (metres)
  compile.py       # build_layout(doc) -> CompiledLayout{bays, bins, diagnostics, summary}
  naming.py        # WMS code generation + QR alphabet + scheme switch
  materialize.py   # CompiledLayout + naming -> WarehouseLocation rows (no commit)
  migrate.py       # schemaVersion migrations
  examples.py      # the reference example document served to the frontend
app/schemas/layout_design.py       # request/response DTOs
app/api/v1/endpoints/layout_design.py  # validate / preview / apply / example / rules
app/services/layout_design_service.py  # orchestration: compile -> materialise -> persist
tests/test_layout_design_*.py
```

`app/layout_design/` is **pure and dependency-free** (metres in, diagnostics out) so it is
unit-testable without a database, exactly like the existing `capacity_math` module.

### Persistence

The imported document is stored in its own column, `warehouse_floor_plans.layout_doc`
(`JSONB`, nullable, migration `131`), with the summary and provenance in `config`:

```jsonc
// layout_doc column
{ …the validated document, verbatim… }

// config column
{ "source": "json_import",
  "naming_scheme": "wms_typed",
  "layout_doc_summary": { "bays": 101, "bins": 472, "aisles": 4, "lanes": 8, "levels": 24 } }
```

The column is deliberately separate from `config`, which keeps holding the form-shaped
`FloorPlanConfig` that `FloorPlanGeneratorService` writes — two different formats with two
different readers, so they should not share a key.

**No backfill is needed.** Rows written before the column existed keep their document in
`config["layout_doc"]`, and `LayoutDesignService.get_stored_document` prefers the column but
falls back to that key, so old and new rows both round-trip.

Getting there required first merging the two divergent migration heads (`129_bulk_put_away_jobs`
and `129_asn_short_delivery_close`) in revision `130`, which is why the column landed in `131`
rather than alongside the feature. `floor_plan_id` on `warehouse_locations` is still open.

---

## 6. API

Base `GET/POST /api/v1/layout-design` (registered in `app/api/v1/router.py`).

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/rules` | `warehouse.read` | rule registry so the UI can explain codes |
| `GET` | `/example` | `warehouse.read` | reference document (import template) |
| `POST` | `/validate` | `warehouse.read` | compile only → `{valid, summary, diagnostics}`; **no writes** |
| `POST` | `/preview` | `warehouse.read` | validate + naming sample + first N bins; **no writes** |
| `POST` | `/apply` | `warehouse.manage` | compile → materialise → persist locations + plan |
| `GET` | `/{floor_plan_id}/doc` | `warehouse.read` | the stored document, for round-tripping |

**Response envelope:** bare typed DTOs on success; failures use the existing
`{"detail": {"message", "status_code", "code"}}` shape, where `code` is the **rule code**
(`LAYOUT_DOC_INVALID`, `SCHEMA_VERSION_UNSUPPORTED`, …) — never a generic error string. This
matches the placement-refusal convention already in use.

`organization_id` always comes from `CurrentUser`; the warehouse is resolved from
`warehouse.code` **scoped to that organisation** (404 `WAREHOUSE_NOT_FOUND` otherwise) — the
organisation is never taken from the request body.

### Apply semantics

- `replace_existing: true` → previous locations for the warehouse are **soft-deactivated**
  (`is_active = false`), never hard-deleted, so historical stock/placement rows survive —
  the same rule `FloorPlanGeneratorService.apply` follows.
- Bins are **upserted by `full_path`**; a path that already exists with a different type is a
  blocked `LOCATION_PATH_ALREADY_EXISTS`.
- One transaction, one commit at the end.
- On success a `warehouse:3d:{id}` event is published so the open 3D view refreshes.

---

## 7. Task list

IDs are shared with the frontend plan so the two can progress in parallel.

| ID | Backend task | Depends on |
|---|---|---|
| **BE-1** | `app/layout_design/schema.py` — LayoutDoc v1 Pydantic models, defaults, normalisation | — |
| **BE-2** | `app/layout_design/rules.py` + `geometry.py` — rule registry, AABB helpers | — |
| **BE-3** | `app/layout_design/compile.py` — bay/bin derivation + diagnostics | BE-1, BE-2 |
| **BE-4** | `app/layout_design/naming.py` — WMS codes, QR alphabet, scheme switch | BE-1 |
| **BE-5** | `app/layout_design/materialize.py` + `service` — rows, transaction, event | BE-3, BE-4 |
| **BE-6** | `app/schemas/layout_design.py` + `endpoints/layout_design.py` + router | BE-5 |
| **BE-7** | *(follow-up)* merge Alembic heads → `layout_doc` column, `floor_plan_id` FK | heads merged |
| **BE-8** | Tests: compiler unit, conformance fixtures, naming, endpoints; `ruff` + `pytest` | BE-3…BE-6 |
| **BE-9** | `examples.py` reference documents + `docs/LAYOUT_JSON_DESIGNER_PLAN.md` examples | BE-1 |

---

## 8. Testing

- Pure compiler tests (`tests/test_layout_design_compile.py`) assert the **full diagnostics
  list** (code, severity, order) plus the derived bay/bin counts, over the reference document
  in `layout_design/examples.py` and ~20 focused mutations of it — the same "fixtures are the
  contract" discipline used for the WMS conformance suites.
- Naming tests assert exact `full_path` strings for both schemes.
- Endpoint tests (`tests/test_layout_design_endpoints.py`) run against a **sentinel session**,
  not a database: validate/preview/rules/examples are pure and a refused apply returns before
  any query, so a regression that starts querying fails loudly instead of skipping. Only the
  apply round-trip is DB-gated behind `RUN_DATABASE_TESTS=1`, as elsewhere in this suite.
- The frontend mirrors these expectations in its own jest suite over the same document
  (`apps/inventory/src/app/features/layout-designer/layout-core/__tests__/`), so a divergence
  fails on one side rather than reaching production.

---

## 9. Risks & decisions needing confirmation

1. **Naming scheme.** Default `wms_typed` (`Z01-A03-B02-L04-BN001`). The alternative,
   `wms_floorplan` (`A01-B01-L01-BN01`, what `FloorPlanGeneratorService` emits today), is
   selectable per document via `layout.namingScheme`. Two schemes exist in the codebase
   today; this plan does not unify them.
2. **Obstacles have nowhere to live.** `warehouse_locations` has no column for a pillar, so
   obstacles are preserved in the plan JSON only. If they must be queryable (e.g. for route
   avoidance), a `warehouse_obstacles` table is a new task.
3. **Zones are derived, not authored.** A document without explicit `zoneCode` values lumps
   every aisle into one default zone. Multi-zone warehouses should author `zoneCode`.
4. **Alembic heads** — the two `129` heads are merged in revision `130`, so the graph is linear
   again. Re-run `alembic heads` before adding the next migration; this repo has re-branched
   before.

---

## 10. Status

**Implemented and verified** (`81 tests passing`, 2 DB-gated tests skipped without
`RUN_DATABASE_TESTS=1`; `ruff` clean apart from 3 `C901` complexity notes that match the 85
pre-existing ones in `app/`):

| ID | Task | State |
|---|---|---|
| BE-1 | `layout_design/schema.py` — LayoutDoc v1, camelCase contract, defaults | ✅ |
| BE-2 | `layout_design/rules.py` + `geometry.py` — registry (24 rules), AABB helpers | ✅ |
| BE-3 | `layout_design/compile.py` — bays/bins/WMS paths/diagnostics, flood-capped | ✅ |
| BE-4 | `layout_design/naming.py` — both schemes, pattern rendering, batched QR | ✅ |
| BE-5 | `layout_design/materialize.py` + `services/layout_design_service.py` | ✅ |
| BE-6 | `schemas/layout_design.py` + `endpoints/layout_design.py` + router (7 routes) | ✅ |
| BE-8 | Unit tests: compiler (36), materialiser (18), service reads (14) | ✅ |
| BE-9 | `layout_design/examples.py` + this document | ✅ |
| BE-10 | `tests/test_layout_design_endpoints.py` — 13 endpoint tests on a sentinel session | ✅ |
| BE-11 | `publish_layout_event()`, published after the commit on `warehouse:3d:{id}` | ✅ |
| BE-7 | Merge heads (`130`) + `layout_doc` column (`131`); `floor_plan_id` FK still open | ◑ part |

### Verification commands

```bash
cd core-service
.venv/bin/python -m pytest tests/test_layout_design_compile.py \
    tests/test_layout_design_materialize.py tests/test_layout_design_service.py \
    tests/test_layout_design_endpoints.py -q --no-cov
ruff check app/layout_design app/services/layout_design_service.py
DATABASE_URL=sqlite:///:memory: .venv/bin/python -m alembic heads   # must print ONE head
```

> `alembic upgrade head` is **not** run as part of this work: it needs a live PostgreSQL.
> What *was* verified is that the revision graph loads, resolves to a single head
> (`131_add_floor_plan_layout_doc`), and that the new migration is guarded and idempotent.
> Note `--sql` (offline) mode cannot be used with this repo's `alembic_guards` helpers, since
> they need a live inspector — a pre-existing property of the guard pattern.

The compiler reproduces the reference cross-aisle document exactly: **3 aisles x 2 lanes x
(10 bays − 2 in the cross-aisle) x 5 levels = 240 bins over 60 bays**, with bins `BN005` and
`BN006` missing from every level — the same gap semantics the reference engine asserts.

### Deliberate deviations from the original sketch

1. **The refresh event is coarse by design.** `publish_bin_event` is bin-scoped, so a
   layout-level change gets its own `publish_layout_event` (no `bin_id`) rather than a
   mislabelled bin event; subscribers refetch the whole hierarchy.
2. **`binCodePattern` is a label, not an identity.** The document's pattern still renders
   (shown in preview), but a bin's persisted identity is always its WMS `full_path`. `{bay}`
   and `{level}` render **1-based** so `L{level}` reads as `L1`, not `L0`.
3. **`binsPerLevel` is not yet supported.** A document bay yields exactly one bin per level
   (`FloorPlanGeneratorService`'s `bins_per_level` is always 1 here).
4. **Zone ordinals come from the code** when it ends in digits (`"02"` → `Z02`), otherwise
   from position. Two zone codes resolving to the same ordinal raise `ZONE_CODE_DUPLICATE`.

