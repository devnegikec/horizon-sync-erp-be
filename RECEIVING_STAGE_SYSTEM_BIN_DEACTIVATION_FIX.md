# Receiving Slip Approve → 409 Conflict on Deactivated System Bin

> Status: **Fixed**
> Service: `core-service` (WMS Inbound / Warehouse Locations)
> Date: 2026-09-04

---

## 1. Symptom

Approving a receiving slip fails with a **409 Conflict**:

```
POST /api/v1/inbound/receiving-slips/{slip_id}/approve
```

Response body:

```json
{
  "error": "STATE_CONFLICT",
  "message": "Cannot perform stock operations on deactivated location '_inactive_1d916e95-8026-49ac-8fc4-6f51a18c6803_RECEIVING-STAGE'. Reactivate the location first.",
  "current_state": "deactivated",
  "required_state": ["active"]
}
```

Core service log:

```
State conflict on POST /api/v1/inbound/receiving-slips/.../approve:
  Cannot perform stock operations on deactivated location
  '_inactive_..._RECEIVING-STAGE'. Reactivate the location first.
```

The `_inactive_<uuid>_` prefix in the location path is the key clue.

---

## 2. Root Cause

A **floor-plan apply / regeneration** deactivated every location in the
warehouse, including the **logical system bins** that inbound receiving depends
on: `RECEIVING-STAGE`, `HOLD`, and `QUARANTINE`.

### Why the system bins got deactivated

`FloorPlanGeneratorService.apply()` always calls `_deactivate_existing()`,
which soft-deactivated **all** active `warehouse_locations` rows for the
warehouse (and renamed `full_path` to `_inactive_<id>_<path>` to avoid unique
constraint collisions). System bins were not excluded.

### Why the approve then failed

1. `InboundService._stage_approved_receipt_lines()` → `_get_or_create_system_bin(..., "RECEIVING-STAGE")`.
2. `_get_or_create_system_bin()` queried by **`code` only** (no `is_active`
   filter), so it returned the deactivated `RECEIVING-STAGE` bin (a bin with
   that `code` still existed — it was just inactive).
3. The subsequent stock insert went through `BinStockService._get_active_bin()`,
   which validates `is_active` and raised the 409 `StateError`.

### Summary of the failure chain

```
Floor-plan apply()
  └─ _deactivate_existing()  (deactivated system bins: is_active=false,
                               full_path renamed with _inactive_ prefix)
        ... later ...
Approve receiving slip
  └─ _stage_approved_receipt_lines()
        └─ _get_or_create_system_bin("RECEIVING-STAGE")
              └─ returned the DEACTIVATED bin (no is_active filter)
                    └─ _get_active_bin() → 409 STATE_CONFLICT
```

---

## 3. Affected Files / Code

| File | Change |
|---|---|
| `core-service/app/services/floor_plan_generator_service.py` | `_deactivate_existing()` now only deactivates `is_pickable = true` locations, preserving system bins. |
| `core-service/app/services/scanned_item_tracking_service.py` | `_get_or_create_system_bin()` now prefers an **active** bin and reactivates/restores a deactivated copy (self-healing). |

---

## 4. Fix Details

### 4.1 Prevent future deactivation of system bins

`_deactivate_existing()` now adds `WarehouseLocation.is_pickable.is_(True)` to
both the count query and the update query. System bins (`RECEIVING-STAGE`,
`HOLD`, `QUARANTINE`) are created with `is_pickable=False`, so they are left
untouched by floor-plan regeneration.

### 4.2 Make system-bin lookup self-healing

`_get_or_create_system_bin()`:

1. First looks for an **active** bin by `code`.
2. If none is active but a deactivated copy exists, it **reactivates** it
   (`is_active=True`, `is_available=True`) and restores `full_path`/`name`
   (stripping the `_inactive_` prefix).
3. Only creates a new bin if no row with that `code` exists at all.

This means even pre-existing deactivated system bins recover automatically the
next time they are referenced.

---

## 5. Immediate Data Repair (already applied)

For any environment already affected, reactivate the deactivated system bins:

```sql
UPDATE warehouse_locations
SET
  is_active    = true,
  is_available = true,
  full_path    = code,
  name         = initcap(replace(code, '-', ' '))
WHERE is_pickable = false
  AND is_active   = false
  AND code IN ('RECEIVING-STAGE', 'HOLD', 'QUARANTINE');
```

Then restart the core service to load the code changes:

```bash
docker restart horizon_core
```

---

## 6. Verification

After the fix, the affected warehouse's system bins are active again with
restored paths:

| Code | full_path | is_active |
|---|---|---|
| RECEIVING-STAGE | RECEIVING-STAGE | true |
| HOLD | HOLD | true |
| QUARANTINE | QUARANTINE | true |

Retrying the approve (`POST /api/v1/inbound/receiving-slips/{slip_id}/approve`)
returns 200 instead of 409.

---

## 7. Prevention / Takeaways

- **System bins are logical, not physical.** They must never be swept by a
  floor-plan apply. Filtering on `is_pickable = false` keeps them out of layout
  regeneration.
- **"Get or create" helpers must respect `is_active`.** A lookup that ignores
  `is_active` silently hands back soft-deleted rows, which surface later as
  confusing 409 conflicts on unrelated operations.
- The `_inactive_<uuid>_<path>` naming convention is a marker for
  "deactivated by floor-plan regeneration" — searching for it quickly identifies
  this class of issue.
