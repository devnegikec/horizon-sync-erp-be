# WMS Picklist Execution — Requirements, Gap Analysis & Task List

> Status: **Gap analysis & implementation plan**
> Source: `WMS_Picklist_Execution_Requirements_Consumer_Appliances.xlsx` (4 sheets)
> Scope: `core-service` (backend) + `BWmobile` (handheld) + `horizon-sync/apps/inventory` (web)
> Date: 2026-08-22

---

## 1. Requirement inventory (from the workbook)

| Sheet | IDs | Count | Theme |
|---|---|---|---|
| `01_Workflow_Requirements` | WF-001 … WF-023 | 23 | Picklist creation & execution workflow |
| `02_Exceptions` | EX-001 … EX-022 | 22 | Reason-code-driven exception resolution |
| `05_Alerts_Warnings` | ALT-001 … ALT-012 | 12 | Alerts, warnings & hard stops |
| `09_NFR_Design_Guidelines` | NFR-001 … NFR-010 | 10 | Non-functional / engineering guidelines |

The workflow spans the full outbound lifecycle:

```
WF-001..007  Demand → Validate → ATP → Allocate → Pick strategy → Task → Prioritize
WF-008..010  Assign → Login → Accept
WF-011..018  Navigate → Bin validate → SKU validate → Serial validate → Qty → Inventory move → Multi-bin → HU
WF-019..020  Stage transfer → Stage validate
WF-021..023  Task complete → Status update (ERP) → Audit
```

---

## 2. Current implementation baseline

### 2.1 What already exists

**Models** (`core-service/app/models/`):
- `pick_list.py` — `PickList` (status DRAFT/IN_PROGRESS/COMPLETED/CANCELLED, `invoice_reference`, `invoice_data`, `assigned_to`, `dispatch_record_id`) + `PickListItem` (`item_id`, `qty`, `picked_qty`, `uom`, `per_case_qty`, `case_qty`, `loose_qty`, `batch_no`, `serial_nos` JSONB, `bin_location_id`, `sort_order`)
- `bin_stock_level.py` — `BinStockLevel` (`quantity_on_hand`, `batch_number`, `expiry_date`, `packaging_unit_id`) — **no inventory status (blocked/damaged/hold)**
- `dispatch_record.py`, `gate_verification.py` — gate + dispatch
- `qr_scan_event.py` — scan audit events
- `stock_movement.py`, `bin_reservation.py` — ledger + worker bin reservation
- `serial_no.py` — serial master (exists, not yet wired into pick validation)

**Services** (`core-service/app/services/`):
- `pick_list_service.py` — CRUD, `create_from_invoice`, `resolve_bin_locations` (FEFO→FIFO, multi-bin split, skips reserved bins), `record_pick_scan` (SKU match, over-pick block, bin stock decrement, status transition, scan event), `complete_pick_list`, `cancel_pick_list`
- `order_import_service.py` — SAP invoice + **PDF packing-slip import** (per-case qty / no-of-cases / case qty / loose qty / loose boxes / batch)
- `gate_verification_service.py`, `outbound_service.py`, `bin_reservation_service.py`, `routing_optimizer.py`, `location_suggestion_service.py` (3D suggest, `task_type='pick'`)

**Endpoints** (`outbound.py`, base router):
- `POST /from-invoice`, `POST /import`
- `GET /` (list, filters), `GET /{id}`
- `POST /{id}/assign`, `POST /{id}/scan`, `POST /{id}/complete`, `POST /{id}/cancel`
- `POST /gate-sessions`, `POST /gate-sessions/{id}/scan`, `GET /gate-sessions/{id}/progress`, `POST /gate-sessions/{id}/verify`
- `POST /dispatches`, `GET /dispatches`, `GET /dispatches/{id}`

**Web UI**: `PickListView.tsx`, `PickListManagement.tsx`, `PickListDetailDialog.tsx`, `AssignWorkerDialog`, status badges/stats, `CreateDeliveryFromPickListDialog`.

