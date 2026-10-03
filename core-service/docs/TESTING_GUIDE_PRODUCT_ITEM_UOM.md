# Product / Item / UOM Redesign — Testing Guide

> **Branch:** `feature/product_item_uom_redesigning` (backend `horizon-sync-erp-be`)
> **Frontend:** `horizon-sync` — `apps/inventory` and `apps/platform`
> **Audience:** QA / manual testers
> **Date:** 2026-08-25

This guide covers every feature implemented in this branch, with concrete
examples (API payloads + UI steps) and expected results. Read the
"Prerequisites" section first, then test in the order given (features build on
each other).

---

## 0. Prerequisites

### 0.1 Running services

| Service | URL | Port |
|---|---|---|
| Identity Service | `http://localhost:8000` | 8000 |
| Core Service | `http://localhost:8001` | 8001 |
| Postgres | `postgres:5432` (db `railway`) | 5432 |
| Platform web app | `http://localhost:4200` | 4200 |
| Inventory web app | `http://localhost:4201` | 4201 |

Make sure containers are up and healthy:

```bash
cd horizon-sync-erp-be
docker compose up -d --build
docker compose ps        # all services should be Up (healthy)
```

### 0.2 Apply migrations + seed

```bash
docker exec horizon_core python -m alembic upgrade heads
docker exec horizon_core python seed_uoms.py
docker exec horizon_core python seed_packaging_types.py
docker exec horizon_core python seed_dual_mode_flags.py
```

Verify the migration head is `087_split_packaging_from_uoms`:

```bash
docker exec horizon_core python -m alembic heads
# expect: 087_split_packaging_from_uoms (head)
```

### 0.3 Get an access token

Log in through the web UI and copy the bearer token from the browser's network
tab / localStorage (`access_token`), or call the identity service directly:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<your-email>","password":"<your-password>"}'
```

Use the returned token for all core-service calls below:

```bash
export TOKEN="<paste-token>"
export CORE="http://localhost:8001/api/v1"
```

> **Tip:** the organization UUID used below (`147f3b9d-…`) is an example — use
> your own org's UUID (it's `user.organization_id` in the app).

---

## 1. Feature summary

| # | Feature | Where to test | Phase |
|---|---|---|---|
| F1 | UOM master (uom_type, precision, is_active) | DB / API | 0 |
| F2 | Packaging types master + item packaging FK | DB / API | 0 |
| F3 | Feature-flag dual-mode (9 tenant flags) | Settings → Feature Flags | 1 |
| F4 | Shared catalog core `products` | API | 2 |
| F5 | Variant reconciliation (Item ↔ ProductSKU) | API (flag-driven) | 3 |
| F6 | Sync-service removal (6 Qseal cols dropped) | DB / API | 4 |
| F7 | Bulk catalog import (3 modes) | Inventory → Bulk upload / API | 5 |
| F8 | Item approval workflow | Inventory item detail | 5 |
| F9 | Settings tabs (Org / Preferences / Flags / Items & UOM) | Platform → Settings | — |
| F10 | Items & UOM conversions (bulk edit + import) | Platform → Settings → Items & UOM | — |
| F11 | UOM scalability (global conversions, packaging split) | API / DB | 085–087 |

---

## F1 — UOM master (Phase 0)

**Description:** `uoms` now has `uom_type` (count/weight/volume/length/area/time),
`precision`, and `is_active`. Physical packaging units (BAG/BOX/…) were
deactivated and moved conceptually to `packaging_types`.

**Test steps:**

1. List UOMs:

```bash
curl -s "$CORE/uoms" -H "Authorization: Bearer $TOKEN" | jq '.uoms[] | {name, abbreviation, uom_type, precision, is_active}'
```

**Expected:** every active UOM has a non-null `uom_type` and a sensible
`precision` (e.g. `KG → weight/3`, `PCS → count/0`, `SQM → area/2`). Packaging
codes (`BAG, BOX, CTN, DRM, PLT…`) should have `is_active=false` or not appear.

2. Create a new UOM:

```bash
curl -s -X POST "$CORE/uoms" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Milliliter","abbreviation":"MLX","uom_type":"volume","precision":1}'
```

**Expected:** `201` with `uom_type="volume"`, `precision=1`.

---

## F2 — Packaging types master (Phase 0)

**Description:** new `packaging_types` table (8 seeded: `BAG, BOTTLE, BOX,
CARTON, CASE, DRUM, EACH, PALLET`), linked to a measurement UOM via `uom_id`.
`item_packaging_units` now has a `packaging_type_id` FK.

**Test steps:**

```bash
docker exec horizon_core python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as c:
    rows = c.execute(text('SELECT code, name, uom_id FROM packaging_types ORDER BY code')).fetchall()
    for r in rows: print(r[0], '|', r[1], '| uom_id:', r[2])
