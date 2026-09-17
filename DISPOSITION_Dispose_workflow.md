
## The endpoint

`POST /api/v1/inbound/exceptions/{exception_id}/disposition`

- **Permission**: `inbound_exception.dispose` (plus the caller must be a warehouse manager, org admin, or have `warehouse.manage`).
- **Body** (`InboundExceptionDispositionRequest`):

```json
{
  "action": "return_to_sender",
  "note": "optional free text",
  "item_id": "optional UUID — only needed when releasing an unknown SKU"
}
```

Valid `action` values (from `FINAL_DISPOSITIONS`):
`release_to_receiving`, `move_to_hold`, `move_to_quarantine`, `return_to_sender`, `dispose`.

## What happens to the item per action

| Action | Stock effect | Exception status | Receipt line |
|---|---|---|---|
| `release_to_receiving` | Moves held/qty stock into `RECEIVING-STAGE` (becomes normal receiving inventory) | `released` | `flag=ok`, `condition_code=GOOD` |
| `move_to_hold` | Moves stock into the `HOLD` bin | `approved` | `flag=hold`, `condition_code=HOLD` |
| `move_to_quarantine` | Moves stock into the `QUARANTINE` bin | `approved` | `flag=quarantine`, `condition_code=QUARANTINE` |
| `return_to_sender` | **Removes** the held/quarantined stock from the bin | `closed` | `flag=rejected`, `condition_code=REJECTED` |
| `dispose` | **Removes** the held/quarantined stock from the bin | `closed` | `flag=rejected`, `condition_code=REJECTED` |

So a held item that never gets a positive disposition (`release`/`move_*`) stays **physically segregated** in the HOLD/QUARANTINE bin and remains non-pickable.

## How to "return to sender"

Send `action: "return_to_sender"`. What actually happens:

1. The HOLD/QUARANTINE stock is reversed (removed from the system bin).
2. The exception is closed (`status=closed`, `destination=null`).
3. The receipt line is marked `rejected` / `REJECTED`.
4. The decision is recorded as `disposition="return_to_sender"` with your note and `disposed_at`/`disposed_by`, plus an audit event.

⚠️ Note: `return_to_sender` and `dispose` currently behave **identically** — the only difference is the recorded `disposition` label and audit event. There is **no actual outbound return shipment / supplier-return document generated**. If you need real return-shipping records, that would be new functionality.

## Can I dispose multiple items at once?

**No.** The API is single-item only (one `{exception_id}` in the path). There is no bulk endpoint. To dispose several items you must call this endpoint once per exception (loop over the selected rows on the frontend).

## Does the API support pagination?

- The **disposition** endpoint is single-record — pagination doesn't apply.
- The **list** endpoint `GET /api/v1/inbound/exceptions` does **not** paginate. It returns the full queue as a plain array, filterable by `warehouse_id`, `destination`, `status` (query params). If the queue can grow large, pagination would need to be added server-side.

## Can I build a table on the frontend?

Yes. Flow:

1. **Fetch the queue** with `GET /api/v1/inbound/exceptions` (optionally `?status=pending_approval&destination=HOLD`).
2. **Render a table** using these fields from each row:

   `exception_type`, `reason_code`, `sku`, `item_name`, `batch_number`, `quantity`, `status`, `condition_code`, `destination`, `disposition`, `created_at`, `disposed_at`.

3. **Per-row action**: a dropdown/button with the five disposition actions, calling
   `POST /api/v1/inbound/exceptions/{id}/disposition` with `{ action, note }`.
   After a successful response, refresh the row/list.

For multi-select, you'd select several rows and issue one POST per selected row (since bulk isn't supported).

Want me to add **bulk disposition** or **pagination** to the exceptions API? That would be the natural next step if the queue grows or you want multi-select support.
