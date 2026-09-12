# Direct Put-Away & RECEIVING-STAGE Removal

> Change summary: the parallel **direct put-away** flow and the
> **`RECEIVING-STAGE`** staging bin have been removed. The warehouse now
> follows a single, linear **receiving → put-away** flow where stock enters
> the final bin only when a put-away item is completed.
>
> Related (superseded) docs: `WMS_RECEIVING_PUTAWAY_ARCHITECTURE.md`,
> `DUAL_AXIS_RECEIVING_PUTAWAY_DESIGN.md`, `DIRECT_PUTAWAY_STANDALONE_DESIGN.md`,
> `RECEIVING_STAGE_SYSTEM_BIN_DEACTIVATION_FIX.md`.

---

## 1. Why

The previous design booked approved receipt stock into a non-pickable
`RECEIVING-STAGE` bin at receipt approval, then *transferred* it to the final
bin at put-away completion. In practice this caused:

- stock being left stuck in `RECEIVING-STAGE` after put-away,
- silent double-counting (a failed staged-stock lookup fell back to
  `add_stock` on the target bin while the staged stock remained),
- a parallel direct put-away flow that bypassed the receiving-slip approval
  cycle and needed reconciliation afterwards.

The requirement is now **receiving then put-away**, with no staging bin.

---

## 2. New flow

```text
Receiving scan
  → create receiving slip
  → approve slip            (NO stock entry — no RECEIVING-STAGE)
  → generate put-away list  (auto assigns bins, or manual leaves bin empty)
  → complete put-away item  (add_stock into the final bin — stock entered ONCE)
  → slip → putaway_complete
```

- Stock is entered **only at put-away completion** (`PutAwayService.complete_item`
  → `BinStockService.add_stock`).
- The put-away list item records the destination (`bin_location_id`), and the
  completion response returns `bin_location_code`.

---

## 3. What was removed

### Backend (`horizon-sync-erp-be/core-service`)

- `PutAwayService`:
  - `_move_from_receiving_stage_or_add()` (RECEIVING-STAGE transfer logic).
  - `create_direct_list()`, `add_direct_completed_item()`,
    `reconcile_tracking_with_recent_slip()`,
    `reconcile_slip_with_completed_putaway()`.
- `InboundService`:
  - `_stage_approved_receipt_lines()` (staging at approval).
  - the two direct put-away reconciliation blocks in the approval /
    slip-generation paths.
- `ScannedItemTrackingService`:
  - `stage_tracking()`.
  - the `RECEIVING-STAGE` transfer branch inside `complete_putaway()`.
- `InboundExceptionService.release_to_receiving`:
  - no longer moves stock into `RECEIVING-STAGE`; it removes segregated stock
    (`_remove_segregated_stock`) and queues the item for normal put-away.
- Endpoints in `app/api/v1/endpoints/put_away.py`:
  - `GET /available`
  - `POST /direct`
  - `POST /lists`
  - `POST /complete`
  - `POST /scan`
  - `GET /lookup/{qr}`
- Comments/docstrings referencing `RECEIVING-STAGE` in `bin_stock_service.py`,
  `floor_plan_generator_service.py`, `scanned_item_tracking.py`.

### Mobile (`BWmobile`)

- Removed the **"Start Direct Put-Away"** entry point in `PutawayScreen.tsx`.
- Removed the `DirectPutaway` route from `navigation/AppNavigator.tsx`.
- Updated `types/inbound.ts`:
  `InboundException.destination` now allows `'released'` instead of
  `'RECEIVING-STAGE'`.

---

## 4. Files changed

| Layer | File |
|---|---|
| Put-away service | `core-service/app/services/put_away_service.py` |
| Inbound service | `core-service/app/services/inbound_service.py` |
| Tracking service | `core-service/app/services/scanned_item_tracking_service.py` |
| Exception service | `core-service/app/services/inbound_exception_service.py` |
| Bin stock service | `core-service/app/services/bin_stock_service.py` |
| Floor plan | `core-service/app/services/floor_plan_generator_service.py` |
| Model comment | `core-service/app/models/scanned_item_tracking.py` |
| Endpoints | `core-service/app/api/v1/endpoints/put_away.py` |
| Mobile put-away screen | `BWmobile/src/screens/PutawayScreen.tsx` |
| Mobile navigator | `BWmobile/src/navigation/AppNavigator.tsx` |
| Mobile types | `BWmobile/src/types/inbound.ts` |

---

## 5. Data cleanup (existing warehouses)

Removing the code stops **new** warehouses from creating `RECEIVING-STAGE`,
but existing rows remain in the database and will still appear in the
location tree until migrated.

- `alembic/versions/078_add_inbound_exception_hold_quarantine.py` no longer
  seeds `RECEIVING-STAGE` (only `HOLD` / `QUARANTINE` are seeded now).
- `alembic/versions/114_remove_receiving_stage_bins.py` deactivates any
  existing `RECEIVING-STAGE` rows (`is_active = false`), which removes them
  from the Location Tree. Run `alembic upgrade head` (or apply migration
  `114` directly) to apply it.

After migrating, verify there is no leftover `BinStockLevel` stock still
sitting in deactivated `RECEIVING-STAGE` bins and reconcile it manually if
any exists (move it to a real bin or zero it out).

---

## 6. Leftover dead mobile files (optional manual deletion)

These are no longer reachable from navigation and can be deleted:

- `BWmobile/src/screens/DirectPutawayScreen.tsx`
- `BWmobile/src/hooks/useDirectPutaway.ts`
- `BWmobile/src/components/putaway/ScanningView.tsx`
- `BWmobile/src/components/putaway/AssignTable.tsx`
- Direct put-away functions in `BWmobile/src/api/putawayService.ts`
  (`completePutawayByQr`, `createDirectPutAwayList`, `scanItemForDirectPutaway`)

---

## 7. Verification

- All modified backend files pass `python -m py_compile`.
- Modified mobile files pass TypeScript checks (no errors).
- No remaining callers of the removed service methods
  (`create_direct_list`, `_stage_approved_receipt_lines`,
  `_move_from_receiving_stage_or_add`, `stage_tracking`,
  `reconcile_slip_with_completed_putaway`, etc.).
