# Returns — Web App Integration Guide

> **Version**: 1.1 (implemented — local/dev verified 2026-09-20)
> **Date**: 2026-09-20
> **Audience**: Web app (back-office / supervisor console) developers
> **Base URL**: `http://<host>/api/v1` > **Status**: ✅ **IMPLEMENTED** — all 12 web endpoints below are live
> (migration `124_returns_module`, permissions migration identity `022`). Verified end-to-end
> against both warehouses. See §14 for the four implementation notes that differ from v1.0.
> **Companion doc**: `RETURNS_HANDHELD_INTEGRATION.md` (dock scanning + condition capture).
> **Related**: `SHORT_RECEIPT_FRONTEND_INTEGRATION.md` (inbound receipt notes),
> `INBOUND_EXCEPTION_AND_RETURNS_GAP_ANALYSIS.md` (backlog + open business questions),
> `RETURNS_API_AUDIT_2026-09-20.md` (pre-build gap audit).

---

## 1. Division of labour

| Step                                                           | Owner        | Where                       |
| -------------------------------------------------------------- | ------------ | --------------------------- |
| Register a return against Invoice / Dealer / Warehouse         | Web app      | §5                          |
| Look up + validate the reference (invoice / party / warehouse) | Web app      | §4                          |
| Print / hand the registration to the dock                      | Web app      | §5.3                        |
| Receive + classify returned units                              | **Handheld** | handheld doc §5, §6         |
| Review the Draft Return Receipt Note (expected vs received)    | Web app      | §6                          |
| Approve / reject the note, per-line disposition                | Web app      | §6.3 – §6.5                 |
| Generate put-away for good lines / segregate the rest          | Web app      | §6.6                        |
| Produce the Return Slip document                               | Web app      | §6.7                        |
| Confirm put-away of good stock in the bin                      | **Handheld** | existing put-away endpoints |

The web app **never** scans returned units and the handheld **never** approves a note — mirrors the
existing receiving split (`SHORT_RECEIPT_FRONTEND_INTEGRATION.md` §1).

---

## 2. End-to-end flow

```
Web app                                Handheld                       Web app (supervisor)
────────                                ────────                       ───────────────────
GET  /returns/references?invoice_no=…
POST /returns/registrations      ──►  (registration becomes receivable)
                                       POST /registrations/{id}/sessions
                                       POST /sessions/{id}/scans       (validate + hard stops)
                                       POST /sessions/{id}/classify    (good/damaged/hold/quarantine)
                                       POST /sessions/{id}/end
                                                  │
                                                  ▼  draft note
GET  /returns/receipt-notes  ◄────────────────────┘
GET  /returns/receipt-notes/{id}        (expected vs received, conditions, serials)
POST /returns/receipt-notes/{id}/approve
POST /returns/receipt-notes/{id}/disposition     (per line)
POST /returns/receipt-notes/{id}/generate-put-away
GET  /returns/receipt-notes/{id}/slip            (Return Slip document)
```

---

## 3. Status model

### 3.1 Return registration

```
draft ──► ready ──► receiving ──► received ──► closed
  │         │            │
  └─────────┴────────────┴──► cancelled        (allowed until the first unit is scanned)
```

| Status      | Meaning                                       | Set by                            |
| ----------- | --------------------------------------------- | --------------------------------- |
| `draft`     | Created, lines not confirmed yet              | `POST /registrations`             |
| `ready`     | Lines confirmed, the dock may start receiving | `POST /registrations/{id}/…`      |
| `receiving` | A handheld session is open against it         | handheld session start            |
| `received`  | Session ended, units classified               | handheld session end              |
| `closed`    | Return Slip issued / put-away handled         | after `generate-put-away`         |
| `cancelled` | Cancelled before any unit was scanned         | `POST /registrations/{id}/cancel` |

> `cancelled` is terminal. The UI must hide **Start receiving** once `receiving`/`received`/`closed`.

### 3.2 Return Receipt Note

