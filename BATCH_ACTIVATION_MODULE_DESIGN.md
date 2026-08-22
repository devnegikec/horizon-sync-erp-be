# Batch & Activation Module — Design Document (QSeal)

> **Status:** Design / planning (no code changes yet).
> **Date:** 2026-08-21
> **Scope:** New **Batch (D-Batch) + QR Activation** module for the QSeal app in `horizon-sync-be` (FastAPI) + `horizon-sync` (web) + `bwmobile` (mobile).
> **Reference:** This adapts the Django reference implementation documented in `QR_ACTIVATION_FLOW.md` (`app/integration/`) into the current FastAPI architecture.

---

## 1. Goal

Add a **Batch & Activation** module where an authorized user can:

1. Define a **production batch (D-Batch)** and attach **product production information**:
   - batch / lot name
   - manufacturing date
   - expiry date (auto-computed from shelf life)
   - **location where it is created** (production site / facility / plant)
   - manufacturing unit, destination market + currency, MRP, batch capacity
2. **Activate** individual QR codes (serial numbers) against that batch — copying the batch's manufacturing details onto each unit and flipping the unit to "active".
3. **Deactivate** a batch or a single unit.

---

## 2. Current state (what already exists vs what is missing)

### Already exists in the FastAPI project

| Concept | Where |
|---|---|
| Product master with `activation_method` (`pre`/`post`), `warranty_period_months`, `sr_number_type`, `gtin`, `item_code` | `app/models/qr_product.py` (`QRProduct`) |
| Individual QR unit with `serial_number` and activation flags (`qr_deactive`, `qr_deactive_unit`, `qr_active`) | `app/models/product_item.py` (`ProductItem`) |
| Per-unit manufacturing metadata (`manufacturing_date`, `expiry_date`, `manufacturing_unit`, `dispatch_batch`, `destination_market`, `mrp`, `currency`, `batch_size`, `qseal_settings`) | `app/models/qseal.py` (`QSealParameters`) |
| Physical container hierarchy (shipper / pallet / container) | `app/models/qseal.py` (`QSealTrack`) |
| QSeal parent/child CRUD, map, scan, history, labels, linked-units | `app/api/v1/endpoints/qseal.py` |
| QR blocks (generated QR batches) | `QRBlock`, `app/api/v1/endpoints/qr_products.py` |
| Destination markets + currency | `app/models/destination_market.py` (`destinations.py`) |

### Missing (what this module adds)

| Gap | Description |
|---|---|
| **D-Batch CRUD** | No API/UI to create, list, edit, clone, or deactivate batch-level manufacturing settings |
| **Activation flow** | No scan → validate → copy-details-to-unit → mark-active flow |
| **Unit activation state** | `ProductItem` has the flags, but no service/endpoint toggles them during activation |
| **Batch MRP/price management** | No endpoint to view/update batch MRP |
| **Activation counts** | No aggregated "activated / remaining / capacity" per batch |
| **Production location** | No field for "where the batch was created" (facility/plant) |

---

## 3. Concept mapping (Django reference → FastAPI)

| Django (`app/integration/`) | FastAPI equivalent | Notes |
|---|---|---|
| `QRActivationParameters` (D-Batch, `qr_settings=True`) | `QSealParameters` (`qseal_settings=True`) | Batch-level settings row |
| `QRActivationParameters` (unit, `qr_settings=False`) | `QSealParameters` (`qseal_settings=False`) | Per-unit manufacturing details |
| `ProductItem` | `ProductItem` | Same name + flags |
| `Product` | `QRProduct` | `activation_method`, `warranty_period_months` |
| `Order` (batch of QRs) | `QRBlock` | QR block |
| `DestinationMarket` | `DestinationMarket` | Market + currency |
| `WarrantyPeriod.number_of_years` | `QRProduct.warranty_period_months` | Expiry computation |
| `SerialNumFormat.serial_prefix` | `QRProduct.sr_number_type` | Serial prefix |

**Decision:** Reuse the existing `QSealParameters` table for both roles (batch config + unit activation), mirroring the Django single-table design — the `qseal_settings` boolean already exists for exactly this purpose.

---

## 4. Data model changes (proposed migration)

### 4.1 Reuse `QSealParameters` (dual-purpose)

- `qseal_settings = True` → **D-Batch config** row.
- `qseal_settings = False` → **per-unit activation** row (linked to the batch via `dispatch_batch` + `product_id`).

### 4.2 Add columns to `QSealParameters`

