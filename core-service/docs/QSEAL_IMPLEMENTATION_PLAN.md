# QSeal Parent-Child Relationship System — Implementation Plan

> **Status:** QSeal module does NOT exist yet. Only a feature flag constant `QSEAL_MODULE_ENABLED = "qseal_module_enabled"` is defined in `core-service/app/core/constants.py`.
>
> **Goal:** Build a complete QSeal parent-child hierarchy system mirroring the existing Cascade QR (`/cascade-qr`) module.

---

## 1. What Already Exists (Reference: Cascade QR Module)

The Cascade QR module is a fully implemented parent-child hierarchy system that the QSeal module should mirror. Here's what it provides:

### 1.1 Models (`core-service/app/models/`)

| File | Model | Table | Purpose |
|------|-------|-------|---------|
| `qr_activation.py` | `QRActivationTrack` | `qr_activation_tracks` | Hierarchical container (shipper/pallet/container) with self-referential `parent_id` and `parent_app_id` FKs |
| `qr_activation.py` | `QRActivationParameters` | `qr_activation_parameters` | Individual unit parameters linked to shipper-level parents |
| `product_item.py` | `ProductItem` | `product_items` | Atomic QR block with serial number and scan counts |

### 1.2 Endpoints (`core-service/app/api/v1/endpoints/cascade_qr.py`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/cascade-qr/parents` | Create a parent QR node (pallet, carton, etc.) |
| `GET` | `/cascade-qr/parents` | List parent QR nodes (paginated, filterable by type) |
| `GET` | `/cascade-qr/parents/{node_id}` | Get a single parent QR node |
| `POST` | `/cascade-qr/parents/{parent_id}/children` | Create a child QR node under a parent |
| `GET` | `/cascade-qr/parents/{parent_id}/children` | List children under a parent (paginated) |
| `POST` | `/cascade-qr/parents/{parent_id}/map` | Map existing unattached children to a parent (bulk) |
| `POST` | `/cascade-qr/scan` | Record a cascade QR scan (public, no auth) |
| `GET` | `/cascade-qr/history` | Get cascade scan history (paginated, filterable by serial) |
| `GET` | `/cascade-qr/parents/{parent_id}/labels` | Download label data for all children of a parent |

### 1.3 Service Layer (`core-service/app/services/cascade_qr_service.py`)

- `CascadeQRService` class with methods: `create_parent`, `list_parents`, `get_parent`, `create_child`, `list_children`, `map_children`, `record_cascade_scan`, `get_scan_history`, `get_labels`
- Uses `CascadeQRRepository` for data access

### 1.4 Repository (`core-service/app/repositories/cascade_qr_repository.py`)

- `CascadeQRRepository` with methods: `create_node`, `get_by_id`, `get_by_serial`, `list_roots`, `list_children`, `count_children`, `map_children`, `generate_serial`, `record_scan`, `list_scan_history`

### 1.5 Schemas (`core-service/app/schemas/cascade_qr.py`)

- `ParentQRCreate`, `ParentQRResponse`, `ParentQRListResponse`
- `ChildQRCreate`, `ChildQRListResponse`
- `MapQRRequest`, `MapQRResponse`
- `CascadeScanRequest`, `CascadeScanResponse`
- `CascadeHistoryItem`, `CascadeHistoryResponse`
- `LabelDownloadResponse`

### 1.6 Router Registration (`core-service/app/api/v1/router.py`)

```python
api_router.include_router(
    cascade_qr.router,
    prefix="/cascade-qr",
    tags=["Cascade QR"],
)
```

---

## 2. What Needs to Be Created for QSeal

The QSeal module requires **7 new files** and **2 modifications** to existing files, following the exact same pattern as Cascade QR.

### 2.1 New Files (7 files)