```
draft ──► pending_approval ──► approved
                       └────► rejected
```

### 3.3 Line condition (captured on the handheld)

`pending` → `good` | `damaged` | `hold` | `quarantine`.

### 3.4 Line disposition (chosen on the web app at approval)

| Disposition          | Applies to              | Stock effect                                                 |
| -------------------- | ----------------------- | ------------------------------------------------------------ |
| `release_to_stock`   | `good`                  | enters put-away; becomes available only after put-away       |
| `move_to_hold`       | `hold`, `damaged`       | non-pickable HOLD bin, `inventory_status='hold'`             |
| `move_to_quarantine` | `quarantine`, `damaged` | non-pickable QUARANTINE bin, `inventory_status='quality'`    |
| `scrap`              | `damaged`, `quarantine` | stock removed, exception closed                              |
| `return_to_dealer`   | any                     | stock removed, exception closed with the dealer as recipient |

---

## 4. Reference lookup (build the registration form on this)

### 4.1 `GET /returns/references`

Resolves the invoice / dealer / warehouse triple so the operator picks from real records instead of
typing free text (R-02). Read-only, safe to call on every keystroke with debounce.

```
GET /api/v1/returns/references?invoice_no=INV-2026-00123
GET /api/v1/returns/references?party_id=<customer_uuid>
GET /api/v1/returns/references?invoice_no=INV-2026-00123&warehouse_id=<uuid>
```

```json
{
  "invoice": {
    "id": "9f0f5f8e-…",
    "invoice_no": "INV-2026-00123",
    "invoice_type": "sales",
    "posting_date": "2026-08-30T00:00:00Z",
    "status": "submitted",
    "grand_total": 12500.0,
    "currency": "USD",
    "party": { "id": "c1a2…", "type": "customer", "name": "Prestige Traders" },
    "warehouse": { "id": "f0099ec7-…", "name": "Ecity" }
  },
  "lines": [
    {
      "line_id": "…",
      "item_id": "…",
      "sku": "TTK-COOK-897",
      "item_name": "Prestige Cooker 3L",
      "uom": "NOS",
      "invoiced_qty": 10,
      "already_returned_qty": 2,
      "returnable_qty": 8
    }
  ],
  "suggested_warehouse_id": "f0099ec7-…"
}
```

**Rules**

- `returnable_qty = invoiced_qty − already_returned_qty`. The UI **must** cap the quantity input at
  `returnable_qty` and hide lines where it is `0`.
- `404 RETURNS_REFERENCE_NOT_FOUND` when nothing matches — keep the operator on the form and show
  `hint` instead of redirecting.
- Serials: sales invoice lines do **not** carry a serial list today. The registration accepts an
  optional `serials[]` per line; when omitted, validation is SKU + quantity only. See §12 Q3.

---

## 5. Registrations

### 5.1 `POST /returns/registrations`

```json
{
  "reference_type": "invoice",
  "invoice_no": "INV-2026-00123",
  "party_id": "c1a2…",
  "warehouse_id": "f0099ec7-…",
  "return_reason_code": "RETURN_DAMAGED",
  "return_date": "2026-09-19",
  "note": "Dealer reported 2 damaged cookers on arrival",
  "lines": [
    {
      "sku": "TTK-COOK-897",
      "quantity": 2,
      "uom": "NOS",
      "serials": ["TTK-1T1ZB0"]
    },
    { "sku": "PTK-TOA-G001", "quantity": 1 }
  ]
}
```

**Response `201`** — the same body as `GET /returns/registrations/{id}` (§5.3).