**Mobile (`BWmobile`)**: PickScreen is **deferred/disabled** — worker login (QR) works, but handheld pick execution is not yet wired.

### 2.2 Key structural gaps (one-liner)

1. **No inventory status** on `bin_stock_levels` → can't exclude blocked/damaged/hold/quality (WF-003, EX-007/010/011/013).
2. **No reason-code / exception model** → all 22 exception flows are unimplemented (no capture, no resolution, no approval).
3. **No alerts/exception queue** → ALT-001…012 largely absent.
4. **No staging lane concept** → WF-019/020, EX-019/020 missing.
5. **No handling-unit (HU) association** during pick (WF-018).
6. **No prioritization / wave / aging** fields (WF-007, ALT-011).
7. **No wrong-bin hard stop** in scan (WF-012, ALT-001).
8. **Serial validation is shallow** — grouping only; no available/blocked/consumed enforcement (WF-014, EX-005/006).
9. **No idempotency keys** on scan/confirm (NFR-003).
10. **No ERP sync queue/retry** (WF-022, ALT-009).

---

## 3. Gap analysis matrix

Legend: ✅ implemented · 🟡 partial · ❌ missing

### 3.1 Workflow requirements (WF-001 … WF-023)

| ID | Function | Status | Notes |
|---|---|---|---|
| WF-001 | Receive SAP SO/Delivery | 🟡 | `create_from_invoice` + `/import` exist; no duplicate/malformed rejection + interface log retention |
| WF-002 | Validate order eligibility (master data exists) | ❌ | No SKU/UoM/location-master existence check → exception hold |
| WF-003 | Check ATP (exclude blocked/damaged/hold/quality) | 🟡 | FEFO/FIFO resolution exists, but only filters `quantity_on_hand > 0` — no status exclusion; no configurable backorder/partial rule |
| WF-004 | Allocate / reserve inventory | 🟡 | Worker bin-reservation exists; no demand-level reservation + partial-allocation policy |
| WF-005 | Pick strategy (FIFO/FEFO, fixed-bin, bulk-break, zone, bin-priority) | 🟡 | FEFO/FIFO done; fixed-bin/zone/bulk-break/bin-priority not implemented |
| WF-006 | Create pick task/list | ✅ | `create_from_invoice`, `create`, task creation via `TaskService` |
| WF-007 | Prioritize (cutoff, wave, route, aging, manual) | ❌ | No priority field, no wave, no sequencing |
| WF-008 | Assign picker/team (zone, workload, role) | 🟡 | `assigned_to` + `/assign` + UI exist; no team/queue, no role/zone/workload validation |
| WF-009 | Handheld login (individual, lockout, timeout) | 🟡 | Worker QR login exists; lock-after-failures & session timeout not implemented |
| WF-010 | Task accept / record start time | 🟡 | Task exists; no explicit accept + start timestamp |
| WF-011 | Navigate to source (zone/aisle/rack/bin) | 🟡 | 3D suggest endpoint exists; guided step-by-step handheld nav deferred |
| WF-012 | Bin validation (scan source bin, wrong-bin hard stop) | ❌ | Scan accepts optional bin override; no wrong-bin hard stop |
| WF-013 | SKU/GTIN validation | ✅ | Wrong SKU hard stop, no picker bypass |
| WF-014 | Serial validation (belongs to SKU, available, not consumed) | 🟡 | Serial grouping + Mfg/Exp display only; no availability/consumed/blocked enforcement |
| WF-015 | Quantity confirmation (over-pick block, short-pick exception) | 🟡 | Over-pick blocked; short-pick exception flow missing |
| WF-016 | Inventory movement (status: available→picked→in-transit-to-stage) | 🟡 | Bin stock decremented + movement ledger; no status transitions; no idempotency guard |
| WF-017 | Multi-bin continuation | ✅ | Split-across-bins implemented |
| WF-018 | Handling unit (trolley/carton/pallet) | ❌ | No HU association during pick |
| WF-019 | Stage transfer (direct to staging lane) | ❌ | No staging lane concept |
| WF-020 | Stage validation (scan staging) | ❌ | Missing |
| WF-021 | Task completion (all lines/approved exceptions) | 🟡 | `complete_pick_list` exists; no approved-exception prerequisite |
| WF-022 | Status update / ERP sync (queue + retry) | 🟡 | Dispatch + invoice ref exist; no outbound message queue/retry/alert |
| WF-023 | Immutable audit (operator, device, scans, reasons, approvals) | 🟡 | `QRScanEvent` + audit log exist; no exception/approval/override audit |

