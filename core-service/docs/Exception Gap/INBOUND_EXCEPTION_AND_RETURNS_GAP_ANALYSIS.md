# Inbound Exception Handling & Returns — Gap Analysis and Remaining Tasks

**Date:** 2026-09-18
**Scope:** core-service (`app/services`, `app/api/v1`, `app/models`, `alembic/versions`)
**Requirement source:** Blue requirement — _Inbound Exception Handling & Returns Management_
(sections 1 Short Receipts / Damaged Stock, 2 Unreadable QR, 3 Other Inbound Exceptions,
4 Returns Process & Return Slip Generation)

Status legend

| Symbol | Meaning                                                              |
| ------ | -------------------------------------------------------------------- |
| ✅     | Implemented and exposed through an API                               |
| ⚠️     | Partially implemented — works but is missing part of the requirement |
| ❌     | Not implemented                                                      |

---

## 1. Executive summary

| #   | Requirement                                                                                             | Status | Bottom line                                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| 1a  | Short receipt: post only actual, keep ASN expected, traceable balance                                   | ✅     | Balances, formal closure/write-off and arrival history implemented (`119_add_shortage_tracking`)                  |
| 1b  | Shortage **reason code** captured by the operator                                                       | ✅     | Reason code + short quantity persisted on the receipt line and carried onto the balance; the silent drop is fixed |
| 1c  | Supervisor approves Draft Receipt Note with shortage highlighted                                        | ✅     | `approve_slip` / `reject_slip` on the slip, and `assert_manager` on dispositions                                  |
| 1d  | Damaged never becomes `Available`; Hold/Quarantine segregation                                          | ⚠️     | Segregation works, but the stock keeps `inventory_status='available'` and damaged is routed to QUARANTINE only    |
| 1e  | Put-away excludes damaged stock and routes to segregated locations                                      | ✅     | Non-pickable system bins + slip-line flag filter                                                                  |
| 2a  | Unknown/uncommissioned QR → hard stop, no stock created                                                 | ✅     | Exception recorded, scan rejected                                                                                 |
| 2b  | No operator manual identity creation                                                                    | ✅     | Scan flow never mints identities                                                                                  |
| 2c  | Controlled supervisor **relabeling workflow**                                                           | ❌     | Nothing exists                                                                                                    |
| 2d  | Record "unreadable / unscannable QR" + alert supervisor                                                 | ❌     | No exception type, no supervisor task                                                                             |
| 3a  | Excess receipt (scanned > expected) → Hold + Accept-to-Hold / Reject-Excess                             | ⚠️     | Slip-level reconciliation only; **no scan-time over-receipt check**; dispositions can express the outcome         |
| 3b  | Unexpected SKU (valid SKU, not on ASN) → Hold + supervisor decision                                     | ✅     | `unexpected_known_sku` + HOLD + disposition                                                                       |
| 3c  | Duplicate serial scans → hard stop (session **and active stock**)                                       | ⚠️     | Session-scoped only; **no active-stock check**; `can_scan()` gate is dead code                                    |
| 3d  | Aggregation mismatch (parent/child dispute) → stop MC, isolate child identities                         | ❌     | No inbound parent/child validation                                                                                |
| 4   | Returns process end-to-end (register → scan → classify → draft note → approve → put-away → return slip) | ❌     | **No returns module at all**                                                                                      |

> **§3.1 (short receipts) is complete** as of 2026-09-18 — see
> `SHORT_RECEIPT_FRONTEND_INTEGRATION.md` for the API contract and error catalogue.

**Headline:** the inbound _exception_ half of the requirement is ~70 % built and solid — reason-coded
exceptions, hold/quarantine segregation, non-pickable system bins, put-away exclusion, manager
dispositions and short balances all exist. The _returns_ half (section 4) and the
_relabeling / aggregation-mismatch_ controls are greenfield.

---

## 2. What already exists (verified in code)

### 2.1 Exception engine