"
```

**Expected:** 8 rows, each with a non-null `uom_id` (migration 086 backfilled).

---

## F3 — Feature-flag dual-mode (Phase 1)

**Description:** 9 tenant-scoped flags drive WMS/Qseal/approval/variant
behaviour. Administrators can override them per tenant in
**Settings → Feature Flags**.

| Flag | Meaning | Default |
|---|---|---|
| `wms_enabled` | show WMS module | — |
| `qseal_enabled` | show QSeal module | — |
| `product_editable_manually` | allow manual product editing | — |
| `item_auto_create_product` | auto-create product on item create | — |
| `variant_structured_enabled` | structured variant axes | `true` |
| `auto_create_sku_on_item` | auto-create ProductSKU on item create | `false` |
| `auto_create_variant_axes` | auto-create missing axes | `false` |
| `require_item_approval` | require item approval | `false` |
| `auto_approve_single_create` | auto-approve single-item create | `true` |

**Test steps (API):**

1. Evaluate a flag:

```bash
curl -s "$CORE/feature-flags/evaluate/wms_enabled" -H "Authorization: Bearer $TOKEN"
# → {"feature_name":"wms_enabled","enabled":true|false,"visible":true}
```

2. List effective flags for your org:

```bash
curl -s "$CORE/feature-flags" -H "Authorization: Bearer $TOKEN" | jq '.flags[] | {name, enabled, visible, scope, inherited}'
```

**Expected:** each flag shows `scope="TENANT"` (override) or `scope="GLOBAL"`
with `inherited=true`.

3. Toggle a tenant override:

```bash
curl -s -X PUT "$CORE/feature-flags/require_item_approval" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"enabled":true}'
```

**Expected:** `200`; the flag now shows `scope="TENANT"`, `inherited=false`,
`enabled=true`.

**Test steps (UI):**

1. Platform → **Settings → Feature Flags**.
2. Confirm the 9+ flags are listed with **Enabled** and **Visible** toggles and
   an **Inherited (Global)** vs **Tenant Override** badge.
3. Toggle a flag → toast confirms; reload → value persists.
4. A user without `organization.update` should see the toggles disabled.

---

## F4 — Shared catalog core `products` (Phase 2)

**Description:** new `products` table + CRUD endpoints; `items.product_id` and
`qr_products.product_id` link WMS/Qseal records to one catalog row.

**Test steps:**

1. Create a product:

```bash
curl -s -X POST "$CORE/products" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Product","sku":"TP-001","gtin":"0123456789012","product_type":"both"}'
```

2. List products:

```bash
curl -s "$CORE/products" -H "Authorization: Bearer $TOKEN" | jq '.products[] | {name, sku, gtin, product_type}'
```

3. Update + delete:

```bash
curl -s -X PATCH "$CORE/products/<id>" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"is_active":false}'
curl -s -X DELETE "$CORE/products/<id>" -H "Authorization: Bearer $TOKEN"
```

**Expected:** CRUD succeeds; the product appears in list; delete returns `204`.

---

## F5 — Variant reconciliation (Phase 3)

**Description:** `items.product_sku_id` links a WMS variant item to its Qseal
`ProductSKU`. Behaviour is driven by 3 flags (see F3). Refer to the
"Variant flags — behaviour matrix" in
`PRODUCT_ITEM_IMPLEMENTATION_PLAN.md §14`.

**Guards (always apply):** a ProductSKU is only auto-created when the item is a
**concrete variant child** (`variant_of` set, not `has_variants=true`), has a
`qr_product_id`, has non-empty `variant_attributes`, and is not already linked.
It is idempotent (reuses an existing SKU with the same `sku_code`).

**Test scenarios (pick the flag combination you want, then create a child item):**

1. **Legacy JSONB** (`variant_structured_enabled=false`): create child item with
   `variant_attributes` → no `product_skus` row is created, `product_sku_id` stays NULL.
2. **Manual link** (`structured=true`, `auto_create_sku_on_item=false`): create
   item with `product_sku_id` → `variant_attributes` is one-way synced from the SKU.
3. **Auto SKU, existing axes only** (`structured=true`, `auto_create_sku=true`,
   `auto_create_axes=false`): unknown attribute keys are skipped.
4. **Full auto** (`structured=true`, both auto flags true): missing axes are
   auto-created and linked.

Verify with:

```bash
curl -s "$CORE/items/<child-item-id>" -H "Authorization: Bearer $TOKEN" \
  | jq '{product_sku_id, variant_attributes, variant_of, has_variants}'
