# Dispatch Slip Serial Match — Frontend Integration

**Status:** Backend implemented — frontend changes pending
**Date:** 2026-09-23
**Companion docs:** `WMS_DISPATCH_SERIAL_MATCH_DESIGN.md` (design),
`WMS_DISPATCH_RECEIPT_SERIAL_MATCH.md` (gap analysis)

This is the frontend contract for the dispatch→inbound serial/QR match feature.
The backend endpoints below are implemented; the frontend needs to consume them.

---

## 1. Receiving screen — "quantity-only verification" banner

The ASN now carries `serialization_mode` (`"serialized" | "quantity_only" | null`),
set at dispatch. It is returned on:

- `GET /api/v1/asn-orders/{id}` → `serialization_mode`
- session payload (`start_session` / `link_asn_to_session` responses) → `serialization_mode`

**Change:** when the value is `quantity_only`, show a banner:

> ⚠️ This shipment is verified by quantity only — unit serials were not captured.

Do **not** claim per-unit verification was performed.

---

## 2. Serial-match screen

`GET /api/v1/asn-orders/{id}/transfer-verification` (requires `asn_order.read`)

Response shape:

```jsonc
{
  "asn_order_id": "...",
  "asn_order_no": "...",
  "asn_type": "internal_transfer",
  "serialization_mode": "serialized",
  "warehouse_from": "...",
  "warehouse_to": "...",
  "delivery_date": "2026-09-26",
  "dispatched_at": "2026-09-22T08:10:00+00:00",
  "summary": {
    "total_serials": 47,
    "received": 47,
    "in_transit": 0,
    "missing": 0,
    "unexpected": 0
  },
  "serials": [
    {
      "serial_no": "S8DN0001234",
      "item_id": "...",
      "item_code": "SKU-001",
      "sku": "SKU-001",
      "item_name": "Widget",
      "carton_id": "...",
      "carton": "MP-2026-1",
      "carton_serial": "QSL...",
      "status": "received",        // received | in_transit | missing | unexpected
      "received_at": "2026-09-23T10:00:00+00:00",
      "received_by": "...",
      "reason_code": null,          // set only for "unexpected"
      "exception_type": null        // set only for "unexpected"
    }
  ],
  "cartons": [
    {
      "carton": "MP-2026-1",
      "carton_serial": "QSL...",
      "expected": 24,
      "received": 23,
      "in_transit": 0,
      "missing": 1,
      "missing_serials": ["S8DN0009999"]
    }
  ]
}
```

**Change:** render a header line *"47 dispatched · 47 received · 0 missing"* with
drill-downs per carton and per serial. Status → badge mapping:
`received` (green) · `in_transit` (grey) · `missing` (red) · `unexpected` (amber).

---

## 3. Master-carton receive — replace the client-side loop

`POST /api/v1/inbound/sessions/{id}/scan-carton` (requires `receiving_slip.create`)

Request:

```jsonc
{
  "qr_data": "<raw parent QR payload>",
  "device_type": "mobile",
  "os": "android"
}
```

Response:

```jsonc
{
  "session_id": "...",
  "carton": "MP-2026-1",
  "carton_serial": "QSL...",
  "expected": 24,
  "received": 23,
  "duplicate": 0,
  "unexpected": 1,
  "exception_ids": ["..."],
  "serials": [
    { "serial_no": "S8DN0001234", "status": "received", "sku": "SKU-001", "item_name": "Widget", "reason_code": null },
    { "serial_no": "S8DN0009999", "status": "unexpected", "sku": null, "item_name": null, "reason_code": "UNEXPECTED_SERIAL" }
  ]
}
```

**Change (T2.5):** replace the current flow
(scan parent → `GET /qseal/parents/{id}/linked-units` → N × `POST /scan`) with this
single call. Show the carton summary before the worker ends the session:

> Carton `MP-2026-1`: 24 expected · 23 received · 1 unexpected (`S8DN0009999`)

Unexpected units are already recorded as inbound exceptions — no extra client work.

---

## 4. Exception queue — new reason codes

The following reason codes now appear in `GET /inbound/exceptions` and
`GET /inbound/exception-reasons`:

| Code | Meaning | Physical unit? | Disposition |
|---|---|---|---|
| `UNEXPECTED_SERIAL` | Serial scanned but not on the ASN | yes (held) | move_to_hold / return / dispose |
| `WRONG_ITEM` | Serial on the ASN under a different item | yes (held) | move_to_hold / return / dispose |
| `MISSING_SERIAL` | Dispatched but never received | **no** | short-close with approval |

**Change:** render these codes; treat `MISSING_SERIAL` as a shortage (short-close
flow), not a physical hold.

---

## 5. Receiving slip detail — serials on the document

Slip item payloads now include:

```jsonc
{ "serial_nos": ["S8DN0001234"], "received_serial_count": 1 }
```

**Change:** show the unit serials directly on the slip detail/print view
(no client-side join of `scan_session_items` + `scanned_item_tracking` +
`asn_order_serial_lines`).

---

## 6. ASN closure — handle the new block

`PUT /api/v1/asn-orders/{id}/status` with `{"status": "closed"}` now returns
`422` when unreceived transfer serials remain:

> Cannot close ASN `ASN-…`: 3 serial(s) have not been received

**Change:** on this error, surface the message and route the user to short-close
the missing units (manager approval) before closing.

---

## 7. Receiving summary — serial counts (additive)

`receiving-summary` now includes:

```jsonc
{
  "expected_serials": 47,
  "received_serials": 47,
  "missing_serials": 0,
  "unexpected_serials": 0
}
```

**Change (optional):** display these next to the quantity totals.

---

## No frontend impact

- `qr_scan_events` document FKs (T3.5) — backend analytics only.
- Scheduled `MISSING_SERIAL` reconciliation (T3.1) — backend beat task only.
- Single audit event per carton scan (T2.3) — backend only.