| Column | Type | Purpose |
|---|---|---|
| `status` | `String(20)` default `'active'` | Batch lifecycle: `draft` / `active` / `suspended` / `archived` |
| `history` | `Boolean` default `False` | Superseded batch configs (kept for audit) |
| `production_location` | `String(150)` nullable | **Location where the batch is created** (plant/facility/site) |
| `production_line` | `String(100)` nullable | Optional production line |
| `activated_at` | `DateTime(tz)` nullable | When the unit was activated |
| `activated_by` | `UUID` nullable | Who activated |
| `deactivated_at` | `DateTime(tz)` nullable | When deactivated |

### 4.3 Optional industry-standard fields (stored in existing `extra_data` JSONB)

| Field | Purpose |
|---|---|
| `storage_condition` | e.g. "Keep below 25°C" |
| `country_of_origin` | Country of manufacture |
| `cost_price` | Production cost (MRP already exists) |
| `license_no` / `reg_no` | Regulatory license (FSSAI / FDA / CE) |
| `batch_type` | `production` / `import` / `rework` |

> Rationale: keep the schema lean; put free-form/compliance fields in `extra_data` and only promote columns that are queried/aggregated (`status`, `history`, `production_location`).

### 4.4 `ProductItem` (already present — no change)

Reuse `qr_deactive`, `qr_deactive_unit`, `qr_active` to represent activation state, plus `scan_date`/`scans` for activation audit.

### 4.5 `QRProduct` (optional)

Add `num_activated_qr` (Integer) for a denormalized activation counter, or derive it from a `COUNT(ProductItem WHERE qr_active = true)`. **Recommend:** derive it (no column) to avoid drift.

---

## 5. Backend APIs (14 endpoints, 4 groups)

New router file: `core-service/app/api/v1/endpoints/qseal_batch.py`
Base path: `/api/v1/qseal`

### Group 1 — Batch (D-Batch) settings

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | `POST` | `/batches` | Create D-Batch settings (product + manufacturing details + capacity) |
| 2 | `GET` | `/batches` | List batches (filter: product, status; paginated) |
| 3 | `GET` | `/batches/{batch_id}` | Batch detail + activated/remaining/capacity counts |
| 4 | `PATCH` | `/batches/{batch_id}` | Update batch (versioned: mark old `history=True`, create new) |
| 5 | `POST` | `/batches/{batch_id}/clone` | Clone an existing batch (prefilled for re-use) |
| 6 | `POST` | `/batches/{batch_id}/deactivate` | Deactivate a batch (all its units) |
| 7 | `PATCH` | `/batches/{batch_id}/mrp` | Update batch MRP |

### Group 2 — Lookups

| # | Method | Path | Purpose |
|---|---|---|---|
| 8 | `GET` | `/batches/currency?destination_market_id=` | Resolve currency for a market |
| 9 | `GET` | `/batches/expiry?product_id=&manufacturing_date=` | Compute expiry + return serial prefix / existing config |

### Group 3 — Activation

| # | Method | Path | Purpose |
|---|---|---|---|
| 10 | `POST` | `/activation/scan` | Validate a scanned serial (pre-activation check) |
| 11 | `POST` | `/activation/batch` | Activate a list of serials against a batch (copy details + mark active) |
| 12 | `POST` | `/activation/single` | Activate a single serial |
| 13 | `POST` | `/activation/deactivate-unit` | Deactivate a single unit |
| 14 | `GET` | `/activation/units?serial=` | Get unit activation status/details |

### Request/response sketches

**POST `/batches`** (request)
```json
{
  "product_id": "uuid",
  "dispatch_batch": "MP-AUG-2026-B12",
  "batch_size": 100,
  "manufacturing_date": "2026-08-21",
  "manufacturing_unit": "Plant A — Hosur",
  "production_location": "Plant A, Hosur, TN",
  "production_line": "Line 3",
  "destination_market": "India",
  "currency": "INR",
  "mrp": 1299.00,
  "expiry_date": "2027-08-21",
  "append_to_existing": false
}
```

**POST `/activation/scan`** (response)
```json
{
  "serial_number": "4T6AKZ",
  "status": "valid | duplicate | already_active | limit_exceeded | not_found",
  "product_id": "uuid",
  "batch_id": "uuid",
  "message": "Ready to activate"
}
```

**POST `/activation/batch`** (request/response)
```json
{ "batch_id": "uuid", "serial_numbers": ["4T6AKZ", "DU3WIW"] }
→ { "activated": 2, "failed": [], "activated_serials": [...] }
```

---

## 6. Business rules (from the reference + industry standard)

