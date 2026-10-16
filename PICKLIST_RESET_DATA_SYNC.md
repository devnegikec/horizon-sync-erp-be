# Reset PickList (Settings → Data Sync)

> Destructive test/retest helper for the outbound pick-list flow.

Wipes every artifact generated from an outbound order's pick list so the order
can be re-picked from scratch — without re-running confirm → generate → pick →
dispatch by hand.

## Where it lives

- **UI**: `Settings → Data Sync → Reset PickList` (same screen as *Inbound Automation*).
- **API**: reuses the existing data-sync endpoint.

```http
GET  /api/v1/data-sync/features      # now includes {"key": "reset_picklist", "label": "Reset PickList", ...}
POST /api/v1/data-sync/sync
```

## API contract

```jsonc
POST /api/v1/data-sync/sync
Authorization: Bearer <token>

{
  "features": ["reset_picklist"],
  "reset_picklist": {
    "order_id": "<uuid>",       // reset every pick list generated from this order
    "pick_list_id": null        // OR reset a single pick list
  }
}
```

Exactly one of `order_id` / `pick_list_id` is required.

Response:

```jsonc
{
  "success": true,
  "message": "Seeded 1 data category",
  "summary": {
    "reset_picklist": {
      "reset": 2,             // number of pick lists wiped
      "orders_reset": 1,
      "details": [
        { "pick_list_no": "PL-2026-00052", "status": "delivered" }
      ]
    }
  }
}
```

## What it cleans per pick list

| Area | Action |
|---|---|
| Pick list + items | Deleted |
| Bin stock | Picked units restored to `available` (per serial for QR items, per batch otherwise) |
| Warehouse stock | Reservation released (not-yet-dispatched) or dispatch `on_hand` decrement reversed |
| Bin reservations | Deleted |
| Transfer ASN | Serial lines + material-transfer stock entry + `SerialNoHistory` removed; `SerialNo.status` → `in_stock`; `serialization_mode`/`linked_stock_entry_id` cleared |
| Child rows | Scan events, pick movements, exceptions + audit, idempotency keys, dispatch records, gate sessions, packing-slip items, delivery notes, ERP sync messages |
| Source order | Status reset to `confirmed` |

## Permissions

Gated behind `organization.update` (same as the rest of the Data Sync screen).

## Files

- `core-service/app/services/picklist_reset_service.py` (new)
- `core-service/app/services/organization_onboarding_service.py` (`reset_picklist` feature + dispatch)
- `core-service/app/api/v1/endpoints/data_sync.py` (`ResetPickListOptions` request model)
- `horizon-sync/apps/platform/.../data-sync/services/dataSyncService.ts`
- `horizon-sync/apps/platform/.../data-sync/components/DataSyncSettings.tsx`

## Notes / limits

- Destructive. Re-running with an `order_id`/`order_no` is a safe no-op once the
  order is back to `confirmed` (no pick lists remain and the order is no longer
  `pending_picking`/`completed`). Re-running with a `pick_list_id`/
  `pick_list_no` that no longer exists returns a not-found error — use the
  order identifier to re-target an already-reset order.
- If the transfer was **already received** at the destination warehouse, the
  destination-side stock movement is not reversed — only the source-side
  dispatch/ASN artifacts are cleaned. Re-check destination stock levels for
  already-received transfers before retesting.
