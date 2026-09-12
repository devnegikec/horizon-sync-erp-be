# WMS Outbound End-to-End Flow — Packing Slips

> How an outbound order becomes a packing slip and gets dispatched, plus the
> 405 bug that was fixed on the `packing-slips` collection route.
>
> Related docs: `WMS_PICKLIST_OUTBOUND_EXPLAINED.md` (the picking journey),
> `WMS_PICKLIST_DELIVERY_PLAN.md`, `WMS_IMPLEMENTATION_PLAN.md`.

---

## 1. The 30-second version

After an outbound order is picked, the goods are **packed** into a *packing
slip* (an internal staging document) before they leave the warehouse. The
packing slip has its own lifecycle:

```text
draft ──▶ loading ──▶ dispatched   (+ cancelled)
```

- **Pack** creates a `draft` packing slip from a **completed** order.
- **Mark Loading** moves it to `loading` (goods staged onto the vehicle).
- **Dispatch** moves it to `dispatched`, decrements stock once, and advances
  the source pick lists to `in_transit`.

---

## 2. Status lifecycles

### Outbound order

```text
draft ──▶ confirmed ──▶ pending_picking ──▶ completed ──▶ (cancelled)
```

### Pick list (outbound-order-driven picking)

```text
draft ──▶ confirmed ──▶ pending_picking ──▶ in_progress
        ──▶ pick_complete ──▶ ready_for_dispatch ──▶ in_transit ──▶ delivered
```

> `completed` is kept as an alias of `pick_complete` for the legacy
> gate-verification flow.

### Packing slip

```text
draft ──▶ loading ──▶ dispatched   (+ cancelled)
```

---

## 3. Step-by-step happy path

| Step | Where (UI) | Action | Result |
|---|---|---|---|
| 1 | Orders tab | **Confirm** a `draft` order | order → `confirmed` |
| 2 | Orders tab | **Create Pick List** on a `confirmed` order | order → `pending_picking`; pick lists created |
| 3 | Pick Lists tab | Pick items (scan bin → item → qty) | pick list → `in_progress` → `pick_complete` |
| 4 | — | All pick lists finished | order → `completed` |
| 5 | Orders tab | **Pack** on the `completed` order | packing slip → `draft` |
| 6 | Packing Slips tab | **Mark Loading** | packing slip → `loading` |
| 7 | Packing Slips tab | **Dispatch** | packing slip → `dispatched`; pick lists → `in_transit` |
| 8 | (destination) | **Mark Delivered** on pick list | pick list → `delivered` |

### Key point — when can I pack?

The **Pack** button only appears when the **order** status is `completed`.
The backend enforces the same rule:

```python
# packing_slip_service.py — create_from_orders()
if order.status != OutboundOrderStatus.COMPLETED:
    raise ValidationError(
        f"Order '{order.order_no}' is not completed "
        f"(current status: '{order.status.value}')"
    )
```

So the sequence is **not**:

> ❌ pick-list completed → ready for dispatch → in transit → Pack

It is:

> ✅ order completed → **Pack** (draft) → Mark Loading → Dispatch

---

## 4. Two parallel flows (why it can look confusing)

The codebase has two overlapping outbound mechanisms:

### A. Pick-list-centric (legacy)

```
pick_complete ──▶ ready_for_dispatch ──▶ in_transit ──▶ delivered
                        │
                        └──▶ Gate Verification ──▶ Dispatch record
```

- `POST /outbound/{pick_list_id}/mark-ready|mark-in-transit|mark-delivered`
- Gate verification: `POST /outbound/gate-sessions` … `/{id}/verify`
- Dispatch from a verified gate session: `POST /outbound/dispatches`

### B. Packing-slip-centric (new end-to-end flow)

```
order completed ──▶ Pack ──▶ draft ──▶ Mark Loading ──▶ loading
                                              ──▶ Dispatch ──▶ dispatched
```

- Packing slip dispatch **automatically** moves its pick lists to
  `in_transit` (final stock decrement + transfer-serial propagation happen
  here).
- Gate verification is **not** a prerequisite for packing-slip dispatch — it
  remains the separate, optional gate-scan step in the legacy flow.

For the outbound end-to-end flow, use flow **B**.

---

## 5. API endpoints (`/outbound/packing-slips`)

| Method | Path | Purpose | Permission |
|---|---|---|---|
| `POST` | `/` | Create from completed order(s) | `PICK_LIST_CREATE` |
| `GET` | `/` | List packing slips | `PICK_LIST_READ` |
| `GET` | `/{slip_id}` | Detail | `PICK_LIST_READ` |
| `POST` | `/{slip_id}/mark-loading` | `draft` → `loading` | `PICK_LIST_UPDATE` |
| `POST` | `/{slip_id}/dispatch` | `loading` → `dispatched` | `PICK_LIST_UPDATE` |

Request/response schemas: `app/schemas/packing_slip.py`.

### Creation rules (`create_from_orders`)