| Field               | Required      | Notes                                                                |
| ------------------- | ------------- | -------------------------------------------------------------------- |
| `reference_type`    | yes           | `invoice` \| `dealer` \| `warehouse`. Only `invoice` carries lines   |
| `invoice_no`        | for `invoice` | Must resolve through §4.1 — otherwise `400 RETURN_REFERENCE_INVALID` |
| `party_id`          | for `dealer`  | Customer/dealer UUID                                                 |
| `warehouse_id`      | yes           | Receiving warehouse for the return                                   |
| `lines[]`           | yes           | At least one; `quantity ≥ 1`; SKU must be active in the org          |
| `lines[].serials[]` | no            | When present the handheld validates each scanned unit against it     |
| `registration_no`   | read-only     | Server-generated, series `RR` (e.g. `RR-2026-00042`)                 |

### 5.2 `GET /returns/registrations`

`?status=ready&warehouse_id=&party_id=&invoice_no=&from=&to=&page=1&page_size=20`

```json
{
  "items": [
    {
      "id": "…",
      "registration_no": "RR-2026-00042",
      "status": "ready",
      "party_name": "Prestige Traders",
      "warehouse_name": "Ecity",
      "warehouse_id": "…",
      "return_reason_code": "RETURN_DAMAGED",
      "expected_qty": 3,
      "received_qty": 0,
      "created_at": "2026-09-19T09:12:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 1,
  "total_pages": 1,
  "has_next": false,
  "has_prev": false
}
```

The list row is **flat** (`party_name`, `warehouse_name`, `warehouse_id`) and carries
`return_reason_code`, so the registration table can render the reason and preselect the picker
without a second call. Only `GET /returns/registrations/{id}` nests `party` / `warehouse` objects.

### 5.3 `GET /returns/registrations/{id}`

Detail used by both the review screen and the handheld's expected list:

```json
{
  "id": "…",
  "registration_no": "RR-2026-00042",
  "status": "receiving",
  "reference_type": "invoice",
  "invoice_no": "INV-2026-00123",
  "party": { "id": "…", "name": "Prestige Traders" },
  "warehouse": { "id": "…", "name": "Ecity" },
  "return_reason_code": "RETURN_DAMAGED",
  "note": "…",
  "expected_qty": 3,
  "received_qty": 2,
  "lines": [
    {
      "id": "…",
      "sku": "TTK-COOK-897",
      "item_name": "Prestige Cooker 3L",
      "uom": "NOS",
      "expected_qty": 2,
      "received_qty": 1,
      "serials": ["TTK-1T1ZB0"],
      "conditions": { "good": 1, "damaged": 0, "hold": 0, "quarantine": 0 }
    }
  ],
  "sessions": [
    { "id": "…", "status": "open", "started_at": "…", "worker_id": "…" }
  ]
}
```

### 5.4 `POST /returns/registrations/{id}/cancel`

```json
{ "reason": "Dealer cancelled the collection" }
```

- `409 RETURN_REGISTRATION_NOT_CANCELLABLE` once any unit has been scanned.
- `409 RETURN_REGISTRATION_ALREADY_CANCELLED` on a repeat call.

---

## 6. Return Receipt Notes

### 6.1 `GET /returns/receipt-notes` — supervisor queue

`?status=pending_approval&warehouse_id=&registration_id=&page=&page_size=`

The dock writes every note straight to `pending_approval` (§6.2), so this is the status a
supervisor queue should ask for. `draft` is only reachable through the note's own lifecycle.

```json
{
  "items": [
    {
      "id": "…",
      "note_no": "RRN-2026-00017",
      "status": "pending_approval",
      "registration_no": "RR-2026-00042",
      "warehouse_name": "Ecity",
      "expected_qty": 3,
      "received_qty": 2,
      "mismatch": true,
      "damaged_qty": 1,
      "open_exceptions": 1,
      "created_at": "2026-09-19T11:40:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 1,
  "total_pages": 1
}
```

Badges to render: `mismatch` (expected ≠ received), `damaged_qty`, `open_exceptions`.

### 6.2 `GET /returns/receipt-notes/{id}`

Same grouped shape as a receiving slip so the existing review component can be reused:

