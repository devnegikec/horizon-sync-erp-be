# Frontend Changes Note — Outbound / Stock (Inbound Automation)

Backend changes that require frontend updates. All endpoints are under `/api/v1`.

---

## 1. Pick-list "Accept" — response is now minimal

`POST /outbound/{pick_list_id}/accept`

The response no longer includes `items`, `progress`, `assigned_to`, `worker_name`,
timestamps, priority, etc.

**New response shape:**

```json
{
  "id": "3f858ded-23b4-44cb-a958-154efa080a58",
  "pick_list_no": "PL-2026-00019",
  "status": "in_progress",
  "accepted_at": "2026-09-11T06:22:35.923683+00:00",
  "accepted_by": "4397ad83-1c2c-423a-bd52-4e2550929166"
}
```

> Update the accept action's TypeScript type/usage — do not rely on the old full
> payload after accepting.

---

## 2. "Create Pick List" (generate pick lists) — partial order

`POST /outbound/orders/{order_id}/generate-pick-lists`

- Request body gains an optional `exclude_out_of_stock` (boolean, default `true`).
  Send `true` for the partial-order behaviour.
- The backend reserves stock under a row lock and **skips out-of-stock lines**.
- If **every** line is out of stock, the API returns a validation error — show a
  message instead of a success.

**Request:**

```json
{
  "worker_ids": ["<uuid>"],
  "mode": "auto",
  "exclude_out_of_stock": true
}
```

---

## 3. "Confirm" order — blocks when nothing is in stock

`POST /outbound/orders/{order_id}/confirm`

- If all lines are `out_of_stock`, the API returns a validation error
  (`"Cannot confirm order: none of its line items are in stock"`).
- Hide/disable the **Confirm** button when `out_of_stock_count > 0` in the list,
  or when every line's `stock_status == "out_of_stock"` in the detail view.

---

## 4. Orders detail/list now return live availability (no type change)

- `GET /outbound/orders/{id}` — per-line `stock_status` and `available_qty` are
  refreshed on every read (no stale snapshot).
- `GET /outbound/orders` — `in_stock_count` / `out_of_stock_count` are live.

> No schema change. The UI can now trust these values to drive button visibility
> (Confirm / Create Pick List).

---

**Request:**

```json
{
  "features": ["receive_asn"],
  "receive_asn": {
    "steps": ["qr_blocks", "asn", "receiving_slip", "put_away"],
    "target_warehouse_id": "<uuid>",
    "put_away_worker_ids": ["<user-id-1>", "<user-id-2>"]
  }
}
```

**New put-away response fields:**

```json
{
  "put_away_count": 2,
  "put_away_list_nos": ["PA-...-0001", "PA-...-0002"],
  "put_away_list_no": "PA-...-0001",
  "put_away_status": "pending"
}
```

**Populate the multi-select dropdown from:**

```
GET /warehouse-users?warehouse_id={target_warehouse_id}
```

Send each record's **`user_id`** in `put_away_worker_ids`.

---

## Summary table

| Action | What changed | Frontend action |
|---|---|---|
| Accept pick list | Minimal response | Update response type/usage |
| Generate pick lists | Partial order, `exclude_out_of_stock` | Send flag; handle all-out-of-stock error |
| Confirm order | Rejects when all out of stock | Hide/disable Confirm when nothing in stock |
| Orders detail/list | Live `stock_status`/counts | Trust the live values (no type change) |