### 3.2 Exceptions (EX-001 … EX-022)

All 22 are **❌ missing** at the reason-code/exception level (a few have hard-stop scan behaviour already). Grouped for action:

| Group | IDs | Current behaviour | Gap |
|---|---|---|---|
| Wrong location/SKU/serial (hard stops) | EX-003, EX-004, EX-005, EX-021, EX-022 | SKU & over-pick blocked in scan | No wrong-bin stop, no serial block, no reason capture |
| Stock quantity discrepancies | EX-001, EX-002, EX-010, EX-011, EX-012 | None | No discrepancy event, no alternate-source flow, no cycle-count handoff |
| Serial exceptions | EX-005, EX-006 | Grouping only | No unknown-serial investigation, no quarantine/correction |
| Damage / hold / barcode issues | EX-007, EX-008, EX-009, EX-013 | None | No damage/hold workflow, no relabel, no blocked-stock stop |
| Order change during pick | EX-014, EX-015, EX-016 | None | No cancellation/qty-change propagation to open tasks |
| Connectivity / recovery | EX-017 | None | No session resume / idempotent resume |
| Bin / staging issues | EX-018, EX-019, EX-020 | None | No inaccessible-bin, no staging unavailable |

### 3.3 Alerts & warnings (ALT-001 … ALT-012)

| ID | Severity | Status | Notes |
|---|---|---|---|
| ALT-001 Wrong source bin | Error | ❌ | No bin validation |
| ALT-002 Wrong SKU | Error | 🟡 | Error raised, but no modal/audible UX (mobile deferred) |
| ALT-003 Invalid/duplicate serial | Error | ❌ | |
| ALT-004 Short pick | Warning | ❌ | No exception queue |
| ALT-005 Damaged stock | Warning | ❌ | |
| ALT-006 Order cancelled while picking | Critical | ❌ | `cancel_pick_list` exists but no in-flight propagation |
| ALT-007 Inventory discrepancy | Warning | ❌ | |
| ALT-008 Staging unavailable | Warning | ❌ | |
| ALT-009 Integration failure | Warning | ❌ | No queue/retry |
| ALT-010 Task reassigned | Info | 🟡 | Assign endpoint exists; no notification |
| ALT-011 Task aging / SLA risk | Warning | ❌ | |
| ALT-012 Repeated scan mismatch | Warning | ❌ | |

### 3.4 NFR design guidelines (NFR-001 … NFR-010)

| ID | Area | Status | Notes |
|---|---|---|---|
| NFR-001 Performance ≤1s | — | ⚠️ | Not verified; needs load test |
| NFR-002 No sync ERP per scan | ✅ | Scan uses local WMS authority |
| NFR-003 Idempotency | ❌ | No dedup keys on scan/confirm |
| NFR-004 RBAC / no shared accounts | 🟡 | Roles exist; worker QR login individual |
| NFR-005 Auditability | 🟡 | No exception/override audit |
| NFR-006 Usability (scan-first) | ❌ | Mobile deferred |
| NFR-007 Server-side validation | 🟡 | Over-pick/SKU server-validated; bin/serial not |
| NFR-008 Configurability | ❌ | No pick-specific flags/settings (see §5) |
| NFR-009 Traceability (order→…→staging) | 🟡 | Order→allocation→scan exists; exception/approval/staging missing |
| NFR-010 Recovery (session resume) | ❌ | |

