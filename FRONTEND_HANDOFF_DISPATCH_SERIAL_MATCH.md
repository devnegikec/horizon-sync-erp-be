# Frontend Handoff — Dispatch → Inbound Serial/QR Match

**For:** frontend team
**Backend status:** implemented and merged to `feature/wms_dispach_receipt_serieal_match`
**Reference code:** `frontend-reference/transferSerialMatch.api.ts`, `frontend-reference/TransferSerialMatchScreen.tsx`
**API contract:** `WMS_DISPATCH_SERIAL_MATCH_FRONTEND.md`

The backend already returns everything needed. Your job is to consume the new
fields/endpoints below. The old flows keep working — none of this is a breaking
change to the existing UI, except the two items marked **breaking**.

---

## Required changes (must-do to complete the feature)

### 1. Quantity-only banner on the receiving screen — **new**
- Where: dock receiving / inbound scan screen (where a worker scans units).
- Data: `serialization_mode` on the session payload and on `GET /asn-orders/{id}`.
- When `"quantity_only"`: show a warning banner — *"Verified by quantity only —
  unit serials were not captured."* Do not claim per-unit verification.
- Component: `QuantityOnlyBanner` (see reference).

### 2. Master-carton receive — replace the client-side loop — **breaking**
- Where: inbound scan screen, master-carton (parent QR) flow.
- **Replace** `GET /qseal/parents/{id}/linked-units` + N × `POST /inbound/sessions/{id}/scan`
  with one `POST /inbound/sessions/{id}/scan-carton`.
- Show the returned carton summary (`expected / received / duplicate / unexpected`
  + `serials[]`) before the worker ends the session.
- Component: `receiveCarton` + `CartonSummary` (see reference).

### 3. Serial-match screen — **new**
- Where: ASN detail / internal-transfer view.
- Data: `GET /asn-orders/{id}/transfer-verification`.
- Render: *"47 dispatched · 47 received · 0 missing"*, carton rollups, and a
  per-serial table with status badges `received / in_transit / missing / unexpected`.
- Component: `TransferVerificationScreen` (see reference).

### 4. ASN closure — handle the new block — **breaking**
- Where: ASN close action.
- `PUT /asn-orders/{id}/status` with `"closed"` now returns `422` when unreceived
  transfer serials remain.
- On that error, surface the message and route to short-close (manager approval)
  before closing.

### 5. Exception queue — new reason codes
- Where: inbound exception queue + disposition UI.
- Render `UNEXPECTED_SERIAL`, `WRONG_ITEM`, `MISSING_SERIAL`.
- `MISSING_SERIAL` has no physical unit → disposition is short-close, not a move.

---

## Optional changes (nice-to-have)

### 6. Receiving slip — show serials on the document
- Slip item payload now has `serial_nos` + `received_serial_count`; show them on
  the slip detail/print view.

### 7. Receiving summary — serial counts
- `receiving-summary` now returns `expected_serials / received_serials /
  missing_serials / unexpected_serials`; display next to quantity totals if useful.

---

## Acceptance criteria

| # | Given | When | Then |
|---|---|---|---|
| 1 | a quantity-only transfer session | worker opens receiving | warning banner is visible |
| 2 | a master carton with 24 units (1 wrong) | worker scans parent QR once | one call; summary shows 23 received + 1 unexpected |
| 3 | an internal-transfer ASN | user opens the match screen | dispatched/received/missing counts + per-serial table render |
| 4 | an ASN with unreceived serials | user tries to close | 422 message shown, closure blocked |
| 5 | a `MISSING_SERIAL` exception | supervisor opens queue | shown as shortage, short-close available |

---

## Notes

- No auth changes — the new endpoints reuse existing permissions
  (`asn_order.read`, `receiving_slip.create`).
- All response shapes are in `WMS_DISPATCH_SERIAL_MATCH_FRONTEND.md`; copy the
  TypeScript types from `frontend-reference/transferSerialMatch.api.ts`.
- Items 2 and 4 are the only **breaking** changes; everything else is additive.