```json
{
  "id": "…",
  "note_no": "RRN-2026-00017",
  "status": "pending_approval",
  "registration_id": "…",
  "registration_no": "RR-2026-00042",
  "warehouse": { "id": "…", "name": "Ecity" },
  "expected_qty": 3,
  "received_qty": 2,
  "short_qty": 1,
  "groups": [
    {
      "product_name": "Prestige Cooker 3L",
      "sku": "TTK-COOK-897",
      "items": [
        {
          "id": "…",
          "serial_number": "TTK-1T1ZB0",
          "quantity": 1,
          "condition": "damaged",
          "reason_code": "RETURN_DAMAGED",
          "note": "Dent on the lid",
          "exception_id": "…",
          "destination": "QUARANTINE",
          "disposition": null
        }
      ]
    }
  ]
}
```

**Rendering rules**

- `expected_qty = 0` or a `pending` condition line ⇒ the note cannot be approved
  (`409 RETURN_NOTE_HAS_UNCLASSIFIED_LINES`).
- Show `theatre`: expected vs received per line, plus the short quantity — never silently hide a
  mismatch.
- Lines with an `exception_id` link to the exception queue (`GET /inbound/exceptions/{id}`).

### 6.3 `POST /returns/receipt-notes/{id}/approve`

```json
{
  "note": "Damaged unit accepted for quarantine",
  "dispositions": [
    {
      "line_id": "…",
      "action": "move_to_quarantine",
      "reason_code": "RETURN_DAMAGED"
    }
  ]
}
```

- Requires warehouse-manager authority (`409 RETURN_APPROVAL_REQUIRED` otherwise, with `hint`).
- `409 RETURN_NOTE_NOT_PENDING_APPROVAL` if it was already approved/rejected.
- Omitting `dispositions` accepts the handheld's proposed routing; supplying them overrides per line.

### 6.4 `POST /returns/receipt-notes/{id}/reject`

```json
{ "reason": "Two units expected, only one arrived" }
```

### 6.5 `POST /returns/receipt-notes/{id}/disposition`

Per-line final decision; safe to call for a single line.

```json
{
  "line_id": "…",
  "action": "move_to_hold",
  "reason_code": "HOLD",
  "note": "Awaiting QA"
}
```

- Allowed actions: `release_to_stock`, `move_to_hold`, `move_to_quarantine`, `scrap`,
  `return_to_dealer` (§3.4).
- `400 RETURN_DISPOSITION_INVALID` for a mismatch between condition and action
  (e.g. `release_to_stock` on a `quarantine` line).
- Badge the line as `disposed` afterwards; `GET` returns the stored `disposition`.

### 6.6 `POST /returns/receipt-notes/{id}/generate-put-away`

Creates put-away tasks for `release_to_stock` lines and keeps the rest in the non-pickable bins.

```json
{ "worker_ids": ["…"], "note": "Split across two workers" }
```

```json
{
  "put_away_lists": [
    {
      "id": "…",
      "list_no": "PA-2026-00119",
      "assigned_to": "…",
      "item_count": 1
    }
  ],
  "segregated_lines": 1,
  "note_status": "approved"
}
```

- `409 RETURN_PUTAWAY_ALREADY_GENERATED` on a repeat call (idempotent guard).
- Good stock is **not** available until the handheld completes put-away — show a
  `Pending put-away` chip, not `In stock`.

### 6.7 `GET /returns/receipt-notes/{id}/slip`

The Return Slip document: expected vs received per line, serials, conditions, reason codes,
approver, immutable timestamps.

- **JSON only today.** The endpoint returns `ReturnSlipResponse`; it has no `format` parameter.
  CSV/PDF export is still open in the gap analysis (`EXPORT_*`), so do not build a download
  button against `?format=csv` yet.

