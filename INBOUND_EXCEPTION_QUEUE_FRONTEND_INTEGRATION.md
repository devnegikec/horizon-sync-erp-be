# Inbound Exception Queue — Frontend Integration Guide

This guide covers how the frontend integrates with the **inbound exception queue**:
hold, quarantine, return-to-sender, and dispose workflows for goods received with
discrepancies.

> **Base URL:** `/api/v1/inbound`
> **Auth:** Bearer token (`Authorization: Bearer <token>`) — same as the rest of the API.

---

## 1. Concepts

An **inbound exception** is a reason-coded record created when a receiving-slip line
(or a scan) cannot be accepted normally:

| Term | Meaning |
|------|---------|
| `classification` | What went wrong: `short`, `damaged`, `excess`, `hold`, `quarantine` |
| `reason_code` | The structured code explaining *why* (e.g. `DAMAGED`, `EXCESS`) |
| `destination` | Where the physical stock is segregated: `HOLD` or `QUARANTINE` |
| `condition_code` | WMS condition on the stock: `GOOD`, `DAMAGED`, `HOLD`, `QUARANTINE`, `REJECTED` |
| `status` | Lifecycle: `pending_approval`, `open`, `approved`, `released`, `closed` |
| `disposition` | The final decision: `release_to_receiving`, `move_to_hold`, `move_to_quarantine`, `return_to_sender`, `dispose` |

Held / quarantined stock lives in **non-pickable** system bins and never enters
normal put-away until a manager resolves it.

---

## 2. Permissions

The backend enforces these permission codes. The UI should hide/disable controls
accordingly:

| API | Permission code | Typical role |
|-----|-----------------|--------------|
| List reason codes | `inbound_exception.read` | Warehouse staff / manager |
| List exception queue | `inbound_exception.read` | Warehouse staff / manager |
| Classify (create exception) | `inbound_exception.create` | Dock / receiving staff |
| Upload evidence | `inbound_exception.create` | Dock / receiving staff |
| Dispose (final decision) | `inbound_exception.dispose` | **Warehouse manager** |

> Disposition additionally requires the acting user to be the warehouse **manager**
> (or org/system admin with `warehouse.manage` / `*.*`). The backend returns a
> `409`/`403` state error otherwise.

---

## 3. API Reference

### 3.1 List reason codes

```
GET /api/v1/inbound/exception-reasons
```

Returns the tenant-configurable reason codes used by the classify flow.

**Response:** `InboundExceptionReasonResponse[]`

```json
[
  {
    "code": "DAMAGED",
    "name": "Damaged goods",
    "category": "damage",
    "default_destination": "QUARANTINE",
    "requires_approval": true
  },
  {
    "code": "EXCESS",
    "name": "Excess receipt",
    "category": "excess",
    "default_destination": "HOLD",
    "requires_approval": true
  },
  {
    "code": "HOLD",
    "name": "Operational hold",
    "category": "hold",
    "default_destination": "HOLD",
    "requires_approval": false
  },
  {
    "code": "QUARANTINE",
    "name": "Quality or compliance quarantine",
    "category": "quarantine",
    "default_destination": "QUARANTINE",
    "requires_approval": false
  },
  {
    "code": "SHORT_PHYSICAL",
    "name": "Physical shortage",
    "category": "short",
    "default_destination": null,
    "requires_approval": false
  }
]
```

> **Seeded codes:** `SHORT_PHYSICAL`, `DAMAGED`, `EXCESS`,
> `UNEXPECTED_KNOWN_SKU`, `UNKNOWN_IDENTITY`, `HOLD`, `QUARANTINE`.

---

### 3.2 Classify a receiving-slip line (create an exception)

```
POST /api/v1/inbound/receiving-slips/{slip_id}/items/{item_id}/exception
```

Called when a reviewer flags a line on a slip that is still in `pending_review`.

**Request:** `InboundExceptionClassifyRequest`

