# Returns — Handheld (HC) Device Integration Guide

> **Version**: 1.1 (implemented — local/dev verified 2026-09-20)
> **Date**: 2026-09-20
> **Audience**: Handheld / mobile app developers (React Native / Flutter) working the dock
> **Base URL**: `http://<host>/api/v1` > **Status**: ✅ **IMPLEMENTED** — all `/returns/…` endpoints below are live
> (migration `124_returns_module`, permissions identity `022`). `POST
/inbound/exceptions/unreadable-qr`, `GET /inbound/exception-reasons`, `GET /items` and the
> put-away endpoints were already live. See the web-app doc §13 for the implementation notes
> that differ from v1.0.
> **Companion doc**: `RETURNS_WEB_APP_INTEGRATION.md` (registration, approval, Return Slip).
> **Related**: `MOBILE_APP_INBOUND_GUIDE.md` (receiving conventions), `MOBILE_APP_API_REFERENCE.md`.

---

## 1. What the device does (and never does)

| Device responsibility                                                                        | Not the device's job                                          |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Start a return receiving session against a registration                                      | Create or approve a registration                              |
| Scan returned units / cartons and validate the identity                                      | Change expected quantities                                    |
| Capture the **condition** of every unit (`good`/`damaged`/`hold`/`quarantine`) + reason code | Approve / reject the Return Receipt Note                      |
| End the session → draft Return Receipt Note                                                  | Choose the final disposition (`scrap`, `return_to_dealer`, …) |
| Report an unreadable label (records + alerts the supervisor)                                 | Relabel / mint a new identity                                 |
| Confirm put-away of `good` stock into a bin                                                  | Decide where `damaged` / `hold` stock goes                    |

Everything the device sends is **evidence**; the supervisor decides (web app).

---

## 2. Session lifecycle

```
GET  /returns/registrations?status=ready&warehouse_id=…   (pick the return to receive)
GET  /returns/registrations/{id}                          (expected lines + serials)
POST /returns/registrations/{id}/sessions                 (open a session → status 'receiving')
      ├── POST /returns/sessions/{id}/scans               (repeat per unit/carton)
      ├── POST /returns/sessions/{id}/classify            (repeat per unit: condition + reason)
      └── POST /returns/sessions/{id}/unreadable          (when a label cannot be read)
POST /returns/sessions/{id}/end                           (→ note pending_approval, registration 'received')
```

Rules

- **One open session per registration.** A second `POST …/sessions` with an open session already on
  the registration returns `409 RETURN_SESSION_ALREADY_OPEN` — resume that one instead.