```json
{
  "slip_no": "RRN-2026-00017",
  "generated_at": "2026-09-19T12:05:00Z",
  "registration_no": "RR-2026-00042",
  "invoice_no": "INV-2026-00123",
  "party": { "name": "Prestige Traders" },
  "warehouse": { "name": "Ecity" },
  "approved_by": "…",
  "approved_at": "…",
  "lines": [
    {
      "sku": "…",
      "expected_qty": 3,
      "received_qty": 2,
      "conditions": { "good": 1, "damaged": 1 },
      "reason_codes": ["RETURN_DAMAGED"],
      "serials": ["TTK-1T1ZB0"]
    }
  ],
  "totals": { "expected_qty": 3, "received_qty": 2, "short_qty": 1 }
}
```

---

## 7. Reason codes

Reuse the existing tenant-configurable list — do **not** hard-code codes in the UI:

```
GET /api/v1/inbound/exception-reasons
→ [{ "code": "RETURN_DAMAGED", "name": "Returned damaged", "category": "return_damage",
     "default_destination": "QUARANTINE", "requires_approval": true,
     "applies_to_conditions": ["damaged"] }, …]

# Optional filters (additive, omitting them keeps the full list):
GET /api/v1/inbound/exception-reasons?condition=damaged
GET /api/v1/inbound/exception-reasons?category=return_damage
```

`?condition=` (`good|damaged|hold|quarantine`) returns only the reasons valid for a returned unit in
that condition — `damaged` → `DAMAGED`, `RETURN_DAMAGED`, `RETURN_SCRAP`; `quarantine` → `QUARANTINE`;
`hold` → `HOLD`; `good` → `RETURN_GOOD`. Inbound-only codes (`SHORT_PHYSICAL`, `EXCESS`,
`UNKNOWN_IDENTITY`, `QR_UNREADABLE`, `DUPLICATE_SERIAL`, …) are excluded. Every reason also carries
`applies_to_conditions` (empty for inbound-only codes) so the mapping is data-driven rather than
hard-coded.

| Picker                      | Filter                                                            |
| --------------------------- | ----------------------------------------------------------------- |
| Registration return reason  | `category === 'return_good' \| 'return_damage' \| 'return_scrap'` |
| Per-line disposition reason | category matching the condition (`damage`, `quarantine`, `hold`)  |
| Scrap / dealer return       | `category === 'return_scrap'`                                     |

New codes are seeded by the returns MVP (`RETURN_GOOD`, `RETURN_DAMAGED`, `RETURN_SCRAP`); see the
gap-analysis appendix for the proposed set.

---

## 8. Error catalogue

Errors for `ValidationError` / `NotFoundError` / `StateError` use the envelope already shipped for
receiving:

```json
{
  "error": "RETURN_UNIT_NOT_REGISTERED",
  "message": "…",
  "hint": "…",
  "details": [{ "field": "sku", "reason": "…", "hint": "…" }]
}
```

http status: `400` validation · `404` not found · `409` state conflict · `403` permission.

| HTTP | `error`                               | When                                            | UI behaviour                                |
| ---- | ------------------------------------- | ----------------------------------------------- | ------------------------------------------- |
| 404  | `RETURNS_REFERENCE_NOT_FOUND`         | Invoice/party/warehouse did not resolve         | Keep the form, show `hint`, focus the field |
| 400  | `RETURN_REFERENCE_REQUIRED`           | No reference supplied                           | Inline error on the reference picker        |
| 400  | `RETURN_REFERENCE_INVALID`            | Reference type/invoice combination not usable   | Show `details[].hint`                       |
| 400  | `RETURN_LINES_REQUIRED`               | Empty `lines[]`                                 | Disable submit until a line is added        |
| 400  | `RETURN_LINE_INVALID`                 | qty ≤ 0, unknown/inactive SKU, qty > returnable | Inline error per line (`details[].field`)   |
| 404  | `RETURN_REGISTRATION_NOT_FOUND`       | Wrong/foreign-tenant id                         | Back to the list + toast                    |
| 409  | `RETURN_REGISTRATION_NOT_CANCELLABLE` | Units already scanned                           | Disable Cancel, explain why                 |
| 404  | `RETURN_RECEIPT_NOTE_NOT_FOUND`       | Wrong id                                        | Back to the queue                           |
| 409  | `RETURN_NOTE_NOT_PENDING_APPROVAL`    | Approved/rejected already                       | Reload the note, hide the approve bar       |
| 409  | `RETURN_NOTE_HAS_UNCLASSIFIED_LINES`  | A line is still `pending`                       | Highlight those lines, block approve        |
| 409  | `RETURN_NOTE_HAS_OPEN_EXCEPTIONS`     | An exception must be disposed first             | Deep-link to the exception                  |
| 409  | `RETURN_APPROVAL_REQUIRED`            | Caller is not a warehouse manager               | Show "Ask a warehouse manager"              |
| 400  | `RETURN_DISPOSITION_INVALID`          | Condition/action mismatch                       | Constrain the dropdown by condition         |
| 409  | `RETURN_PUTAWAY_ALREADY_GENERATED`    | Put-away generated twice                        | Reload; show the existing lists             |
| 409  | `RETURN_REGISTRATION_CANCELLED`       | Acting on a cancelled registration              | Read-only view                              |
| 403  | —                                     | Missing `return.*` permission                   | Hide the action entirely                    |