| Piece                                                                                                       | Location                                                                                                                  |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `inbound_exceptions`, `inbound_exception_reasons`, `inbound_exception_events`, `inbound_exception_evidence` | `app/models/inbound_exception.py`                                                                                         |
| Lifecycle service: create / classify / dispose / bulk dispose / evidence                                    | `app/services/inbound_exception_service.py`                                                                               |
| Classifications                                                                                             | `short`, `damaged`, `excess`, `hold`, `quarantine`                                                                        |
| Destinations                                                                                                | `HOLD`, `QUARANTINE` (non-pickable system bins)                                                                           |
| Final dispositions                                                                                          | `release_to_receiving`, `move_to_hold`, `move_to_quarantine`, `return_to_sender`, `dispose`                               |
| Manager gate                                                                                                | `InboundExceptionService.assert_manager()` (`warehouse.manage`, org/system admin, or `WarehouseUser.role == manager`)     |
| Seeded reason codes                                                                                         | `SHORT_PHYSICAL`, `DAMAGED`, `EXCESS`, `UNEXPECTED_KNOWN_SKU`, `UNKNOWN_IDENTITY`, `HOLD`, `QUARANTINE` (migration `078`) |
| System bins provisioned per warehouse                                                                       | HOLD + QUARANTINE bins; `ScannedItemTrackingService._get_or_create_system_bin()`                                          |
| Permissions                                                                                                 | `inbound_exception.read` / `.create` / `.dispose` (`app/core/authorization.py`)                                           |

### 2.2 Existing endpoints (all under `/api/v1/inbound`)

| Method | Path                                                     | Purpose                                                                            |
| ------ | -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `POST` | `/sessions/{id}/scans`                                   | Record scan (duplicate-session + ASN identity hard stop)                           |
| `POST` | `/sessions/{id}/end`                                     | Close session → generate receiving slip; accepts `rejections[]` and `exceptions[]` |
| `GET`  | `/receiving-slips`, `/receiving-slips/{id}`              | Draft receipt note + grouped detail                                                |
| `POST` | `/receiving-slips/{id}/approve` \| `/reject`             | Supervisor approval / rejection                                                    |
| `POST` | `/receiving-slips/{id}/items/{item_id}/flag`             | Flag line `short` \| `damaged`                                                     |
| `POST` | `/receiving-slips/{id}/items/{item_id}/reject`           | Reject a line                                                                      |
| `GET`  | `/exception-reasons`                                     | Tenant-configurable reason codes                                                   |
| `POST` | `/exceptions/classify`                                   | Classify a slip line (reason code + destination)                                   |
| `GET`  | `/exceptions`                                            | Exception / hold / quarantine queue                                                |
| `POST` | `/exceptions/{id}/evidence`                              | Damage photo / document upload                                                     |
| `POST` | `/exceptions/{id}/disposition`                           | Single disposition                                                                 |
| `POST` | `/exceptions/bulk-disposition`                           | Bulk disposition (≤ 200)                                                           |
| `GET`  | `/short-balances`                                        | ASN short balances                                                                 |
| `GET`  | `/floating-items`, `POST` `/floating-items/{id}/resolve` | Unknown/unlinked scans                                                             |
| `GET`  | `/bin-stock/.../parents`                                 | Box-level bin view (post-put-away)                                                 |

Related: `GET /api/v1/asn-orders/{id}/receiving-summary` (expected vs received, mismatch buckets),
`app/services/asn_reconciliation.py` (accepted/short/excess/damaged/hold/rejected),
`app/services/inbound_short_balance_service.py`, put-away exclusion in
`PutAwayService._build_put_away_specs()`.

### 2.3 Reusable building blocks for the gaps

- `DocumentNumberingService` + `DOCUMENT_TYPES` / `DEFAULT_PREFIXES` (`app/models/document_numbering.py`) → add a `return_receipt` series.
- `BinStockService.add_stock/transfer_stock/remove_stock`, `BinCapacityService.refresh_bin` (physical movement + non-pickable segregation).
- `ScanSession` / `ScannedItemTracking` dual-axis state machine (`receiving_status`, `putaway_status`, `stock_entered`) — the returns scan flow can reuse this shape.
- `PutAwayService.generate_from_slip*` + `enqueue_released_slip_item()` — put-away generation for approved good stock.
- `InboundExceptionService` dispositions — returns condition routing (Good/Damaged/Hold/Quarantine) maps 1:1 onto existing dispositions.
- System bins, `WarehouseLocationType.{HOLD, QUARANTINE, DAMAGED, EXCESS, RECEIVING}`.
- `evidence` storage (`storage_service.store_inbound_exception_evidence`).

---

## 3. Gaps in detail

### 3.1 Short receipts — ✅ COMPLETE (2026-09-18)