- Every order must be in the **same warehouse**.
- Every order must be `completed`.
- An order may appear on only **one active (non-cancelled) packing slip**.
- A packing slip is created only if there is at least **one picked item**
  (`picked_qty > 0`) across the orders' pick lists.

---

## 6. The 405 bug (fixed)

### Symptom

```
POST /api/v1/outbound/packing-slips  →  405 Method Not Allowed
```

### Root cause

1. The `outbound` router (`/outbound`) declares a catch-all
   `GET /{pick_list_id}` route.
2. The `packing_slips` router (`/outbound/packing-slips`) was registered
   **after** `outbound`, and its collection route `POST /` resolves to
   `/outbound/packing-slips/` (trailing slash).
3. A `POST` to `/outbound/packing-slips` (no trailing slash) therefore:
   - matched `GET /{pick_list_id}` with `pick_list_id = "packing-slips"`
     → **partial match (method mismatch)**, and
   - did **not** exactly match `POST /outbound/packing-slips/` (trailing
     slash) → no full match.
4. Starlette returns **405** when only a partial match exists.

Verified against the running server:

```
POST /outbound/packing-slips   → 405
POST /outbound/packing-slips/  → 403 (route matched; 403 only because no token)
```

### Fix

1. **Frontend** (`apps/inventory/src/app/utility/api/wms.ts`): add the trailing
   slash to `createFromOrders` and `list` → `/outbound/packing-slips/`.
2. **Backend** (`app/api/v1/router.py`): register `packing_slips.router`
   **before** `outbound.router` so the literal `/outbound/packing-slips` path
   is never shadowed by the `/{pick_list_id}` catch-all.

---

## 7. Key files

| Layer | File |
|---|---|
| Model | `app/models/packing_slip.py` (`PackingSlip`, `PackingSlipItem`) |
| Enum | `app/models/base.py` (`PackingSlipStatus`, `OutboundOrderStatus`, `PickListStatus`) |
| Service | `app/services/packing_slip_service.py` |
| Endpoints | `app/api/v1/endpoints/packing_slips.py` |
| Router | `app/api/v1/router.py` |
| Schemas | `app/schemas/packing_slip.py` |
| Frontend list | `apps/inventory/src/app/components/wms/PackingSlipList.tsx` |
| Frontend pack button | `apps/inventory/src/app/components/wms/OutboundOrderList.tsx` |
| Frontend API | `apps/inventory/src/app/utility/api/wms.ts` |

### Service-method gotcha

`create_from_orders`, `mark_loading`, and `dispatch` **commit internally**. A
smoke test that calls them and then does `db.rollback()` will **not** undo
them — clean up by deleting rows and restoring statuses explicitly.

---

## 8. Pick bin suggestions & the wrong-bin config (manual mode)

### Manual pick lists have no assigned bin

When pick lists are generated in **manual** mode, the server deliberately
leaves `bin_location_id = NULL` on every line (see
`OutboundOrderService.create_pick_lists_from_order(..., mode='manual')`). The
worker assigns the real source bin while picking — the bin shown in the UI is
a **suggested** bin, not a reservation.

### Where the suggestion comes from

- Suggestions come from the smart location engine: `POST /wms-3d/suggest`
  with `task_type='pick'`.
- **Mobile (`BWmobile`)** fetches them: `PickScreen.tsx` →
  `pickService.suggestPickBins()`, and `PickItemsTable` renders
  `📍 Suggested: {bin}` for manual-mode lines.
- **Web (`apps/inventory`)** does **not** fetch pick suggestions:
  `PickListView.tsx` only renders `bin_location_path || bin_location_id`,
  which is empty in manual mode (shows `—`).

### Two layers of "wrong bin" protection

**Server-side hard stop** — `PickListService.validate_bin()`
(`app/services/pick_list_service.py`):

- If `pick.require_bin_scan` is `true` (default) **and** the line has an
  assigned bin, scanning a different bin raises
  `ValidationError("Wrong bin: …")`.
- If the line has **no** assigned bin (manual mode), the check is skipped —
  no hard stop.
- Setting `pick.require_bin_scan = false` disables bin validation entirely
  (legacy behaviour).

**Mobile client-side popup** — `PickScreen.tsx` `handleScan()` shows an
`Alert.alert('Wrong Bin', …)` when a scanned bin QR isn't on the list's bin
fields. This is client-side only and is **not** driven by any config flag.

### Config: allow scanning a different bin

| Setting | Key | Default | Effect |
|---|---|---|---|
| Require bin scan | `pick.require_bin_scan` | `true` | `false` = any bin accepted (no hard stop) |

Where to change it:

- **UI**: platform app → **Settings → Pick Settings** → turn off
  **"Require bin scan"**.
- **API**: `PUT /api/v1/pick-settings` with `{"require_bin_scan": false}`.

> Caveat: in manual mode the server check is already skipped, so a manual-mode
> worker's "Wrong Bin" warning is the mobile client-side alert, which has no
> config toggle today and would need a code change in `PickScreen.tsx` to
> suppress.