> **Change control:** these codes are the interface contract. If the backend must differ, the two
> integration docs and the gap analysis are updated together — do not ship a silent rename.

---

## 9. Permissions

| Action                         | Permission                                        |
| ------------------------------ | ------------------------------------------------- |
| View registrations / notes     | `return.read`                                     |
| Create / cancel a registration | `return.register`                                 |
| Approve / reject a note        | `return.approve` + **manager** (`assert_manager`) |
| Per-line disposition           | `return.dispose` + **manager**                    |
| Generate put-away              | `return.approve`                                  |
| Export the Return Slip         | `return.read`                                     |

`return.*` are new codes added alongside the existing `inbound_exception.*` in
`app/core/authorization.py` (R-10 / X-02). Roles: warehouse manager / org admin get all;
supervisors get `return.read` + `return.approve`; the dock role gets `return.receive` /
`return.classify` only (handheld doc).

---

## 10. UI rules & gotchas

1. **Never optimistically approve.** Approval moves stock; always wait for the response.
2. **Expected vs received must always be visible** — the requirement is explicit that expected
   numbers are never silently altered. Show the short quantity, do not re-base the expectation.
3. **Approved notes are immutable.** No line edits after `approved`; corrections happen through a
   new return or an exception disposition.
4. **`release_to_stock` ≠ available.** Show `Pending put-away` until the handheld confirms; the
   put-away list chips come from `GET /put-away` (detail `GET /put-away/{put_away_list_id}`).
5. **Cancelled registrations are read-only** — hide Start receiving, approve and disposition.
6. **Quantity units**: render the line `uom`; server quantities are decimals and may not be integers.
7. **Deep links**: `exception_id` → `GET /inbound/exceptions/{id}`; `registration_id` → §5.3;
   put-away lists → `GET /put-away` (detail `GET /put-away/{put_away_list_id}`).

---

## 11. Frontend test checklist