All four gaps below were fixed by migration `119_add_shortage_tracking` and the service/endpoint
changes described in `SHORT_RECEIPT_FRONTEND_INTEGRATION.md`. Kept here for the record.

| ID       | Gap                                                                                                                                                                                                                       | Evidence                                        |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **G-S1** | ~~**No shortage closure / write-off.**~~ **Fixed:** `POST /inbound/short-balances/{id}/close` records a reason code, approver and timestamp, and `written_off` is terminal.                                               | `inbound_short_balance_service.close_balance()` |
| **G-S2** | ~~**No arrival-level traceability.**~~ **Fixed:** append-only `inbound_short_balance_events` records every create/update/resolve/write-off with the receipt that caused it.                                               | `GET /inbound/short-balances/{id}/history`      |
| **G-S3** | ~~**Line-flag API drops the reason code.**~~ **Fixed:** `flag_line_item` accepts all five flags, validates the reason code against its category, persists it on the line and creates the exception for segregation flags. | `inbound_service.flag_line_item()`              |
| **G-S4** | ~~**No operator-confirmed quantity + shortage reason in one action.**~~ **Fixed:** `FlagLineItemRequest.short_qty` is required for `short` and validated against the outstanding ASN quantity.                            | `inbound_service._outstanding_asn_qty()`        |
| **G-S5** | `short` classification carries no default destination (`SHORT_PHYSICAL` → `None`) — unchanged and intentional: nothing is physically received for a short, so no bin is involved.                                         | migration `078` seed rows                       |

### 3.2 Damaged stock

> **Status 2026-09-19:** **G-D1 and G-D2 fixed** (E-05, E-06, branch
> `feature-inbound-exception-gaps`, migrations `121`/`122`). Segregated stock is
> now written with `inventory_status = hold | quality | damaged` (95 live rows
> backfilled) and damaged goods get their own non-pickable `DAMAGED` bin instead
> of defaulting to QUARANTINE. **G-D3** (mandatory damage reason/evidence at flag
> time) remains open as E-07; **G-D4** is resolved by the same status write.

| ID       | Gap                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Evidence                                                                                    |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **G-D1** | **Segregated stock keeps `inventory_status='available'`.** `classify_slip_item()` and `create_scan_exception()` add stock to the HOLD/QUARANTINE bin without setting a status; `BinStockService.add_stock()` has no status parameter, so the row defaults to `available`. Allocation is still blocked by `is_pickable=false`, but status-based reporting, analytics and any status-driven filter will mis-report damaged/held stock as available. **Confirmed in the live database:** `HOLD` bin = 72 stock rows / 83 units, all with `inventory_status='available'`; `QUARANTINE` = 1 row, also `available`. | `bin_stock_service.py` `add_stock`/`_get_or_create_bin_stock`; `bin_stock_level.py` default |
| **G-D2** | **No DAMAGED-destination route.** `DESTINATIONS = {HOLD, QUARANTINE}`. `WarehouseLocationType.DAMAGED` exists but is never provisioned or used; damaged goods default to QUARANTINE, so "Damaged / Hold / Quarantine" segregation collapses to two bins.                                                                                                                                                                                                                                                                                                                                                      | `inbound_exception_service.py:29`                                                           |
| **G-D3** | **No mandatory damage reason/evidence at flag time.** `FlagLineItemRequest.reason_code` is optional and ignored (G-S3); evidence upload is a separate manual call after the exception exists.                                                                                                                                                                                                                                                                                                                                                                                                                 | as above                                                                                    |
| **G-D4** | Condition code is stored per exception and mirrored on the slip line, but **not propagated to `bin_stock_levels`** (no `inventory_status`/condition column update), reinforcing G-D1.                                                                                                                                                                                                                                                                                                                                                                                                                         | `inbound_exception_service.py`                                                              |

### 3.3 Unreadable / unscannable QR

> **Status 2026-09-19:** **G-Q1 fixed** — `POST /inbound/exceptions/unreadable-qr`
> records a `QR_UNREADABLE` exception (destination HOLD, `pending_approval`) from a
> carton reference without decoding anything or creating stock. **G-Q2 fixed for
> this path** — the warehouse supervisors are alerted (in-app notification).
> **G-Q3** (relabeling workflow, E-10) and **G-Q4** (controlled lookup, E-11) remain open.

