# Put-Away Multi-Worker API Change

> Frontend integration guide for splitting a receiving slip's put-away work
> across multiple workers.

## Endpoint

```
POST /api/v1/put-away/generate-from-slip/{slip_id}
```

Permission required: `warehouse.create`

---

## What changed

The endpoint now accepts an optional **`worker_ids`** array. When provided, the
API generates **one put-away list per worker** and distributes the slip's items
across them (round-robin). The existing single-worker behavior is unchanged.

| Mode | Request field | Response shape |
|------|---------------|----------------|
| Single worker (unchanged) | `worker_id` or nothing | `PutAwayListResponse` (single object) |
| Multiple workers (NEW) | `worker_ids` | `PutAwayListBatchResponse` (object with `put_away_lists` array) |

---

## Request body

### Single worker (unchanged, backward compatible)

```json
{
  "worker_id": "45939feb-d15e-49a2-8dbd-5c2b5428d1f3",
  "mode": "auto"
}
```

### Multiple workers (NEW)

```json
{
  "worker_ids": [
    "45939feb-d15e-49a2-8dbd-5c2b5428d1f3",
    "869674d6-886a-4736-956b-48a77dff78e1"
  ],
  "mode": "auto"
}
```

- `worker_id`: optional single worker UUID (existing field).
- `worker_ids`: optional list of worker UUIDs (NEW).
- If both are sent, **`worker_ids` wins**.
- `mode`: optional — `"auto"` (server assigns bins) or `"manual"` (worker
  assigns bins). Omit to use the organization's `putaway_mode` setting.

---

## Response

### Single worker → `PutAwayListResponse` (unchanged)

Same object as before:

```json
{
  "id": "...",
  "put_away_list_no": "PA-2026-00086",
  "status": "pending",
  "assigned_to": "45939feb-d15e-49a2-8dbd-5c2b5428d1f3",
  "receiving_slip_id": "...",
  "receiving_slip_no": "RS-2026-00098",
  "total_items": 24,
  "completed_items": 0,
  "pending_items": 24,
  "warnings": null,
  "items": [ "... PutAwayListItemResponse ..." ]
}
```

### Multiple workers → `PutAwayListBatchResponse` (NEW)

The top level becomes a wrapper object — each entry in `put_away_lists` has the
**exact same shape** as the old single `PutAwayListResponse`:

```json
{
  "put_away_lists": [
    {
      "id": "7d5faf77-aff8-49fd-a71c-38338a4aa9ba",
      "organization_id": "147f3b9d-77fd-432f-8d91-e5559af9d897",
      "warehouse_id": "f0099ec7-0364-416c-9806-22fe38a4c56c",
      "put_away_list_no": "PA-2026-00086",
      "status": "pending",
      "reference_type": "receiving_slip",
      "reference_id": "87860e0b-...",
      "receiving_slip_id": "87860e0b-...",
      "receiving_slip_no": "RS-2026-00098",
      "remarks": null,
      "warnings": null,
      "assigned_to": "45939feb-d15e-49a2-8dbd-5c2b5428d1f3",
      "worker_name": null,
      "total_items": 12,
      "completed_items": 0,
      "pending_items": 12,
      "completed_at": null,
      "created_at": "2026-09-04T05:38:13.813200+00:00",
      "updated_at": "2026-09-04T05:38:13.891675+00:00",
      "items": [
        {
          "id": "a4dcf107-...",
          "item_id": "28c7a653-...",
          "sku": "PTK-DUK-M010",
          "item_name": "Prestige Electric Induction Cooktop PIC 20.0",
          "batch_number": "TTK-X9ARN3",
          "serial_number": "TTK-X9ARN3",
          "manufacturing_date": "2026-09-03",
          "expiry_date": "2026-09-03",
          "quantity": 1.0,
          "bin_location_id": "a78b55f6-...",
          "bin_location_code": "Z-02-A-01-B01-L02-BN03",
          "suggested_bin_code": "Z-02-A-01-B01-L02-BN03",
          "sort_order": 1,
          "status": "pending",
          "notes": null,
          "completed_at": null,
          "created_at": "2026-09-04T05:38:13.835572+00:00"
        }
      ]
    },
    {
      "id": "...",
      "put_away_list_no": "PA-2026-00087",
      "assigned_to": "869674d6-886a-4736-956b-48a77dff78e1",
      "total_items": 12,
      "items": [ "... PutAwayListItemResponse ..." ]
    }
  ]
}
```

---

## Distribution behavior

- Items are distributed **round-robin**: worker 1 gets item 1, 4, 7, …;
  worker 2 gets item 2, 5, 8, …; and so on.
- Each worker gets a separate `PutAwayList` with `assigned_to` = that worker.
- A worker task (`task_type = "put_away"`) is created for **each** worker.
- If there are **more workers than items**, workers that end up with no items
  are skipped (no empty list is created for them).
- If every slip line is skipped (hold/quarantine/excess/damaged/rejected or
  unresolved SKU), the API returns a **single** list (with `warnings`) — the
  same fallback as the old single-worker path.

---

## Errors (unchanged)

| Case | Behavior |
|------|----------|
| Slip not `pending_putaway` | 400 — "Receiving slip must be in pending_putaway status…" |
| A put-away list already exists for the slip | 409/422 — "Put-away list '…' already exists for receiving slip '…'" |
| Missing permission | 403 — "Permission denied. Required one of: warehouse.create" |

Note: one put-away generation is allowed per slip. To split across workers you
must pass `worker_ids` on the **first** generate call for that slip.

---

## Frontend checklist

1. **Multi-worker toggle**: when the user selects >1 worker, send
   `worker_ids: [...]` instead of `worker_id`.
2. **Response handling**: if you sent `worker_ids`, the response is
   `{ "put_away_lists": [...] }` — iterate the array. Each element is the same
   type as the old single response, so reuse your existing list/item types.
3. **Single-worker path**: keep using `worker_id` (or nothing) and the old
   single-object response.