| Rule | Enforced in |
|---|---|
| A D-Batch must exist before scanning/activating | `activation/scan`, `activation/batch` |
| Duplicate `dispatch_batch` + `product` requires append confirmation | `POST /batches` |
| `batch_size` cannot exceed available inactive units | `POST /batches` |
| Batch capacity (`activated >= batch_size`) blocks further activation | `activation/scan` |
| Already-activated serial returns its stored details (no double-activate) | `activation/scan` |
| Scanned units in one activation session must be the same product | `activation/batch` |
| Activated count cannot exceed total generated QR quantity | `activation/batch` |
| Old batch configs retained with `history=True` | `PATCH /batches` |
| Expiry = manufacturing date + `QRProduct.warranty_period_months` | `batches/expiry` |
| Deactivation decrements active counts (batch or unit) | `deactivate` endpoints |

---

## 7. Frontend flow

### 7.1 Web (`horizon-sync` → QSeal page)

Add a new tab/section **"Batch & Activation"** (next to QSeal Products, Blocks, Analytics).

**Tab A — Batches**
- Table: Batch name, Product, Mfg date, Expiry, Production location, Batch size, Activated / Remaining, MRP, Status.
- Actions: **New Batch**, **Edit**, **Clone**, **Change MRP**, **Deactivate**.
- **New/Edit dialog** (form sections):
  1. Product Information (product, batch name, batch size)
  2. Manufacturing Details (manufacturing date, expiry auto-computed, manufacturing unit, **production location**, production line)
  3. Market & Pricing (destination market → auto currency, MRP)
  4. Validity (warranty months → auto expiry)

**Tab B — Activation**
- Scanner input (keyboard + camera) → list of scanned serials with per-serial status (valid / duplicate / already active / limit).
- **Activate** button → calls `POST /activation/batch` → shows activated/failed summary.
- Per-serial "already activated" shows its stored manufacturing details.

**Tab C — Units** (optional)
- List activated units for a batch (serial, mfg/expiry, location, status), with **Deactivate unit** action.

### 7.2 Mobile (`bwmobile`)

New screen **Batch Activation** (operator line flow):
1. Select a batch (list from `GET /batches`).
2. Scan unit serials (camera) → status list.
3. Tap **Activate** → `POST /activation/batch`.
4. Success/error toasts per serial.

> Batch *setup* stays on web (admin/QC role); batch *activation* scanning is on mobile (line operator). The existing `QsealCascadeScreen` stays unchanged.

---

## 8. RBAC / Permissions

New permission codes in `core-service/app/core/authorization.py`:

| Code | Purpose |
|---|---|
| `qseal_batch.read` | View batches, units |
| `qseal_batch.create` | Create/clone batch |
| `qseal_batch.update` | Edit batch, change MRP |
| `qseal_batch.delete` | Deactivate batch/unit |
| `qseal_activation.execute` | Scan + activate units |

These plug into the new WMS roles seeded in `WMS_GAP_ANALYSIS_AND_ROADMAP.md` (e.g. *Inbound Operator* / *Quality Operator* get `qseal_batch.read` + `qseal_activation.execute`; *Warehouse Admin* gets all).

---

## 9. Implementation phases

| Phase | Work | Size |
|---|---|---|
| 1 | Alembic migration (`status`, `history`, `production_location`, `production_line`, `activated_at/by`, `deactivated_at`) | S |
| 2 | `qseal_batch` service + repository + schemas | M |
| 3 | 14 endpoints + RBAC codes + seed permissions | M |
| 4 | Web UI (Batches tab, Activation tab, dialogs) | M |
| 5 | Mobile activation screen + service methods | M |
| 6 | Tests (batch lifecycle, activation, capacity/duplicate rules) | M |

---

## 10. Open questions

1. **Production location** — free-text facility name (`production_location`), or a real FK to `warehouse_locations` (physical site/bins)? Recommend free-text for now, FK later if site-level reporting is needed.
2. **Activation method** — do you need both `pre` (batch created before activation) and `post` (details entered during activation)? The reference supports both via `Product.activation_method`.
3. **Mobile scope** — is the line-operator activation scanning needed on mobile now, or web-only first?
4. **Regulatory fields** — which compliance fields matter (FSSAI/FDA, country of origin, storage condition)?

---

## 11. Key file references

- Models: `core-service/app/models/qseal.py`, `product_item.py`, `qr_product.py`
- Existing QSeal API: `core-service/app/api/v1/endpoints/qseal.py`
- Existing QSeal service: `core-service/app/services/qseal_service.py`
- Reference Django flow: `QR_ACTIVATION_FLOW.md`
- Web QSeal UI: `horizon-sync/apps/inventory/src/app/components/qseal/`
- Mobile QSeal: `bwmobile/src/screens/QsealCascadeScreen.tsx`, `bwmobile/src/api/qsealService.ts`