---

## 4. Task list

### Phase 0 — Foundation (enables most exception/NFR work)

| # | Task | Covers | Configurable? |
|---|---|---|---|
| T-01 | Add `inventory_status` (available/blocked/damaged/hold/quality) to `bin_stock_levels` + migration | WF-003, EX-007/010/011/013 | status enum is master config |
| T-02 | **Reason-code & exception framework**: `pick_exceptions` model (pick_list_item, reason_code, severity, reported_by, status, resolution, approver) + endpoints | All EX, ALT-004/005/007/008 | reason-code master configurable |
| T-03 | **Exception queue + supervisor dashboard** (web) | ALT-004/005/007/008/011/012 | queue filters |
| T-04 | Idempotency keys on `scan`/`complete`/`cancel` + server dedup | NFR-003, EX-017 | client header, always-on |
| T-05 | Audit trail for exceptions, approvals & overrides (immutable) | WF-023, NFR-005 | — |

### Phase 1 — Scan-time validation hardening

| # | Task | Covers | Configurable? |
|---|---|---|---|
| T-06 | Bin validation: wrong-bin hard stop (scan source bin first) | WF-012, ALT-001, EX-003 | `pick.require_bin_scan` flag |
| T-07 | Serial validation against `serial_no` (available/not consumed/not blocked) | WF-014, EX-005/006, ALT-003 | `pick.require_serial` flag (per-item `has_serial_no`) |
| T-08 | Short-pick + over-pick tolerance + damage/hold capture at scan | WF-015, EX-002/007/021, ALT-004/005 | `pick.over_pick_tolerance`, `pick.allow_short_pick` |
| T-09 | Inventory movement status transitions (available→picked→staged) + idempotent posting | WF-016 | status enum config |

### Phase 2 — Flow completion (staging, HU, priority, ERP)

| # | Task | Covers | Configurable? |
|---|---|---|---|
| T-10 | **Staging lane** model + stage transfer + stage validation (scan) | WF-019/020, EX-019/020, ALT-008 | `pick.require_stage_scan` flag |
| T-11 | Handling-unit (HU) association during pick | WF-018 | `pick.enable_handling_unit` flag |
| T-12 | Prioritization + task aging (priority, cutoff, wave, SLA) | WF-007, ALT-011 | `pick.aging_threshold`, priority config |
| T-13 | ERP status sync queue + retry + alert | WF-022, ALT-009 | retry config |
| T-14 | Task accept + start-time + login session controls (lockout/timeout) | WF-009/010 | `pick.login_lockout`, `pick.session_timeout` |

### Phase 3 — Handheld execution (mobile)

| # | Task | Covers | Configurable? |
|---|---|---|---|
| T-15 | **Mobile PickScreen**: task list → accept → guided nav → bin/SKU/serial/qty scan → exception → stage → complete/cancel | WF-008…023 (handheld) | all pick flags |
| T-16 | Mobile session resume + offline-safe resume | NFR-010, EX-017 | — |

### Phase 4 — Configurability & verification

| # | Task | Covers | Configurable? |
|---|---|---|---|
| T-17 | **Pick configuration layer** — settings + feature flags (see §5) | NFR-008 | core |
| T-18 | NFR verification: load test (≤1s), ERP outage sim, replay/negative tests, trace-one-shipment | NFR-001/002/003/007/009 | — |

---

## 5. Configurability plan (your focus point #4)

Use the existing `FeatureFlag` (tenant-scoped) + a `pick_settings` config table. Every rule below is toggle-able per organization, so Type-1 vs Type-2 customers can differ without code changes.