| ID       | Gap                                                                                                                                                                                               | Evidence                                           |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **G-Q1** | **No "unreadable / unscannable QR" exception.** No `QR_UNREADABLE` reason code, no exception type, and no operator action to set the carton aside and record it.                                  | reason-code seed list (migration `078`)            |
| **G-Q2** | **No supervisor alert/task.** No notification or task is raised when an operator reports an unreadable code (`NotificationService` exists but is not wired to this case).                         | —                                                  |
| **G-Q3** | **No relabeling workflow.** No request/approval entity, no reprint path, no label PDF re-issue for a damaged label. Only QSeal parent label _download_ exists (`GET /qseal/parents/{id}/labels`). | `qseal.py:433`                                     |
| **G-Q4** | **No controlled supervisor lookup** by carton label / batch / serial-prefix to resolve an unreadable carton (partial primitive only: `GET /asn-orders/{id}/serials`).                             | `asn_orders.py:114`                                |
| ✅       | Unknown/uncommissioned identity already hard-stops **and** records the exception, and no stock is created.                                                                                        | `inbound_service.record_scan` (`unknown_identity`) |

### 3.4 Other inbound exceptions

> **Status 2026-09-19:** **G-E1 and G-E2 fixed** — `record_scan` now compares the
> scanned eaches against the ASN line expectation, holds the over-receipt in HOLD
> with an `EXCESS` exception and returns `requires_decision` plus the disposition
> options (`move_to_hold`, `return_to_sender`, `dispose`). **G-E3 fixed** — a
> duplicate identity already in active stock is a hard stop (`409
> DUPLICATE_SERIAL`), recorded for the supervisor and never counted as a receipt
> line. **G-E4** (MC ↔ IC aggregation validation, E-14) remains open.

| ID       | Gap                                                                                                                                                                                                                                                                                                                                                                | Evidence                                                                |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| **G-E1** | **No scan-time excess check.** Nothing compares scanned quantity against the ASN line quantity, so "scanned > expected" is only discovered later in the slip-level reconciliation (`asn_reconciliation`). The extra units are therefore not auto-held at the dock.                                                                                                 | `inbound_service.record_scan` ASN validation checks SKU membership only |
| **G-E2** | **No explicit Accept-to-Hold / Reject-Excess decision vocabulary.** The outcomes can be expressed with existing dispositions (`move_to_hold`, `return_to_sender`, `dispose`) but the reason code/`requires_approval` flag for e.g. `REJECT_EXCESS` is missing from the seed, and quantity is not compared to the expectation anywhere.                             | migration `078` seed                                                    |
| **G-E3** | **Duplicate serial check is session-scoped only.** `record_scan` rejects a repeat within the same session; it does not check whether that QR already sits in **active stock** (`bin_stock_levels` / `serial_nos` / prior tracking). `ScannedItemTrackingService.can_scan()` exists but has **no callers** (dead gate).                                             | `inbound_service.py:~297`, `scanned_item_tracking_service.py:23`        |
| **G-E4** | **No parent/child (MC↔IC) aggregation validation at receipt.** A master carton whose children are missing, unexpected or duplicated relative to WMS records is not detected or stopped; there is no "isolate child identities for Stock Controller investigation" state or queue. (QSeal aggregation log exists but is a reporting view, not an inbound control.) | `qseal_service.list_aggregation()`, no inbound caller                   |

### 3.4.1 Live queue observation (local restore of production, 2026-09-18)

```
inbound_exceptions by status/destination
  pending_approval | HOLD       | 85
  approved         | HOLD       |  3
  pending_approval | QUARANTINE |  1
  closed           |            |  3
```

The exception queue is **already carrying 86 items awaiting supervisor approval**, which makes the
missing pagination/filters (`X-04`) and bulk-review UX a practical (not theoretical) concern.

### 3.5 Returns (section 4) — entirely missing

Searched for `return_slip`, `return_receipt`, `sales_return`, `customer_return`, `credit_note`, `RMA`
across `core-service/app/**` and the API router: **no matches**. There is no returns router in
`app/api/v1/router.py`.

Missing end-to-end:

| Step                                                                                                                                                 | Status                                                                                 |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Return **registration** against Invoice / Dealer / Warehouse reference (+ expected SKUs, qty, serials)                                               | ❌                                                                                     |
| Arrival + **HC scan receiving** session for returns, validated against the registration                                                              | ❌                                                                                     |
| **Condition classification** per returned unit (Good / Damaged / Hold / Quarantine)                                                                  | ❌ (inbound classification is not reusable as-is: it is bound to a receiving slip/ASN) |
| **Draft Return Receipt Note** auto-compiled from scans + conditions + reference reconciliation                                                       | ❌                                                                                     |
| **Returns Supervisor approval** of note lines                                                                                                        | ❌                                                                                     |
| **Good stock → put-away tasks**, available only after put-away confirmed                                                                             | ❌                                                                                     |
| **Damaged/Hold/Quarantine → segregated restricted locations**, blocked from allocation                                                               | ❌ (bins + transfer primitives exist)                                                  |
| **Return slip document** (expected vs received per line, serials, conditions, reason codes, approver, immutable audit timestamps) + numbering series | ❌                                                                                     |
| Returns **put-away generation**                                                                                                                      | ❌                                                                                     |

---

## 4. Remaining tasks (backlog)

Priority: **P0** = required for the blue requirement, **P1** = controls/quality, **P2** = reporting/polish.
Sizes: S (≤1 day), M (2–4 days), L (1–2 weeks).

### 4.1 Returns module (largest piece — section 4)

> **Progress 2026-09-20** (branch `feature-inbound-exception-gaps`, core migration
> `124_returns_module`, identity migration `022`): **R-01, R-02, R-03, R-04, R-05, R-06,
> R-07, R-10 done.** All 18 web + handheld endpoints answer and were verified end-to-end
> on both warehouses (Mother `8bc22a62`, Ecity `f0099ec7`) — registration → session → scan
> → classify → note → approval → put-away, including the 409/404 guards. Still open:
> **R-08** CSV/PDF export (JSON slip is live), **R-09** explicit note→exception link (the
> exceptions are created at classification today), **X-03** note audit events (written, but
> not yet surfaced), **X-04** pagination on the exception queue.
> Implementation notes and the four deliberate deviations from the v1.0 contract are in
> `RETURNS_WEB_APP_INTEGRATION.md` §14. See `RETURNS_API_AUDIT_2026-09-20.md` for the
> pre-build state.

| ID       | Task                                                    | APIs to build                                                                                                                                                                                                                                       | Data / migration                                                                                                                                                  | Pri    | Size |
| -------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---- |
| **R-01** | Return registration entity + lifecycle                  | `POST /api/v1/returns/registrations`<br>`GET /returns/registrations` (filters: status, dealer, invoice, warehouse)<br>`GET /returns/registrations/{id}`<br>`POST /returns/registrations/{id}/cancel`                                                | `return_registrations`, `return_registration_items` (+ optional serial lines). Reuse `DocumentNumberingService` with new type `return_registration` (prefix `RR`) | **P0** | M    |
| **R-02** | Reference reconciliation (Invoice / Dealer / Warehouse) | `GET /returns/references?invoice_no=` / `?dealer_id=` (lookup + validation source)                                                                                                                                                                  | read-model over `invoices`, `customers`, `warehouses`                                                                                                             | **P0** | S    |
| **R-03** | Return receiving session (HC)                           | `POST /returns/registrations/{id}/sessions`<br>`GET /returns/sessions/{id}`<br>`POST /returns/sessions/{id}/scans` (validate identity against registration; duplicate hard stop)<br>`POST /returns/sessions/{id}/end`                               | `return_sessions`, `return_session_items` **or** extend `scan_sessions` with `session_type='return'` + `return_registration_id`                                   | **P0** | M    |
| **R-04** | Condition classification per returned unit              | `POST /returns/sessions/{id}/classify` (`good` \| `damaged` \| `hold` \| `quarantine` + `reason_code` + note)<br>`POST /returns/sessions/{id}/classify/bulk`                                                                                        | reuse `inbound_exception_reasons` (add `return_*` categories) + per-item condition column                                                                         | **P0** | M    |
| **R-05** | Draft Return Receipt Note generation                    | `POST /returns/sessions/{id}/finalize` → draft note<br>`GET /returns/receipt-notes`<br>`GET /returns/receipt-notes/{id}` (grouped: parent_qseal / product_name / items, same shape as receiving slips)                                              | `return_receipt_notes`, `return_receipt_note_items`; numbering `return_receipt` (prefix `RRN`)                                                                    | **P0** | M    |
| **R-06** | Supervisor approval & disposition                       | `POST /returns/receipt-notes/{id}/approve`<br>`POST /returns/receipt-notes/{id}/reject`<br>`POST /returns/receipt-notes/{id}/disposition` (per line: `release_to_stock` \| `move_to_hold` \| `move_to_quarantine` \| `scrap` \| `return_to_dealer`) | reuse `assert_manager()` for the supervisor gate + `return_receipt_note_events` audit                                                                             | **P0** | M    |
| **R-07** | Put-away / segregation on approval                      | `POST /returns/receipt-notes/{id}/generate-put-away`<br>(good lines → put-away tasks; others → HOLD/QUARANTINE transfer)                                                                                                                            | reuse `PutAwayService` + `BinStockService.transfer_stock`; mark stock available **only** after put-away confirm                                                   | **P0** | M    |
| **R-08** | Return slip document                                    | `GET /returns/receipt-notes/{id}/slip` (+ PDF/CSV export)                                                                                                                                                                                           | expected vs received, serials, conditions, reason codes, approver, immutable timestamps                                                                           | **P1** | S    |
| **R-09** | Returns exception hook-up                               | reuse `POST /returns/receipt-notes/{id}/exceptions` → `inbound_exceptions` (type `return_*`)                                                                                                                                                        | link `InboundException.return_receipt_note_id`                                                                                                                    | **P1** | S    |
| **R-10** | Permissions & roles                                     | `return.register`, `return.receive`, `return.classify`, `return.approve`, `return.dispose` in `authorization.py` + role seed                                                                                                                        | `identity`/role seed migration                                                                                                                                    | **P0** | S    |