```

---

## F6 — Sync-service removal (Phase 4)

**Description:** `product_item_sync_service.py` deleted; 6 Qseal-only mirror
columns dropped from `items` (`industry`, `landing_page`, `warranty_period_months`,
`qr_type`, `activation_method`, `sr_number_type`).

**Test steps:**

```bash
docker exec horizon_core python -c "
from app.database import engine
from sqlalchemy import inspect
cols = {c['name'] for c in inspect(engine).get_columns('items')}
dropped = ['industry','landing_page','warranty_period_months','qr_type','activation_method','sr_number_type']
print('dropped present:', [c for c in dropped if c in cols] or 'NONE (correct)')
print('brand_id/gtin kept:', 'brand_id' in cols, 'gtin' in cols)
"
```

**Expected:** the 6 dropped columns are absent; `brand_id` and `gtin` remain.

---

## F7 — Bulk catalog import (Phase 5)

**Description:** one engine, three modes; idempotent upsert on `(org, sku)`
falling back to `(org, gtin)`; per-row error report.

**Modes:**
- `product_only` — creates/updates catalog products only.
- `product_with_items` — products + linked inventory items.
- `item_with_auto_product` — items; auto-creates a product per item when the
  `item_auto_create_product` flag is on.

**Test steps (API):**

```bash
curl -s -X POST "$CORE/catalog-import" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{
    "mode": "product_with_items",
    "rows": [
      {"name":"Widget A","sku":"WDG-A","uom":"PCS","item_code":"ITM-WDG-A","has_batch_no":false,"has_serial_no":false},
      {"name":"Widget B","sku":"WDG-B","uom":"BOX","item_code":"ITM-WDG-B","has_batch_no":true,"has_serial_no":false}
    ]
  }'
```

**Expected:** `{created: 2, updated: 0, errors: []}`.

Run the **same** request again → `{created: 0, updated: 2, errors: []}` (idempotent).

Introduce a bad row and confirm per-row errors:

```bash
curl -s -X POST "$CORE/catalog-import" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{
    "mode": "product_only",
    "rows": [
      {"name":"Good","sku":"GOOD-1"},
      {"name":""}   # invalid: name required
    ]
  }'
```

**Expected:** `created=1`, and `errors` contains `{row:1, error:"…name…"}`.

**Test steps (UI):**

1. Inventory app → **Items** → **Bulk upload** button.
2. Choose a mode, paste a JSON array of rows, click **Import**.
3. Confirm created/updated/errors panel shows counts and per-row errors.

---

## F8 — Item approval workflow (Phase 5)

**Description:** items can be `draft → pending_approval → active/inactive` (or
rejected). Controlled by `require_item_approval` (default off) and
`auto_approve_single_create` (default on).

**Setup:** set `require_item_approval=true` (see F3).

**Test steps (API):**

1. Create an item (status becomes `draft` when approval is required):

```bash
curl -s -X POST "$CORE/items" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_code":"ITM-APP-1","item_name":"Approval Test","item_type":"stock","uom":"PCS","maintain_stock":false,"status":"draft"}' \
  | jq '{id, status}'
```

2. Submit → approve:

```bash
curl -s -X POST "$CORE/items/<id>/submit"  -H "Authorization: Bearer $TOKEN" | jq '.status'
curl -s -X POST "$CORE/items/<id>/approve" -H "Authorization: Bearer $TOKEN" | jq '.status'
```

**Expected:** `submit` → `pending_approval`; `approve` → `active`.

3. Reject path:

```bash
curl -s -X POST "$CORE/items/<id>/reject" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"reason":"missing data"}' | jq '{status, rejection_reason}'
```

**Expected:** status returns to `draft` (or stays pending) with
`rejection_reason` set.

**Test steps (UI):**

1. Inventory → **Items** list: status column shows badges for `draft`,
   `pending_approval`, `discontinued` (not just active/inactive).
2. Open an item in **draft** → **Submit for Approval** button appears.
3. Open an item in **pending_approval** → **Approve** and **Reject** buttons;
   reject asks for a reason.
4. With `require_item_approval=false`, no approval buttons appear.

---

## F9 — Settings tabs reorganization

**Description:** the platform Settings page is split into relevant tabs
(no more "everything in General"), and the Banking tab was removed.

**Test steps (UI):**

1. Platform → **Settings**.
2. Confirm tabs: **Organization · Preferences · Feature Flags · Items & UOM**.
3. **Organization** — org details + document address (edit address → Save).
4. **Preferences** — currencies and units of measure (UOM list, add/delete).
5. **Feature Flags** — the F3 toggle UI.
6. Confirm the **Banking** tab is no longer visible.

---

## F10 — Items & UOM conversions (bulk edit + import)

**Description:** a Settings tab listing items with their UOM conversion factors;
supports manual editing (Save All) and bulk JSON import. Backed by
`PUT /api/v1/uom-conversions/bulk`.

**Test steps (UI):**

1. Platform → **Settings → Items & UOM**.
2. Confirm items load with their base UOM and any existing conversion rows
   (Item · From UOM · To UOM · Factor).
3. **Add Conversion** → pick item, from UOM, to UOM, factor → **Save All**.
4. **Bulk Import** → paste:

```json
[
  {"item_id":"<item-uuid>","from_uom":"PCS","to_uom":"BOX","conversion_factor":12},
  {"item_id":"<item-uuid>","from_uom":"KG","to_uom":"GM","conversion_factor":1000}
]
```

5. Click **Import** → success toast with created/updated counts; rows appear.

**Test steps (API):**

```bash
curl -s -X PUT "$CORE/uom-conversions/bulk" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{
    "conversions": [
      {"item_id":"<item-uuid>","from_uom":"PCS","to_uom":"BOX","conversion_factor":12}
    ]
  }'
