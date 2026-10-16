# ASN Short Delivery — Frontend Integration

**Feature:** a warehouse manager accepts a short delivery by formally closing a
partially delivered ASN.
**Service:** `core-service` · branch `feature-inbound-process-complete`
**Related:** `WMS_INTERNAL_STOCK_TRANSFER_DESIGN.md`,
`INBOUND_EXCEPTION_QUEUE_FRONTEND_INTEGRATION.md`

> Every path below is relative to the global `/api/v1` prefix (see
> `app/main.py`). Calling a path without `/api/v1` returns **404**.

---

## 1. When to show the action

Offer **"Close as short delivery"** on an ASN when:

- `status == "partially_delivered"` (or `"delivered"`), **and**
- the caller has the `asn_order.update` permission, **and**
- `short_closed == false`.

Hide it when the status is `draft`, `confirmed`, `closed` or `cancelled` —
those must be **cancelled**, not short-closed, and the API returns
`ASN_NOT_CLOSABLE` / `ASN_ALREADY_CLOSED`.

Before confirming, show the manager **what is being given up**. The data is
already available:

| Call | Gives you |
|---|---|
| `GET /asn-orders/{id}/receiving-summary` | expected vs scanned/accepted/short, per line + totals, and `reconciliation_status` |
| `GET /asn-orders/{id}` | `items[]` with `qty` (expected) and `delivered_qty` (received) |
| `GET /inbound/asn-orders/{id}/short-balances` | the per-SKU residual shorts that will be written off |

---

## 2. Close the ASN

```
POST /api/v1/asn-orders/{asn_order_id}/close
Authorization: Bearer <token>
Content-Type: application/json
```

```jsonc
{
  "reason_code": "SHORT_PHYSICAL",   // required when a short qty is outstanding
  "note": "Carrier short-shipped the last carton"  // optional, max 1000 chars
}
```

Both fields are optional in the schema. **Always send a JSON object** — send
`{}` for a fully delivered ASN rather than omitting the body entirely, so
clients that set `Content-Type: application/json` without a payload don't
misfire.

**Authority** — beyond `asn_order.update`, the caller must be a warehouse
manager for the ASN's destination warehouse: org/system admin, holder of `*.*`
or `warehouse.manage`, or an active `manager` assignment on that warehouse.
Otherwise the API returns **409 `ASN_CLOSE_APPROVAL_REQUIRED`** — surface that
as *"ask a warehouse manager to approve"*, not as a generic error.

The response is the full **`AsnOrderResponse`** with `status: "closed"` plus the
closure fields below.

---

## 3. New response fields

Present on **`AsnOrderResponse`** (detail); `short_closed` is also on
**`AsnOrderListItem`** so the list can badge a short-closed order.

| Field | Type | Meaning |
|---|---|---|
| `short_closed` | `boolean` | `true` when the ASN was closed with an accepted shortfall |
| `short_closed_qty` | `number \| null` | Quantity accepted as a loss (`0` when nothing was short) |
| `close_reason_code` | `string \| null` | Reason code echoed back, e.g. `SHORT_PHYSICAL` |
| `close_note` | `string \| null` | The manager's explanation |
| `closed_by` | `uuid \| null` | Acting user |
| `closed_at` | `datetime \| null` | ISO-8601 UTC |

Read them as *"closed short"* when `short_closed === true`, and as a plain close
when `status === "closed"` and `short_closed === false`.

---

## 4. Reason codes — fetch, don't hardcode

```
GET /api/v1/inbound/exception-reasons?category=short
```

Returns the tenant's active `short`-category codes
(`code`, `name`, `default_destination`, `requires_approval`). The list is
tenant-configurable, so drive the picker from this call rather than a constant.
Requires `inbound_exception.read` — if the manager lacks it, fall back to a
plain note and let the API reject with `SHORTAGE_REASON_REQUIRED`.

---

## 5. Errors

Error envelope is `{ "error": <code>, "message": ..., ... }`.

| HTTP | `error` | Cause | Suggested UI |
|---|---|---|---|
| `400` | `SHORTAGE_REASON_REQUIRED` | A short exists but no `reason_code` was sent | Mark the reason picker required |
| `400` | `SHORTAGE_REASON_INVALID` | Unknown or inactive code | Refetch section 4 and re-pick |
| `409` | `ASN_ALREADY_CLOSED` | Already closed or cancelled | Refresh the ASN; the closure is final |
| `409` | `ASN_NOT_CLOSABLE` | Status is not `partially_delivered`/`delivered` | Hide the action, refresh |
| `409` | `ASN_CLOSE_APPROVAL_REQUIRED` | Not a manager for that warehouse | "Ask a warehouse manager to approve" |
| `403` | — | Missing `asn_order.update` | Hide the action |
| `404` | — | ASN not found | Refresh |

`409` responses also carry `current_state` / `required_state`, and both 400 and
409 include a `hint` when the backend can suggest a next step.

---

## 6. Gotchas

1. **Closing also writes off the shortages.** Every open shortage balance on the
   ASN is closed as `written_off` with the same reason and appends events to
   `inbound_short_balance_events`. **Refetch any "open shortages" widget after a
   successful close**, or it will keep showing shortages for a closed order.
2. **Not idempotent.** A second call returns `409 ASN_ALREADY_CLOSED` rather
   than succeeding silently — disable the button while in flight.
3. **A reason is only required when something is short.** A fully delivered ASN
   closes with `{}` and yields `short_closed: false`.
4. **`delivered` ASNs can also be closed** through this same endpoint; the
   closure fields are simply empty.
5. **`short_closed` is a flag, not a status.** `status` stays `closed`, so
   existing status filters and counts are unchanged.