### 4.2 Inbound exception gaps

> **Progress 2026-09-19** (branch `feature-inbound-exception-gaps`, migrations
> `121`–`123`): **E-05, E-06, E-08, E-12, E-13 done**; **E-09 done** for the dock
> controls (unreadable QR, duplicate identity, excess, unexpected SKU). Still open
> in this section: **E-10** (relabeling, L), **E-11** (controlled lookup, S),
> **E-14** (aggregation validation, L), **E-07** (photo rule, S).

| ID       | Task                                                                                                                 | APIs to build                                                                                                                                                                                                                                                                           | Data / migration                                                                                                              | Pri    | Size | Covers                                                                           |
| -------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------ | ---- | -------------------------------------------------------------------------------- |
| **E-01** | Shortage closure / write-off with approval                                                                           | `POST /inbound/short-balances/{id}/close` (reason_code, note, approver) <br>`GET /inbound/short-balances?status=open`                                                                                                                                                                   | add `closed_by/closed_at/close_reason/close_note` to `inbound_short_balances`; status enum `open/resolved/written_off/closed` | **P0** | M    | ✅ DONE (migration 119)                                                          |
| **E-02** | Arrival-level shortage history                                                                                       | `GET /inbound/short-balances/{id}/history` (per receipt/arrival)                                                                                                                                                                                                                        | new `inbound_short_balance_events` (append-only)                                                                              | **P1** | S    | ✅ DONE (migration 119)                                                          |
| **E-03** | Fix line-flag contract: accept `excess/hold/quarantine`, persist `reason_code` + `destination`, create the exception | extend `POST /receiving-slips/{id}/items/{item_id}/flag` (no new path)                                                                                                                                                                                                                  | none (uses existing exception tables)                                                                                         | **P0** | S    | ✅ DONE (G-S3, G-D3)                                                             |
| **E-04** | Shortage capture with explicit quantities                                                                            | extend `FlagLineItemRequest` / `EndSessionException` / `InboundExceptionClassifyRequest` with `received_qty` + `short_qty` (validated against line qty); store on the exception (`metadata_json` → promoted columns)                                                                    | optional `short_qty`/`received_qty` columns on `inbound_exceptions`                                                           | **P1** | S    | ✅ DONE for receipt lines (`reason_code`, `short_qty`); ASN-side closure in E-01 |
| **E-05** | Set `inventory_status` when segregating stock                                                                        | extend `BinStockService.add_stock/transfer_stock` with `inventory_status`; set `hold`/`quarantine`/`damaged` in `classify_slip_item`, `create_scan_exception`, `dispose`, `_move_or_enter`                                                                                              | none (column exists); backfill migration for existing held rows                                                               | **P0** | S    | G-D1, G-D4                                                                       |
| **E-06** | DAMAGED destination + bin provisioning                                                                               | allow `DAMAGED` in `DESTINATIONS`; provision the bin in the system-bin helper; route `damaged` there by default                                                                                                                                                                         | data migration to add DAMAGED bins per warehouse                                                                              | **P1** | S    | G-D2                                                                             |
| **E-07** | Photo-required rule for damage                                                                                       | enforce evidence presence before approving a `damaged` classification (config flag)                                                                                                                                                                                                     | config in `inbound.*` settings                                                                                                | **P2** | S    | G-D3                                                                             |
| **E-08** | Unreadable / unscannable QR exception                                                                                | `POST /inbound/exceptions/unreadable-qr` (session, carton ref, note) → `QR_UNREADABLE` reason code, destination HOLD, `pending_approval`; supervisor alert                                                                                                                              | seed reason `QR_UNREADABLE`                                                                                                   | **P0** | S    | G-Q1                                                                             |
| **E-09** | Supervisor notification/task on exception                                                                            | hook `NotificationService` + worker task creation on: unreadable QR, unknown identity, excess, aggregation mismatch                                                                                                                                                                     | none                                                                                                                          | **P1** | S    | G-Q2                                                                             |
| **E-10** | Relabeling workflow                                                                                                  | `POST /inbound/relabel-requests` (source exception, reason, actor)<br>`POST /inbound/relabel-requests/{id}/approve` (supervisor/stock controller)<br>`POST /inbound/relabel-requests/{id}/apply` (new QR/serial binding)<br>`GET /inbound/relabel-requests/{id}/labels` (label payload) | `relabel_requests`, `relabel_request_events`; permission `inventory.relabel`                                                  | **P1** | L    | G-Q3                                                                             |
| **E-11** | Supervisor controlled lookup                                                                                         | `GET /inbound/lookup?serial= \| batch= \| carton= \| asn=` (authorized roles only)                                                                                                                                                                                                      | none (query over ASN serials, tracking, qseal)                                                                                | **P1** | S    | G-Q4                                                                             |
| **E-12** | Scan-time excess detection                                                                                           | in `record_scan`: if scanned qty for the ASN line exceeds expected → create `excess_receipt` exception, segregate to HOLD, return a decision-required response                                                                                                                          | seed reason `REJECT_EXCESS` / `ACCEPT_TO_HOLD`                                                                                | **P0** | M    | G-E1, G-E2                                                                       |
| **E-13** | Duplicate serial hard stop against active stock                                                                      | in `record_scan`: check `bin_stock_levels.batch_number`/`serial_nos`/prior `scanned_item_tracking` for the QR; on hit create `duplicate_serial` exception and reject; wire the existing `can_scan()` gate                                                                               | `DUPLICATE_SERIAL` reason code                                                                                                | **P0** | S    | G-E3                                                                             |
| **E-14** | MC ↔ IC aggregation validation                                                                                      | `POST /inbound/aggregation-verifications` (parent QR + observed children)<br>`GET /inbound/aggregation-disputes` (Stock Controller queue)<br>`POST /inbound/aggregation-disputes/{id}/resolve`                                                                                          | `inbound_aggregation_disputes` + child isolation flag on `scanned_item_tracking` (`investigation`)                            | **P1** | L    | G-E4                                                                             |