| Config key | Type | Default | Controls |
|---|---|---|---|
| `pick.allocation_strategy` | enum | `fefo_fifo` | FEFO/FIFO/fixed-bin/zone |
| `pick.require_bin_scan` | bool | `true` | WF-012 hard stop |
| `pick.require_sku_scan` | bool | `true` | WF-013 |
| `pick.require_serial` | bool | `per_item` | WF-014 (or global override) |
| `pick.over_pick_tolerance` | numeric | `0` | EX-021 tolerance |
| `pick.allow_short_pick` | bool | `true` | EX-002 / ALT-004 |
| `pick.short_pick_approval_threshold` | numeric | `0` | NFR-008 approval threshold |
| `pick.require_stage_scan` | bool | `false` | WF-020 |
| `pick.enable_handling_unit` | bool | `false` | WF-018 |
| `pick.aging_threshold_minutes` | int | `120` | ALT-011 |
| `pick.login_lockout_attempts` | int | `5` | WF-009 |
| `pick.session_timeout_minutes` | int | `30` | WF-009 |
| `pick.reason_codes` | list (master) | standard set | T-02 reason-code list |
| `pick.priority_fields` | list | `[]` | WF-007 (cutoff/wave/route) |
| `pick.backorder_rule` | enum | `partial` | WF-003/004 shortage rule |
| `pick.inventory_statuses_pickable` | list | `[available]` | WF-003 exclusion list |

> Pattern: config lives in one table, read once per pick session, enforced server-side (NFR-007 — never trust UI only).

---

## 6. Conflicts & questions needing your input

1. **Status naming — `DRAFT` vs `OPEN`/`RELEASED`.** Your model uses `DRAFT` as the scannable "open" state; the requirement doc speaks of `OPEN` and "Pick Released". Rename, or keep `DRAFT` and document the mapping?
2. **Inventory status on bin stock** (T-01). Adding `inventory_status` to `bin_stock_levels` is required for WF-003 / EX-007/010/011/013. Confirm the exact status set: `available, blocked, damaged, hold, quality`? Any `reserved` as a separate field (we already have `bin_reservation`)?
3. **Staging lanes** (T-10). This is a brand-new concept (no model today). Is staging **lane-level** (dock door/lane assignment) or just a destination location? Full scan-at-staging in scope, or defer?
4. **Handling units** (T-11). Do you need tote/carton/pallet association *during* pick now, or is the existing `item_packaging_units` enough for this phase?
5. **Serial enforcement** (T-07). Is serial capture **mandatory** (hard stop) for serialized items, or policy-based per item (`has_serial_no`)? This changes scan UX significantly.
6. **Mobile scope.** The requirements are heavily handheld-led, but `BWmobile` PickScreen is currently disabled. Is handheld execution in scope for this round, or web-first with mobile next phase?
7. **Prioritization / wave** (T-12). Do orders arrive with a dispatch cutoff/wave/route from SAP, or do we need manual priority only? Affects WF-007 data model.
8. **ERP (SAP) integration mode** — real-time sync or async queue? WF-001/022 and ALT-009 depend on this.
9. **Idempotency** (T-04). Are callers (mobile/web) able to send an idempotency key? If not, we derive one server-side from task+scan payload.
10. **EX-001 vs EX-002 overlap** — "bin empty" (zero found) vs "insufficient quantity" (some found, less than required). Confirm they should be distinct reason codes.
11. **Alerts delivery** — where do ALT recipients see them? In-app dashboard only, or also email/notification service (we have `communication.py`)?
12. **Damage photo/comment** (EX-007) — "optionally photo/comment if configured". In scope now or later?

---

## 7. Bottom line

- **Implemented well already:** demand→pick-list→FEFO/FIFO→route→scan→complete/cancel→gate→dispatch, plus case/loose/batch/serial display and PDF packing-slip import.
- **Biggest gaps:** (1) no inventory-status model, (2) no reason-code/exception framework, (3) no staging/HU/priority, (4) no idempotency, (5) no configurability layer.
- **Recommended order:** Phase 0 (T-01…T-05) first — the exception + status + idempotency foundation makes every other requirement clean to layer on. Then scan hardening (Phase 1), flow completion (Phase 2), mobile (Phase 3), and configurability + verification (Phase 4).