```json
{
  "classification": "damaged",
  "reason_code": "DAMAGED",
  "destination": "QUARANTINE",
  "note": "Carton crushed on left side, photos attached."
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `classification` | ✅ | `short` \| `damaged` \| `excess` \| `hold` \| `quarantine` |
| `reason_code` | ✅ | Must match a code from 3.1 |
| `destination` | ⚠️ | `HOLD` or `QUARANTINE`; required for `damaged`/`hold`/`quarantine`/`excess` |
| `note` | ➖ | Free text (max 2000) |

**Response (201):** `InboundExceptionResponse` — see §4.

**Errors:**

| Status | Meaning |
|--------|---------|
| `404` | Slip or line not found |
| `409` | Slip not `pending_review`, or line already has an active exception |
| `422` | Invalid `classification`, `destination`, or unknown `reason_code` |

---

### 3.3 List the exception queue

```
GET /api/v1/inbound/exceptions
```

**Query parameters (all optional):**

| Param | Type | Notes |
|-------|------|-------|
| `warehouse_id` | UUID | Filter by warehouse |
| `destination` | string | `HOLD` or `QUARANTINE` |
| `status` | string | `pending_approval` \| `open` \| `approved` \| `released` \| `closed` |

**Response:** `InboundExceptionResponse[]` (newest first, not paginated).

---

### 3.4 Upload evidence (photo / PDF)

```
POST /api/v1/inbound/exceptions/{exception_id}/evidence
```

`multipart/form-data` with a single file field `file`.

**Constraints:** JPEG, PNG, WEBP, or PDF; max **10 MB**.

**Response:** the updated `InboundExceptionResponse` (with the new evidence entry).

---

### 3.5 Final disposition (manager decision)

```
POST /api/v1/inbound/exceptions/{exception_id}/disposition
```

**Request:** `InboundExceptionDispositionRequest`

```json
{
  "action": "return_to_sender",
  "note": "Supplier agreed to take back damaged carton.",
  "item_id": null
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `action` | ✅ | See table below |
| `note` | ➖ | Free text (max 2000) |
| `item_id` | ⚠️ | Required for `release_to_receiving` only if the SKU was just created/corrected |

**Actions:**

| `action` | Result |
|----------|--------|
| `release_to_receiving` | Stock moves to `RECEIVING-STAGE`, condition → `GOOD`, put-away triggered, status → `released` |
| `move_to_hold` | Stock moves to `HOLD` bin, status → `approved` |
| `move_to_quarantine` | Stock moves to `QUARANTINE` bin, status → `approved` |
| `return_to_sender` | Stock removed from hold, exception → `closed`, line flagged `rejected` |
| `dispose` | Stock removed from hold, exception → `closed`, line flagged `rejected` |

**Response:** updated `InboundExceptionResponse`.

---

### 3.6 Receiving-slip line detail (rejected / exception items)

```
GET /api/v1/inbound/receiving-slips/{slip_id}
```

The slip response now includes per-line detail so the UI can show *why* a line is
rejected or held. Items are nested under `groups[].items`.

Relevant per-item fields:

```json
{
  "id": "…",
  "name": "Acme Widget",
  "serial_number": "SN-1001",
  "sku": "ACME-WIDGET",
  "batch_number": "B-2026-08",
  "quantity": 24,
  "box_count": 1,
  "flag": "damaged",
  "condition_code": "QUARANTINE",
  "exception_status": "pending_approval",
  "exception_destination_location_id": "…",
  "rejection_reason": "Carton crushed on left side",
  "reason_code": "DAMAGED",
  "notes": "…"
}
```

| Field | Meaning |
|-------|---------|
| `name` | Catalog item name (resolved from `sku`/`item_code`/`gtin`) |
| `serial_number` | QSeal serial / QR identifier of the unit |
| `flag` | `ok` \| `short` \| `damaged` \| `excess` \| `hold` \| `quarantine` \| `rejected` |
| `condition_code` | `GOOD` \| `DAMAGED` \| `HOLD` \| `QUARANTINE` \| `REJECTED` |
| `rejection_reason` | Human text for a rejected line |
| `reason_code` | Exception reason code (linked `InboundException`) |

---

## 4. Response models

### `InboundExceptionResponse`

```json
{
  "id": "…",
  "warehouse_id": "…",
  "slip_id": "…",
  "slip_item_id": "…",
  "exception_type": "damaged",
  "reason_code": "DAMAGED",
  "status": "pending_approval",
  "condition_code": "QUARANTINE",
  "destination": "QUARANTINE",
  "destination_location_id": "…",
  "qr_identifier": "SN-1001",
  "serial_number": "SN-1001",
  "sku": "ACME-WIDGET",
  "item_name": "Acme Widget",
  "batch_number": "B-2026-08",
  "quantity": 24,
  "note": "Carton crushed on left side, photos attached.",
  "disposition": null,
  "disposition_note": null,
  "created_at": "2026-09-01T10:00:00+00:00",
  "approved_at": null,
  "disposed_at": null,
  "evidence": [
    {
      "id": "…",
      "filename": "crushed-carton.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 102400
    }
  ]
}
```

---

## 5. TypeScript interfaces

```ts
export type InboundExceptionClassification =
  | "short"
  | "damaged"
  | "excess"
  | "hold"
  | "quarantine";

export type InboundExceptionDestination = "HOLD" | "QUARANTINE";

export type InboundExceptionStatus =
  | "pending_approval"
  | "open"
  | "approved"
  | "released"
  | "closed";

export type InboundDispositionAction =
  | "release_to_receiving"
  | "move_to_hold"
  | "move_to_quarantine"
  | "return_to_sender"
  | "dispose";

export interface InboundExceptionReason {
  code: string;
  name: string;
  category: string;
  default_destination: InboundExceptionDestination | null;
  requires_approval: boolean;
}

export interface InboundEvidence {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
}

export interface InboundException {
  id: string;
  warehouse_id: string;
  slip_id: string | null;
  slip_item_id: string | null;
  exception_type: InboundExceptionClassification;
  reason_code: string;
  status: InboundExceptionStatus;
  condition_code: "GOOD" | "DAMAGED" | "HOLD" | "QUARANTINE" | "REJECTED";
  destination: InboundExceptionDestination | null;
  destination_location_id: string | null;
  qr_identifier: string | null;
  serial_number: string | null;
  sku: string | null;
  item_name: string | null;
  batch_number: string | null;
  quantity: number;
  note: string | null;
  disposition: InboundDispositionAction | null;
  disposition_note: string | null;
  created_at: string | null;
  approved_at: string | null;
  disposed_at: string | null;
  evidence: InboundEvidence[];
}

export interface ReceivingSlipItem {
  id: string;
  name: string | null;
  serial_number: string | null;
  sku: string;
  batch_number: string | null;
  manufacturing_date: string | null;
  expiry_date: string | null;
  quantity: number;
  box_count: number;
  flag: "ok" | "short" | "damaged" | "excess" | "hold" | "quarantine" | "rejected";
  condition_code: string | null;
  exception_status: string | null;
  exception_destination_location_id: string | null;
  rejection_reason: string | null;
  reason_code: string | null;
  notes: string | null;
}
```

---

## 6. Recommended UI flow

```mermaid
flowchart TD
    A[Receiving slip in pending_review] --> B{Line looks OK?}
    B -- Yes --> C[Approve slip → put-away]
    B -- No --> D[POST /items/{id}/exception]
    D --> E[Exception status: pending_approval]
    E --> F{Needs evidence?}
    F -- Yes --> G[POST /exceptions/{id}/evidence]
    F -- No --> H[Manager reviews queue]
    G --> H
    H --> I[POST /exceptions/{id}/disposition]
    I --> J{Action}
    J -- release_to_receiving --> K[Goods → receiving stage → put-away]
    J -- move_to_hold / move_to_quarantine --> L[Goods stay segregated]
    J -- return_to_sender --> M[Goods removed, closed]
    J -- dispose --> M
```

### Screen-by-screen guidance

1. **Receiving slip detail** — render `groups[].items`; badge non-`ok` flags and show
   `name`, `serial_number`, `rejection_reason`/`reason_code`.
2. **Classify dialog** — load reason codes (3.1); prefill `destination` from the
   reason's `default_destination`; disable submit until a valid code is chosen.
3. **Exception queue page** — list from 3.3 with `warehouse_id`, `destination`, and
   `status` filters; show item name, SKU, serial, qty, reason, status chip, and
   evidence thumbnails.
4. **Evidence** — allow adding photos/PDF before disposition (max 10 MB).
5. **Disposition modal (manager only)** — present the 5 actions; require a note for
   `return_to_sender` and `dispose`; after success, re-fetch the queue.

### Status chip mapping

| `status` | Chip color | Disposition allowed? |
|----------|------------|----------------------|
| `pending_approval` | Amber | ✅ |
| `open` | Amber | ✅ |
| `approved` | Blue | ✅ (re-route or finalize) |
| `released` | Green | ❌ |
| `closed` | Gray | ❌ |

---

## 7. Error handling

- **409 / state errors** — the backend returns a state machine error when an action
  is invalid for the current status (e.g. disposing an already-resolved exception,
  or classifying a slip that is no longer `pending_review`). Show the message and
  refresh the list.
- **422 validation** — `classification`, `destination`, or `reason_code` is invalid.
- **403** — user lacks the `inbound_exception.dispose` permission or is not the
  warehouse manager for that warehouse.
- **404** — slip, line, or exception not found (likely stale navigation).