```

**Expected:** `{created:1, updated:0, errors:[]}`; re-run → `updated:1`.

---

## F11 — UOM scalability (migrations 085–087)

**Description:** global (item-less) conversions with runtime fallback,
`uom_type`/`precision` backfill, packaging split, ID-based uniqueness.

**Test steps:**

1. **Global conversion fallback** — create a global conversion (no `item_id`) and
   confirm `convert_quantity` uses it:

```bash
curl -s -X POST "$CORE/uom-conversions" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"from_uom":"KG","to_uom":"GM","conversion_factor":1000}'
```

   (Note: `item_id` is now optional — omit it for a global conversion.)

2. **Packaging split** — confirm physical-pack UOMs are inactive:

```bash
docker exec horizon_core python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as c:
    r = c.execute(text(\"SELECT COUNT(*) FROM uoms WHERE is_active=false\")).scalar()
    print('inactive uoms:', r)
"
```

**Expected:** `> 0` (39 physical-pack units deactivated), measurement UOMs active.

3. **ID-based uniqueness** — confirm the index exists:

```bash
docker exec horizon_core python -c "
from app.database import engine
from sqlalchemy import inspect
print([i['name'] for i in inspect(engine).get_indexes('uom_conversions')])
"
```

**Expected:** `uq_uom_conv_org_item_ids` present.

---

## 12. Infrastructure

- `core-service/requirements.txt` now pins `requests` (used by QR activation).
- `docker-compose.yml` runs core migrations with `alembic upgrade heads` (plural).
- `identity-service/.../workers.py` — fixed a duplicate `list_workers`
  signature (service starts cleanly).

**Smoke check:** both containers healthy:

```bash
docker compose ps   # identity-service + core-service Up (healthy)
curl -s http://localhost:8001/health   # 200
```

---

## 13. Quick smoke-test checklist (one-pager)

- [ ] `alembic heads` → single head `087_split_packaging_from_uoms`
- [ ] `/health` → 200
- [ ] `GET /uoms` → active UOMs typed (uom_type/precision set)
- [ ] `POST /products` → product created
- [ ] `POST /catalog-import` (product_with_items) → created; re-run → updated
- [ ] `POST /items` → item created with `base_uom_id` resolved from `uom`
- [ ] `POST /items/{id}/submit|approve|reject` → status transitions
- [ ] `GET /feature-flags` → 9 dual-mode flags; `PUT` override persists
- [ ] `PUT /uom-conversions/bulk` → bulk upsert works; global (no item_id) allowed
- [ ] Platform Settings → 4 tabs render; Feature Flags toggles work; Items & UOM edits work
- [ ] Inventory → Items shows draft/pending_approval badges + approval actions
- [ ] Inventory → Bulk upload dialog imports JSON rows

---

## 14. Known limitations / deferred (out of scope)

1. `items.uom` and `item_packaging_units.unit_name` remain as **legacy cache
   columns** (kept for backward compatibility) — dropping them is a separate,
   larger refactor.
2. `QRProduct` still carries Item-sourced mirror columns (no longer synced).
3. Physical-pack UOM `PK` remains active because item `ITM-2026-00016`
   ("Refrigrator") uses it as base UOM.
4. `convert_quantity` resolution uses name caches with ID-based fallback for
   duplicate checks; fully ID-driven lookups are partially in place.