| # | File | Purpose |
|---|------|---------|
| 1 | `core-service/app/models/qseal.py` | SQLAlchemy models: `QSealTrack`, `QSealParameters` |
| 2 | `core-service/app/schemas/qseal.py` | Pydantic schemas for QSeal API |
| 3 | `core-service/app/repositories/qseal_repository.py` | Data access layer for QSeal |
| 4 | `core-service/app/services/qseal_service.py` | Business logic for QSeal |
| 5 | `core-service/app/api/v1/endpoints/qseal.py` | FastAPI router with all QSeal endpoints |
| 6 | `core-service/app/api/v1/endpoints/qseal_scan.py` | (Optional) Separate public scan endpoint |
| 7 | `QSEAL_PARENT_CHILD_GUIDE.md` | Documentation (mirror of `parent_child_qr_code.md`) |

### 2.2 Modified Files (2 files)

| # | File | Change |
|---|------|--------|
| 1 | `core-service/app/api/v1/router.py` | Register `qseal` router with prefix `/qseal` |
| 2 | `core-service/app/models/__init__.py` | Import new QSeal models (if needed for Alembic) |

---

## 3. Detailed Model Design

### 3.1 `QSealTrack` — The Hierarchy Container Model

Mirrors `QRActivationTrack` with QSeal-specific naming.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `UUID` (PK) | Primary key |
| `organization_id` | `UUID` (indexed) | Tenant isolation |
| `qseal_type` | `String(25)` | Level: `"shipper"`, `"pallet"`, or `"container"` |
| `name` | `String(20)` | Alphanumeric label (max 20 chars) |
| `capacity` | `Integer` | How many children this container can hold |
| `serial_number` | `String(10)` | Unique identifier (8-10 chars) |
| `qseal_code_link` | `Text` | URL to download/download the QSeal label |
| `app_cascade_map` | `Boolean` (default=False) | Flag: `True` when parent has been cascaded via mobile app |
| `parent_id` | `FK → self` (nullable) | **Dashboard hierarchy** — links child → parent |
| `parent_app_id` | `FK → self` (nullable) | **App cascade hierarchy** — links child → parent via mobile app |
| `created_at` | `DateTime(tz=True)` | Creation timestamp |

**Self-referential relationship:**
```python
children = relationship(
    "QSealTrack",
    foreign_keys=[parent_id],
    backref="parent",
    remote_side=[id],
)
```

### 3.2 `QSealParameters` — Individual Unit/Shipper Parameters

Mirrors `QRActivationParameters` for QSeal-specific activation data.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `UUID` (PK) | Primary key |
| `organization_id` | `UUID` (indexed) | Tenant isolation |
| `product_id` | `FK → qr_products.id` (nullable) | Associated product |
| `block_id` | `FK → qr_blocks.id` (nullable) | Associated QR block |
| `serial_number` | `String(75)` | Unique serial identifier |
| `manufacturing_date` | `Date` | Date of manufacture |
| `expiry_date` | `Date` | Expiry date |
| `manufacturing_unit` | `String(100)` | Manufacturing unit/location |
| `dispatch_batch` | `String(100)` | Dispatch batch identifier |
| `destination_market` | `String(100)` | Target market |
| `mrp` | `Numeric(10,2)` | Maximum retail price |
| `currency` | `String(10)` | Currency code |
| `batch_size` | `Integer` | Batch size |
| `qseal_settings` | `Boolean` (default=False) | Distinguishes settings templates from actual units |
| `qseal_cascade` | `Boolean` (default=False) | `True` when all units in dispatch batch are fully cascaded |
| `parent_id` | `FK → qseal_tracks.id` (nullable) | Links individual units to a **shipper-level** parent (dashboard) |
| `parent_app_id` | `FK → qseal_tracks.id` (nullable) | Links units to parent via **app cascade** |
| `extra_data` | `JSONB` | Extensible metadata |
| `created_by` | `UUID` | User who created the record |
| `created_at` | `DateTime(tz=True)` | Creation timestamp |

---

## 4. API Endpoint Design

All endpoints prefixed with `/qseal` (tag: `"QSeal"`).