- The registration is only receivable in `ready` (or the session's own `receiving`). Any other status
  → `409 RETURN_REGISTRATION_NOT_RECEIVABLE` / `409 RETURN_REGISTRATION_CANCELLED`.
- Every scanned unit **must** be classified before `…/end`, otherwise
  `409 RETURN_SESSION_HAS_UNCLASSIFIED_ITEMS` and the note is not produced.

---

## 3. Endpoint reference

### 3.1 `POST /returns/registrations/{id}/sessions`

```json
{ "dock_location": "DOCK-B", "device_id": "HC-07" }
```

```json
{
  "id": "sess-uuid",
  "registration_id": "…",
  "registration_no": "RR-2026-00042",
  "warehouse": { "id": "…", "name": "Ecity" },
  "status": "open",
  "dock_location": "DOCK-B",
  "started_at": "2026-09-19T11:02:00Z",
  "expected_qty": 3,
  "scanned_qty": 0,
  "classified_qty": 0
}
```

**Permission**: `return.receive`

### 3.2 `GET /returns/sessions/{id}` — resume / poll state

Returns the header above plus the per-line counters and the pending queue:

```json
{
  "id": "sess-uuid",
  "status": "open",
  "expected_qty": 3,
  "scanned_qty": 2,
  "classified_qty": 1,
  "lines": [
    {
      "line_id": "…",
      "sku": "TTK-COOK-897",
      "item_name": "Prestige Cooker 3L",
      "uom": "NOS",
      "expected_qty": 2,
      "scanned_qty": 2,
      "classified_qty": 1,
      "serials": ["TTK-1T1ZB0"]
    }
  ],
  "items": [
    {
      "id": "item-uuid",
      "qr_identifier": "TTK-1T1ZB0",
      "sku": "TTK-COOK-897",
      "serial_number": "TTK-1T1ZB0",
      "quantity": 1,
      "condition": null,
      "reason_code": null,
      "exception_id": null
    }
  ]
}
```

`condition: null` ⇒ still needs classification — drive the "N to classify" badge from this list.

**Permission**: `return.read`

### 3.3 `POST /returns/sessions/{id}/scans`

```json
{
  "qr_data": "{\"id\":\"TTK-1T1ZB0\",\"sku\":\"TTK-COOK-897\",\"qty\":1,\"batch\":\"BT-SEP-19\"}",
  "device_type": "mobile",
  "os": "Android 14"
}
```

```json
{
  "item_id": "item-uuid",
  "qr_identifier": "TTK-1T1ZB0",
  "sku": "TTK-COOK-897",
  "matched_line_id": "…",
  "quantity": 1,
  "serial_expected": true,
  "over_receipt": false,
  "condition": null,
  "scanned_qty": 1,
  "expected_qty": 2,
  "next_action": "classify"
}
```

**Permission**: `return.receive`

`next_action` tells the device what to do after a good scan: `classify` (happy path) or
`report_unreadable` (when the payload decoded to nothing usable — see §4.3).

### 3.4 `POST /returns/sessions/{id}/classify` and `…/classify/bulk`

```json
{
  "item_id": "item-uuid",
  "condition": "damaged",
  "reason_code": "RETURN_DAMAGED",
  "note": "Dent on the lid"
}
```

```json
{
  "items": [
    { "item_id": "…", "condition": "good" },
    { "item_id": "…", "condition": "quarantine", "reason_code": "QUARANTINE" }
  ]
}
```

Both classify endpoints return the **same object shape**; `classify/bulk` returns a **bare JSON
array** of them (one entry per item), _not_ an `{ "items": [ … ] }` wrapper.

```json
{
  "item_id": "item-uuid",
  "condition": "damaged",
  "reason_code": "RETURN_DAMAGED",
  "destination": "QUARANTINE",
  "exception_id": "…",
  "exception_status": "pending_approval"
}
```

- `condition`: `good` | `damaged` | `hold` | `quarantine`.
- A **non-`good`** condition requires a `reason_code` → `400 RETURN_REASON_CODE_REQUIRED`.
- `destination` is derived from the reason's `default_destination` (falling back to `QUARANTINE`);
  the device may override with `destination: "HOLD" | "QUARANTINE" | "DAMAGED"`.
- `destination` is **`null`** for a `good` unit (and `exception_id` / `exception_status` are `null`
  too) — a good unit is not segregated, so render no destination chip for it.
- Classifying creates an inbound exception (`pending_approval`) and segregates the stock into the
  matching non-pickable bin with `inventory_status` `hold` / `quality` / `damaged` — no extra call.
- Repeated classify on the same unit → `409 RETURN_ITEM_ALREADY_CLASSIFIED` (offer "Change reason",
  which re-sends with `override: true`).

**Permission**: `return.classify`

### 3.5 `POST /returns/sessions/{id}/end`

```json
{ "note": "One unit damaged, rest good" }
```

```json
{
  "receipt_note": {
    "id": "…",
    "note_no": "RRN-2026-00017",
    "status": "pending_approval"
  },
  "registration_status": "received",
  "expected_qty": 3,
  "received_qty": 2,
  "short_qty": 1,
  "conditions": { "good": 1, "damaged": 1, "hold": 0, "quarantine": 0 },
  "next": "Supervisor review in the web app"
}
```

**Returns `200`, not `201`** (the note reuses the session resource). The note is created directly in
`pending_approval` — the dock captured every line and every condition, so it lands in the
supervisor's queue immediately and there is no separate "submit for approval" step.

**Permission**: `return.receive`

### 3.6 Reused endpoints — do **not** build new ones

| Need                                    | Endpoint (live today)                                        |
| --------------------------------------- | ------------------------------------------------------------ |
| Unreadable / unscannable label          | `POST /returns/sessions/{id}/unreadable` (§4.2)              |
| Reason-code picker                      | `GET /inbound/exception-reasons?condition=`                  |
| Item lookup by SKU (never stock-levels) | `GET /items?search=`                                         |
| List my put-away tasks                  | `GET /put-away` (detail: `GET /put-away/{put_away_list_id}`) |
| Confirm put-away into a bin             | `POST /put-away/{put_away_list_id}/items/{item_id}/complete` |

Put-away for returned `good` stock uses the **same** task list and confirmation flow as inbound
receiving (`MOBILE_APP_INBOUND_GUIDE.md` §4) — no returns-specific put-away UI.

---

## 4. Scan validation — the rules the device must surface

### 4.1 Validation matrix

| Case                                         | Server response                          | Device UI                                                     |
| -------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------- |
| Identity on the registration (SKU + serial)  | `201`                                    | Green, move straight to condition capture                     |
| SKU on the registration, serial not listed   | `409 RETURN_SERIAL_NOT_REGISTERED`       | Red banner + "Report as unexpected / call supervisor"         |
| SKU not on the registration at all           | `404 RETURN_UNIT_NOT_REGISTERED`         | Red, offer the unreadable/unexpected action                   |
| Unit already scanned in **this** session     | `409 RETURN_UNIT_ALREADY_SCANNED`        | Amber "already captured" — jump to that item, do not retry    |
| Identity already in **active stock**         | `409 DUPLICATE_SERIAL`                   | Red — the unit was never dispatched; supervisor investigation |
| Line already at its registered quantity      | `201` with `over_receipt: true`          | Amber warning; keep scanning, the supervisor decides          |
| All lines fully received                     | `409 RETURN_REGISTRATION_FULLY_RECEIVED` | Offer "End session"                                           |
| Malformed / undecodable payload              | `400 RETURN_QR_INVALID`                  | Offer "Report unreadable label" (§4.2)                        |
| Session closed / ended                       | `409 RETURN_SESSION_NOT_OPEN`            | Return to the session picker                                  |
| QR already **put away** by an earlier return | `409 DUPLICATE_SERIAL`                   | Red — same handling as active stock                           |
| Damaged unit already classified              | `409 RETURN_ITEM_ALREADY_CLASSIFIED`     | Use "Change reason" (`override: true`)                        |

### 4.2 Unreadable label — `POST /returns/sessions/{id}/unreadable`

When the operator cannot read the label, **never** let them type an identity. Call the
**returns-scoped** endpoint (the inbound one resolves its session against `scan_sessions` and will
reject a returns session id with `404 SCAN_SESSION_NOT_FOUND`):

```
POST /api/v1/returns/sessions/{session_id}/unreadable
{ "carton_reference": "TTK-1T1ZB0", "sku": "TTK-COOK-897",
  "batch_number": "BT-SEP-19", "quantity": 1, "note": "Label torn" }
→ 201 { "reason_code": "QR_UNREADABLE", "destination": "HOLD", "status": "pending_approval", … }
```

- The `session_id` is in the **path** (the inbound endpoint took it in the body).
- `carton_reference` is required and is what the operator **reads off the carton** (printed
  serial/batch/ASN line); `sku`, `batch_number`, `quantity` and `note` are optional.
- No stock is created, no return counter moves (`scanned_qty`, `classified_qty` and the
  registration's `received_qty` are untouched), and the supervisors are alerted automatically.
- Reporting the same carton twice in a session → `409 EXCEPTION_ALREADY_ACTIVE` (show "already
  reported" and move on).
- An unknown session → `404 RETURN_SESSION_NOT_FOUND`; a session that is no longer open →
  `409 RETURN_SESSION_NOT_OPEN`.

**Permission**: `return.receive` (or `inbound_exception.create`)

### 4.3 Condition capture UX

- One screen per unit, four large buttons: **Good / Damaged / Hold / Quarantine** (thumb-reachable,
  glove-friendly, ≥ 48 dp).
- `Good` is one tap. Any other condition opens the reason picker
  (`GET /inbound/exception-reasons?condition=<condition>`) and then a free-text note (optional).
- **Filter the picker server-side** — do not hard-code a category map. `?condition=damaged` returns
  exactly `DAMAGED`, `RETURN_DAMAGED`, `RETURN_SCRAP`; `?condition=quarantine` returns `QUARANTINE`;
  `?condition=hold` returns `HOLD`; `?condition=good` returns `RETURN_GOOD`. Omitting `condition`
  returns every active code (that is the inbound receiving behaviour and is unchanged).
  Each reason also carries `applies_to_conditions: string[]`, so the mapping is readable from the
  payload — it is `[]` for inbound-only codes such as `SHORT_PHYSICAL` or `QR_UNREADABLE`.
- Show the server-derived destination exactly as returned, so the operator knows where to put the
  unit. It is **not** always `QUARANTINE`: it follows the chosen reason code (`HOLD` for `HOLD`,
  `DAMAGED` for `RETURN_SCRAP`, `QUARANTINE` for `RETURN_DAMAGED`, …). Render the field, never a
  hard-coded bin name.
- Support **bulk good** for a carton ("All good") — `…/classify/bulk` with the scanned item ids.
- Default the picker from the reason the registration was created with, but never auto-classify a
  non-good unit without an explicit tap.

---

## 5. Offline & error handling

1. **Scans are the only retryable operation.** Safe retry after a timeout: the same
   `qr_identifier` in the same session is idempotent **for the client** — treat
   `409 RETURN_UNIT_ALREADY_SCANNED` as success and continue.
2. **Never queue classification or session-end offline.** Condition capture creates exceptions and
   moves stock; a stale queue would move stock twice. Requirement: online for those two calls.
3. **Do not queue approvals.** The device never approves anything.
4. **Session recovery**: persist `session_id` locally; on app restart call `GET /returns/sessions/{id}`
   and rebuild the pending list from `items[].condition === null`.
5. **Token expiry mid-shift**: refresh and replay only the current scan, never a classification.
6. **Never show a success toast before the server responds** — every scan changes auditable state.

---

## 6. Permissions & role

| Operation                      | Permission                          | Dock role (`warehouse_work_user` equivalent) |
| ------------------------------ | ----------------------------------- | -------------------------------------------- |
| List / read registrations      | `return.read`                       | ✅                                           |
| Open a return session          | `return.receive`                    | ✅                                           |
| Record scans                   | `return.receive` + `wms.scan`       | ✅                                           |
| Report an unreadable label     | `inbound_exception.create`          | ✅                                           |
| Classify conditions            | `return.classify`                   | ✅                                           |
| End the session                | `return.receive`                    | ✅                                           |
| Approve the note / dispose     | `return.approve` / `return.dispose` | ❌ Supervisor only                           |
| Create / cancel a registration | `return.register`                   | ❌ Back-office only                          |

`return.receive` / `return.classify` are the returns dock codes (R-10 / X-02), seeded by identity
migration `022`. They are granted to `warehouse_work_user`, `wms_operator`, `wms_manager` and
`wms_admin` — and deliberately **not** to `viewer`, `accountant`, `sales_agent` or
`procurement_officer`.

**Where the client reads them.** The same codes are exposed in **two** places, both resolved from
the same query that identity `GET /me` serves (so client and server never disagree):

1. a `permissions: string[]` claim **in the access token** — canonical, because it survives a token
   refresh; and
2. a `permissions: string[]` array on the **login `user` payload** — convenient at sign-in without
   decoding the JWT.

Gate the Returns tab on `return.read`. Note the dock account used for testing
(`ttkwmsmanager@prestige.com`) holds the `*.*` wildcard, which grants everything — so it is a poor
subject for testing a negative gate; use a `viewer`-style account for that.

---

## 7. Error catalogue (device-facing)

Envelope (same as the receiving flow): `{"error", "message", "hint", "details"}` — **always show
`hint`**, it is written for the operator ("Report it as unreadable and hand the carton to the
supervisor", "This unit is already captured — check the pending list").

| HTTP | `error`                                 | Operator action                                               |
| ---- | --------------------------------------- | ------------------------------------------------------------- |
| 400  | `RETURN_QR_INVALID`                     | "Report unreadable label", retry the camera                   |
| 400  | `RETURN_CONDITION_REQUIRED`             | Force a condition tap before continuing                       |
| 400  | `RETURN_CONDITION_INVALID`              | Reset to the four supported buttons                           |
| 400  | `RETURN_REASON_CODE_REQUIRED`           | Open the reason picker                                        |
| 400  | `RETURN_REASON_CODE_INVALID`            | Refresh the picker (`GET /inbound/exception-reasons`)         |
| 400  | `RETURN_DESTINATION_INVALID`            | Clear the destination override (HOLD/QUARANTINE/DAMAGED only) |
| 404  | `RETURN_REGISTRATION_NOT_FOUND`         | Back to the registration list                                 |
| 404  | `RETURN_SESSION_NOT_FOUND`              | Recover the session (see §5.4)                                |
| 404  | `RETURN_UNIT_NOT_REGISTERED`            | Do not override; report unreadable / call the supervisor      |
| 409  | `RETURN_SERIAL_NOT_REGISTERED`          | Same as above — the serial is not on this return              |
| 409  | `RETURN_UNIT_ALREADY_SCANNED`           | Open the already-captured unit; do not retry blindly          |
| 409  | `DUPLICATE_SERIAL`                      | Hard stop — unit is already in stock; notify the supervisor   |
| 409  | `RETURN_ITEM_ALREADY_CLASSIFIED`        | Offer "Change reason"                                         |
| 409  | `RETURN_SESSION_HAS_UNCLASSIFIED_ITEMS` | Jump to the first unclassified unit                           |
| 409  | `RETURN_SESSION_NOT_OPEN`               | Session ended/abandoned — return to the picker                |
| 409  | `RETURN_SESSION_ALREADY_OPEN`           | Resume the open session instead of creating one               |
| 409  | `RETURN_REGISTRATION_NOT_RECEIVABLE`    | Registration state blocks receiving (cancelled/closed)        |
| 409  | `RETURN_REGISTRATION_FULLY_RECEIVED`    | Offer to end the session                                      |
| 409  | `EXCEPTION_ALREADY_ACTIVE`              | The unreadable carton is already reported                     |
| 403  | —                                       | Hide the action (permission missing)                          |

---

## 8. Device test checklist

| #   | Scenario                              | Call                                        | Expect                                                                 |
| --- | ------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| 1   | Pick a ready registration             | `GET /returns/registrations?status=ready`   | List with `expected_qty` / `received_qty`                              |
| 2   | Open a session                        | `POST /returns/registrations/{id}/sessions` | `201`, registration → `receiving`, counters at 0                       |
| 3   | Open a second session                 | same                                        | `409 RETURN_SESSION_ALREADY_OPEN`                                      |
| 4   | Scan an expected serial               | `POST …/scans`                              | `201`, `next_action=classify`, counters +1                             |
| 5   | Re-scan the same unit                 | same                                        | `409 RETURN_UNIT_ALREADY_SCANNED` + jump to the unit                   |
| 6   | Scan a serial not on the registration | same                                        | `409 RETURN_SERIAL_NOT_REGISTERED` (no stock change)                   |
| 7   | Scan an identity already in stock     | same                                        | `409 DUPLICATE_SERIAL` (no stock change, exception recorded)           |
| 8   | Scan beyond the registered quantity   | same                                        | `201` + `over_receipt: true`                                           |
| 9   | Classify damaged without a reason     | `POST …/classify`                           | `400 RETURN_REASON_CODE_REQUIRED`                                      |
| 10  | Classify damaged with a reason        | same                                        | `201`, `destination=QUARANTINE`, exception `pending_approval`          |
| 11  | Classify good                         | same                                        | `201`, no exception, unit stays available for put-away                 |
| 12  | Bulk good a carton                    | `POST …/classify/bulk`                      | All items classified, counts consistent                                |
| 13  | End with an unclassified unit         | `POST …/end`                                | `409 RETURN_SESSION_HAS_UNCLASSIFIED_ITEMS`                            |
| 14  | End after classifying everything      | `POST …/end`                                | `200`, note `pending_approval` + `RRN-…`, registration `received`      |
| 15  | Unreadable label flow                 | `POST /returns/sessions/{id}/unreadable`    | `201` HOLD `QR_UNREADABLE`; duplicate → `409 EXCEPTION_ALREADY_ACTIVE` |
| 16  | App restart mid-session               | `GET /returns/sessions/{id}`                | Pending list rebuilt from `condition === null`                         |
| 17  | Offline classification attempt        | any                                         | Blocked in the UI with a clear "connect to continue" message           |
| 18  | Classify with a non-dock account      | `POST …/classify`                           | `403`, action hidden                                                   |

Report the tenant/user, session id, `qr_identifier` and the `error` code with any failure — the
`hint` is operator-facing, the `error` code is what engineering needs.

---

## 9. Do-not list (mirrors `MOBILE_APP_INBOUND_GUIDE.md` §7)

| Don't                                              | Do                                                            |
| -------------------------------------------------- | ------------------------------------------------------------- |
| Let the operator type or "fix" an identity         | Report it as unreadable and hand the carton to the supervisor |
| Queue classification/session-end offline           | Require connectivity for anything that moves stock            |
| Treat `409 RETURN_UNIT_ALREADY_SCANNED` as a crash | Treat it as "already captured" and continue                   |
| Use `GET /stock-levels` to resolve an item         | Use `GET /items?search=`                                      |
| Add a returns-specific put-away screen             | Reuse the existing put-away list + confirm flow               |
| Show a success state before the server responds    | Wait for the response, then advance                           |
| Hard-code reason codes in the app                  | Load them from `GET /inbound/exception-reasons`               |
| Approve/alter the note on the device               | Leave approval to the supervisor in the web app               |

---

## 10. Settled questions & what still needs the business

**Answered — build against these:**

1. **Serials are optional (bulk returns are in scope).** Validation is SKU + quantity. A serial list
   is only enforced when the registration supplies `lines[].serials`; otherwise no
   `RETURN_SERIAL_NOT_REGISTERED` is raised. So the scan-per-unit flow stays the happy path, and a
   quantity-entry mode can be added later without a payload change.
2. **Over-receipt is a warning, never a hard stop.** The server accepts and returns
   `201` + `over_receipt: true`; the supervisor decides at approval. Do **not** block the scan.
3. **The `DAMAGED` destination is real — re-enable the chip.** The dedicated non-pickable `DAMAGED`
   bin exists and is provisioned on demand (migration `122`). A `damaged` classification with reason
   `RETURN_SCRAP` resolves to `destination: "DAMAGED"`, and `destination` may be overridden with any
   of `HOLD` / `QUARANTINE` / `DAMAGED`. Nothing routes "nowhere".
4. **No relabel workflow yet** (gap-analysis `E-10`). Until it exists, the unreadable screen ends at
   "supervisor notified" — there is no "waiting for relabel" state to poll.
5. **Role gating:** the dock account you are testing with holds `*.*`, so it passes every gate. Use a
   `viewer`-style account to verify that the Returns tab is actually hidden (§6).

---

## 11. Contract reconciliation (v1.1) — live API is canonical

The mobile client adapted to these live behaviours; the doc has been corrected to match. No API
change was made for items 1–6, so nothing the client already consumes is renamed.

| #   | v1.0 doc said                          | Live API (canonical)                                                                                      |
| --- | -------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1   | `classify/bulk` → `{ "items": [ … ] }` | **bare array** `[ … ]`                                                                                    |
| 2   | `receipt_note.status` = `"draft"`      | `"pending_approval"`                                                                                      |
| 3   | `…/end` → `201`                        | `200`                                                                                                     |
| 4   | classify `destination` always set      | `null` for a `good` unit                                                                                  |
| 5   | registration list nests `warehouse`    | list is **flat** (`warehouse_name` / `warehouse_id`); the **detail** endpoint nests `warehouse` / `party` |
| 6   | `lines[]` shape                        | **two shapes, by design** (see below)                                                                     |
| 7   | —                                      | **fixed in the API**: the list row now also returns `return_reason_code`                                  |

**Item 6 confirmed intent.** The two line shapes differ because they answer different questions:

- **Registration detail** (`GET /returns/registrations/{id}`) → _what was declared_: `id`,
  `expected_qty`, `received_qty`, `serials`, `conditions{}` (per-condition counts for the whole line).
- **Session** (`GET /returns/sessions/{id}`) → _what the dock has captured so far_: `line_id`,
  `scanned_qty`, `classified_qty`, `serials`.

Both are deliberate; do not expect one to mirror the other. Use the registration for the expected
list and the session for live progress.