| #   | Scenario                          | Call                                                 | Expect                                                       |
| --- | --------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| 1   | Reference lookup by invoice       | `GET /returns/references?invoice_no=…`               | `200`, lines with `returnable_qty`                           |
| 2   | Unknown invoice                   | same, bogus number                                   | `404 RETURNS_REFERENCE_NOT_FOUND` + hint                     |
| 3   | Create registration               | `POST /returns/registrations`                        | `201`, `registration_no` `RR-…`, status `draft`/`ready`      |
| 4   | Create with qty > returnable      | same                                                 | `400 RETURN_LINE_INVALID`, per-line error                    |
| 5   | Create with no lines              | same, `lines: []`                                    | `400 RETURN_LINES_REQUIRED`                                  |
| 6   | Cancel before any scan            | `POST /registrations/{id}/cancel`                    | `200`, status `cancelled`                                    |
| 7   | Cancel after a scan               | same                                                 | `409 RETURN_REGISTRATION_NOT_CANCELLABLE`                    |
| 8   | Note queue badges                 | `GET /returns/receipt-notes?status=pending_approval` | `mismatch` / `damaged_qty` / `open_exceptions` set correctly |
| 9   | Approve with an unclassified line | `POST …/approve`                                     | `409 RETURN_NOTE_HAS_UNCLASSIFIED_LINES`                     |
| 10  | Approve as non-manager            | same with a worker token                             | `409 RETURN_APPROVAL_REQUIRED` (or `403`)                    |
| 11  | Disposition per line              | `POST …/disposition`                                 | `200`, line shows `disposition`, stock status tag updates    |
| 12  | Invalid disposition for condition | `release_to_stock` on a `quarantine` line            | `400 RETURN_DISPOSITION_INVALID`                             |
| 13  | Generate put-away twice           | `POST …/generate-put-away` twice                     | `409 RETURN_PUTAWAY_ALREADY_GENERATED` on the second call    |
| 14  | Return Slip export                | `GET …/slip` (and `?format=csv`)                     | Document with conditions, serials, approver, timestamps      |
| 15  | Cross-tenant id                   | any `{id}` from another org                          | `404`, never data                                            |

---

## 12. Open business questions that change this UI

These come from the gap-analysis §6 and are **not** settled — build the screens so they are cheap to
flip once answered:

1. **Q2 — registration source.** Always an existing WMS invoice, or may a return be registered
   against a free-text dealer/warehouse reference? Today §5.1 requires `reference_type` + a resolved
   reference; free-text would add a `reference_note` mode.
2. **Q3 — serials.** Non-serialized/bulk returns are in scope for v1? Decides whether the serial list
   in §5.1/§6.2 is mandatory (hard stop on an unexpected serial) or informational.
3. **Q4 — numbering.** Confirm prefixes `RR` / `RRN` and whether the series is per-warehouse or per
   organization (`DocumentNumberingService.DEFAULT_PREFIXES`).
4. **Q7 — excess on a return.** Should receiving more than expected block approval, or only warn?
   The plan is a `mismatch` badge + supervisor decision, never a silent expectation change.
5. **Q8 — damaged bin.** `move_to_quarantine` vs a dedicated `DAMAGED` destination (the inbound
   `DAMAGED` bin now exists — see the gap analysis §3.2). If returns route there too, a fourth chip
   appears in §3.4.

---

## 13. Backend implementation map (for the API reviewer)

| Concern                 | Where                                                                                                                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Models                  | `app/models/returns.py` (registration, session, receipt note — new)                                                                                                                                           |
| Service                 | `app/services/return_service.py` (registration, session, note, disposition, put-away)                                                                                                                         |
| Endpoints               | `app/api/v1/endpoints/returns.py` + registration in `app/api/v1/router.py`                                                                                                                                    |
| Schemas                 | `app/schemas/returns.py`                                                                                                                                                                                      |
| Numbering               | `return_registration` (`RR`) + `return_receipt` (`RRN`) in `document_numbering.py`                                                                                                                            |
| Permissions             | `return.read` / `.register` / `.receive` / `.classify` / `.approve` / `.dispose` in `app/core/authorization.py`; seeded by identity migration `022`                                                           |
| Migrations              | core `124_returns_module` → `return_registrations`, `return_registration_items`, `return_sessions`, `return_session_items`, `return_receipt_notes`, `return_receipt_note_items`, `return_receipt_note_events` |
| Reason codes            | `RETURN_GOOD` / `RETURN_DAMAGED` / `RETURN_SCRAP` seeded by migration `124`                                                                                                                                   |
| Reuse (no new endpoint) | `InboundExceptionService.assert_manager`, `BinStockService`, `PutAwayService` bin allocation, `DocumentNumberingService`, `GET /inbound/exception-reasons`, `GET /put-away` + put-away completion             |
| Demo seeder             | `app/_seed_returns_demo.py` — creates dispatch references and drives both warehouses end-to-end                                                                                                               |