### 4.3 Cross-cutting

| ID       | Task                                                                                                                                                                        | Pri    | Size |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---- |
| **X-01** | Approval matrix: formalize who may approve what (inbound shortage closure, damaged disposition, returns note, relabel) — add `assert_manager` variants + role seed          | **P0** | S    |
| **X-02** | Permissions for new APIs (`return.*`, `inventory.relabel`, `inbound_exception.reopen`) + frontend matrix doc                                                                | **P0** | S    |
| **X-03** | Immutable audit for every state change (extend `inbound_exception_events` pattern to returns; verify `__audited__` coverage)                                                | **P1** | S    |
| **X-04** | Pagination/filters on the exception + returns queues (exception list currently returns everything)                                                                          | **P1** | S    |
| **X-05** | Mobile/HC contract updates (`MOBILE_APP_INBOUND_GUIDE.md`): unreadable-QR action, excess decision screen, return session flow                                               | **P1** | M    |
| **X-06** | UAT test cases for inbound + return exception scenarios (short, damaged, excess, unexpected SKU, duplicate, unknown, unreadable, aggregation mismatch, return good/damaged) | **P1** | M    |
| **X-07** | Metrics: exception rate by reason, shortage write-off value, return rate by reason, ageing of open exceptions                                                               | **P2** | M    |