### 4.1 Parent QSeal Nodes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/qseal/parents` | ✅ | Create a parent QSeal node |
| `GET` | `/qseal/parents` | ✅ | List parent QSeal nodes (paginated, ?qseal_type= filter) |
| `GET` | `/qseal/parents/{node_id}` | ✅ | Get a single parent QSeal node |

### 4.2 Child QSeal Nodes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/qseal/parents/{parent_id}/children` | ✅ | Create child QSeal node under parent |
| `GET` | `/qseal/parents/{parent_id}/children` | ✅ | List children under a parent (paginated) |

### 4.3 Mapping (App-Side Cascade)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/qseal/parents/{parent_id}/map` | ✅ | Map existing unattached children to a parent (bulk) |

### 4.4 Scanning & History

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/qseal/scan` | ❌ (public) | Record a QSeal scan from consumer-facing page |
| `GET` | `/qseal/history` | ✅ | Get QSeal scan history (paginated, ?serial_number= filter) |

### 4.5 Labels

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/qseal/parents/{parent_id}/labels` | ✅ | Download label data for all children of a parent |

---

## 5. Implementation Steps (Ordered)

### Step 1: Create the Model (`core-service/app/models/qseal.py`)

Create `QSealTrack` and `QSealParameters` SQLAlchemy models following the exact pattern of `qr_activation.py`. Key differences:
- Table names: `qseal_tracks`, `qseal_parameters`
- Field prefix: `qseal_` instead of `qr_`
- Column name: `qseal_type` instead of `qr_type`
- Column name: `qseal_code_link` instead of `qr_code_link`
- Column name: `qseal_settings` instead of `qr_settings`
- Column name: `qseal_cascade` instead of `qr_cascade`
- FK targets: `qseal_tracks.id` instead of `qr_activation_tracks.id`

### Step 2: Create the Pydantic Schemas (`core-service/app/schemas/qseal.py`)

Mirror `cascade_qr.py` with renamed classes:
- `QSealParentCreate`, `QSealParentResponse`, `QSealParentListResponse`
- `QSealChildCreate`, `QSealChildListResponse`
- `QSealMapRequest`, `QSealMapResponse`
- `QSealScanRequest`, `QSealScanResponse`
- `QSealHistoryItem`, `QSealHistoryResponse`
- `QSealLabelDownloadResponse`

### Step 3: Create the Repository (`core-service/app/repositories/qseal_repository.py`)

Mirror `cascade_qr_repository.py` with:
- Model references: `QSealTrack` instead of `QRActivationTrack`
- Serial prefix: `"QSL"` instead of `"PAR"`/`"CHD"`
- All same methods: `create_node`, `get_by_id`, `get_by_serial`, `list_roots`, `list_children`, `count_children`, `map_children`, `generate_serial`, `record_scan`, `list_scan_history`

### Step 4: Create the Service (`core-service/app/services/qseal_service.py`)

Mirror `cascade_qr_service.py` with:
- Class name: `QSealService`
- Repository: `QSealRepository`
- Schema imports from `qseal.py`
- Log prefix: `[QSEAL]` instead of `[CASCADE]`
- QR code link pattern: `/qseal/{serial}` instead of `/qr/cascade/{serial}`

### Step 5: Create the Endpoints (`core-service/app/api/v1/endpoints/qseal.py`)

Mirror `cascade_qr.py` with:
- Router variable: `router`
- Service: `QSealService`
- Schema imports from `qseal.py`
- All 9 endpoints with matching paths

### Step 6: Register Routes (`core-service/app/api/v1/router.py`)

Add:
```python
from app.api.v1.endpoints import qseal

# In the router registration section:
api_router.include_router(
    qseal.router,
    prefix="/qseal",
    tags=["QSeal"],
)
```

### Step 7: Run Database Migrations

Generate and run Alembic migration to create `qseal_tracks` and `qseal_parameters` tables:
```bash
cd core-service
alembic revision --autogenerate -m "add qseal tracks and parameters tables"
alembic upgrade head
```