---

## 14. Implementation notes (differences from v1.0)

Four points where the shipped behaviour is deliberately narrower or more explicit than the v1.0
contract. Screens built against §3–§6 keep working; these only remove ambiguity.

1. **`POST /returns/registrations` returns the registration in `ready`, not `draft`.**
   Lines are validated as part of creation, and v1.0 had no endpoint that performed the
   draft → ready confirmation. `draft` remains a valid stored status but is not produced, so the
   dock can start receiving immediately. If a two-step confirmation is wanted later, add the
   missing transition endpoint rather than changing the create semantics.
2. **Ending a session creates the note in `pending_approval`, not `draft`.** The dock has already
   captured every line and condition, and §6.3 requires a note to be `pending_approval` before it
   can be approved — so producing `draft` would leave the note unreachable by the documented
   approve flow. The queue filter `?status=pending_approval` therefore shows new notes at once.
   `draft` remains valid in the status model for a future manual-edit step.
3. **`GET /returns/references` resolves against delivery notes, not `invoices`.** The tenant's
   `invoices` table holds SaaS subscription billing (`seat_count`, `billing_cycle`, no
   warehouse or customer link), so it cannot produce the §4.1 response. The lookup targets the
   dispatch document that actually recorded the outbound movement, and returns
   `invoice.invoice_type = "delivery_note"` with `invoice_no` carrying the delivery-note number.
   `?invoice_no=` accepts a delivery-note number. The response shape is otherwise unchanged, and
   `already_returned_qty` is still derived per line so the UI can cap the input.
4. **Serial validation only applies when the registration supplies `lines[].serials`.** With no
   serial list the handheld validates SKU + quantity only, which keeps bulk returns working
   (open question §12 Q3). When serials _are_ supplied, a mismatch is the hard
   `409 RETURN_SERIAL_NOT_REGISTERED` stop described in §4.1.

Two further behaviours worth knowing:

- **Duplicate identity.** Scanning a unit that is already in active stock raises
  `409 DUPLICATE_SERIAL`, records an `inbound_exceptions` row (`source: returns`, HOLD,
  `pending_approval`) and creates **no** receipt line.
- **Segregation status.** Non-good lines are placed in their HOLD/QUARANTINE/DAMAGED bin with
  `inventory_status` `hold` / `quality` / `damaged` (never `available`), so held or damaged
  return stock cannot be picked. Verified for both warehouses.

Three live-shape clarifications the mobile client raised, all now reflected above:

- **`classify/bulk` returns a bare array**, not `{ "items": [ … ] }`.
- **`POST /sessions/{id}/end` returns `200`** (not `201`) and creates the note directly in
  `pending_approval`.
- **`destination` is `null` for a `good` line** (nothing is segregated).

One endpoint was added for the handheld, so the dock can report a torn label on a return:
**`POST /returns/sessions/{id}/unreadable`** (`carton_reference` in the body, session in the path).
It mirrors the inbound report exactly — `QR_UNREADABLE`, `destination=HOLD`,
`pending_approval`, no stock, no counter movement, supervisors alerted, repeat report →
`409 EXCEPTION_ALREADY_ACTIVE`. The inbound `POST /inbound/exceptions/unreadable-qr` is unchanged
and still resolves against inbound sessions only.

**Permission codes are now readable by the client.** `return.*` is exported in two places, both
resolved from the same query identity `GET /me` serves (so client and server never disagree):

1. a `permissions: string[]` claim **in the access token** — canonical, because it survives a token
   refresh; and
2. a `permissions: string[]` array on the **login `user` payload** — no JWT decoding needed.

Gate the Returns screens on `return.read`. `warehouse_work_user` / `wms_operator` receive
`return.read` + `return.receive` + `return.classify` but **not** `return.register`,
`return.approve` or `return.dispose`; `viewer`, `accountant`, `sales_agent` and
`procurement_officer` receive none of them.