---

## 5. Suggested phasing

**Phase 1 — close the inbound gaps (P0, ~2–3 weeks)**
`E-03`, `E-05`, `E-01`, `E-08`, `E-13`, `E-12` (+ `X-01`, `X-02`).
This makes section 1–3 of the requirement fully compliant for the paths that already exist, and fixes two real defects (`reason_code` silently dropped; held stock reported as `available`).

**Phase 2 — returns MVP (P0, ~3–4 weeks)**
`R-01` → `R-07` + `R-10` (+ `X-05` for the HC screens). Delivers the complete
Registration → Arrival → Scan → Classification → Draft Note → Approval → Put-Away/Segregation → Return Slip chain.

**Phase 3 — controls & quality (P1, ~2 weeks)**
`E-02`, `E-04`, `E-06`, `E-09`, `E-11`, `E-14`, `R-08`, `R-09`, `X-03`, `X-04`, `X-06`.

**Phase 4 — polish (P2)**
`E-07`, `X-07`.

---

## 6. Open questions for the business

1. **Shortage closure:** who may write off a residual shortage — Inbound Supervisor only, or does it need finance approval above a value threshold?
2. **Returns registration source:** is the reference always an existing WMS invoice, or may returns be registered against a free-text dealer/warehouse reference with no invoice?
3. **Return of serialized units:** must every returned unit be serial-verified (QR scan), or are non-serialized/bulk returns in scope for v1?
4. **Returns numbering:** confirm prefix/series (`RR` for registration, `RRN` for Return Receipt Note) and whether numbering is per-warehouse or per-organization.
5. **Relabeling:** is relabeling enabled by default and who authorizes it (Supervisor vs Stock Controller)? Does a relabeled unit keep its original identity history for traceability?
6. **Aggregation mismatch:** on a mismatch, should the whole carton be blocked, or only the disputed child identities (requirement says children are isolated — confirm the parent carton's fate)?
7. **Excess receipt:** is `Accept to Hold` allowed without increasing ASN expected quantities permanently (requirement says expected numbers are never silently altered) — i.e. is a one-off "accept to hold" note sufficient, or must it be reconciled into a separate document?
8. **Damaged bin:** do you want a dedicated `DAMAGED` bin physically separate from `QUARANTINE` (G-D2), or is QUARANTINE sufficient at your warehouses?

---

## 7. Appendix — quick reference

**Existing reason codes** (`inbound_exception_reasons`, migration `078`):
`SHORT_PHYSICAL`, `DAMAGED`, `EXCESS`, `UNEXPECTED_KNOWN_SKU`, `UNKNOWN_IDENTITY`, `HOLD`, `QUARANTINE`.

**Proposed new reason codes:** `QR_UNREADABLE`, `RELABEL_REQUIRED`, `DUPLICATE_SERIAL`,
`AGGREGATION_MISMATCH`, `REJECT_EXCESS`, `ACCEPT_TO_HOLD`, `RETURN_GOOD`, `RETURN_DAMAGED`,
`RETURN_SCRAP`, `SHORTAGE_WRITE_OFF`.

**Exception lifecycle (existing):** `open` / `pending_approval` → `approved` | `released` → `closed`.

**Slip lifecycle (existing):** `pending_review` → `pending_putaway` → `putaway_complete` (| `rejected`).

**Key files to touch**

- `core-service/app/models/inbound_exception.py`, `inbound_short_balance.py`, `bin_stock_level.py`
- `core-service/app/services/inbound_exception_service.py`, `inbound_service.py`, `bin_stock_service.py`, `scanned_item_tracking_service.py`, `put_away_service.py`
- `core-service/app/api/v1/endpoints/inbound.py`, `router.py`, `app/api/v1/schemas/inbound.py`
- `core-service/app/core/authorization.py`, `app/models/document_numbering.py`
- `core-service/alembic/versions/` (new migrations), `deploy_local_to_railway.sh` (deploy)