### Step 8: Create Documentation (`QSEAL_PARENT_CHILD_GUIDE.md`)

Create a documentation file mirroring `parent_child_qr_code.md` but adapted for QSeal terminology.

---

## 6. File-by-File Comparison: Cascade QR → QSeal

| Cascade QR File | QSeal File | Notes |
|-----------------|------------|-------|
| `models/qr_activation.py` | `models/qseal.py` | `QRActivationTrack` → `QSealTrack`, `QRActivationParameters` → `QSealParameters` |
| `schemas/cascade_qr.py` | `schemas/qseal.py` | All class names: `ParentQR*` → `QSealParent*`, etc. |
| `repositories/cascade_qr_repository.py` | `repositories/qseal_repository.py` | `CascadeQRRepository` → `QSealRepository` |
| `services/cascade_qr_service.py` | `services/qseal_service.py` | `CascadeQRService` → `QSealService` |
| `endpoints/cascade_qr.py` | `endpoints/qseal.py` | URL prefix: `/cascade-qr` → `/qseal` |
| (in `router.py`) | (in `router.py`) | Add `qseal` import and `include_router` call |

---

## 7. Key Functional Features (from parent_child_qr_code.md)

| Feature | Cascade QR | QSeal Equivalent |
|---------|-----------|-----------------|
| Three-level hierarchy | Container → Pallet → Shipper | Container → Pallet → Shipper |
| Capacity enforcement | `capacity` field on parent | Same |
| One-time cascade | `app_cascade_map` flag | Same |
| Type-safe linking | `qr_type` validation | `qseal_type` validation |
| Label download | `GET /cascade-qr/parents/{id}/labels` | `GET /qseal/parents/{id}/labels` |
| Cascade history | `GET /cascade-qr/history` | `GET /qseal/history` |
| Batch cascade tracking | `qr_cascade` flag on parameters | `qseal_cascade` flag on parameters |
| Duplicate prevention | `parent_id IS NULL` filter + capacity check | Same |
| Dashboard linking | Via `parent_id` FK | Same |
| App cascade linking | Via `parent_app_id` FK | Same |

---

## 8. Estimated Effort

| Step | Effort | Complexity |
|------|--------|-----------|
| Model (`qseal.py`) | ~30 min | Low — direct mirror of existing |
| Schemas (`qseal.py`) | ~20 min | Low — rename classes |
| Repository (`qseal_repository.py`) | ~20 min | Low — rename references |
| Service (`qseal_service.py`) | ~25 min | Low — rename references |
| Endpoints (`qseal.py`) | ~25 min | Low — rename references |
| Router registration | ~5 min | Trivial |
| Database migration | ~10 min | Medium — Alembic autogenerate |
| Documentation | ~15 min | Low |
| **Total** | **~2.5 hours** | |

---

## 9. Appendix: Feature Flag

The existing feature flag constant in `core-service/app/core/constants.py`:

```python
# QSeal module
QSEAL_MODULE_ENABLED = "qseal_module_enabled"
```

This can be used to gate the QSeal endpoints behind a feature flag. Add a dependency check in the endpoints:

```python
from app.core.constants import QSEAL_MODULE_ENABLED
from app.dependencies import require_feature_flag

# Then use as a dependency:
# current_user: dict = Depends(require_feature_flag(QSEAL_MODULE_ENABLED))
```

---

## 10. Next Steps

1. ✅ Review and approve this plan
2. Create `core-service/app/models/qseal.py`
3. Create `core-service/app/schemas/qseal.py`
4. Create `core-service/app/repositories/qseal_repository.py`
5. Create `core-service/app/services/qseal_service.py`
6. Create `core-service/app/api/v1/endpoints/qseal.py`
7. Register routes in `core-service/app/api/v1/router.py`
8. Run Alembic migration
9. Create `QSEAL_PARENT_CHILD_GUIDE.md`
10. Test with Postman/curl
