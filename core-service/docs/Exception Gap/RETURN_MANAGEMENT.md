Searched for regex `= Column` (`**/core-service/app/models/scan_session.py`), 24 results

Now a behaviour harness for the new controls (rolled back, no side effects):

Created

Ran terminal command:  docker exec horizon_core python -m app._gap_check_256 2>&1 | tail -35

Ran terminal command:  docker exec horizon_postgres psql -U horizon_user -d railway -tAc "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='chk_session_type';" && docker exec horizon_postgres psql -U horizon_user -d railway -tAc "SELECT DISTINCT session_type FROM scan_sessions;"




```

```


Ran terminal command:  docker exec horizon_core python -m app._gap_check_256 2>&1 | tail -35




```

```


Ran terminal command:  docker exec horizon_core python -m app._gap_check_256 2>&1 | tail -30

All four controls verified. Let me clean up and update the backlog document to reflect the completed work:

Ran terminal command:  cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service && rm -f app/_gap_check_256.py && ls app/ | grep -c _gap_check || echo "harness removed"



The wide table made a bulk edit unreliable — let me make precise, small doc updates instead:




```

```


Ran terminal command:  cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be && docker exec horizon_postgres psql -U horizon_user -d railway -c "SELECT status, count(*) FROM serial_nos GROUP BY 1 ORDER BY 2 DESC LIMIT 12;" && docker exec horizon_postgres psql -U horizon_user -d railway -c "SELECT count(*) AS total, count(*) FILTER (WHERE batch_no IS NOT NULL) AS with_batch FROM serial_nos;"

`serial_nos` is empty here, so I'll make that check precise (only serials still owned by the warehouse) to avoid false rejections of returned/sold units:




```

```


Ran terminal command:  cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service && python3 -m py_compile app/services/scanned_item_tracking_service.py && ruff check app/services/inbound_service.py app/services/inbound_exception_service.py app/services/bin_stock_service.py app/services/scanned_item_tracking_service.py app/schemas/inbound.py app/api/v1/endpoints/inbound.py app/models/base.py alembic/versions/121_backfill_segregated_stock_status.py alembic/versions/122_inbound_exception_reason_codes.py alembic/versions/123_notification_inbound_exception.py 2>&1 | tail -3 && cd .. && git status --short && docker exec horizon_core python -m alembic current 2>&1 | tail -2

Let me re-verify the touched code path after that refinement:

Created

Ran terminal command:  docker exec horizon_core python -m app._gap_recheck 2>&1 | tail -15

Ran terminal command:  cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service && rm -f app/_gap_recheck.py && ls app/ | grep -c _gap || echo "recheck harness removed" && cd .. && git status --short

Completed: *E-05: inventory_status on segregated stock + backfill* (1/8)

Updated memory file

I've completed Phase 1 of the backlog (the P0 inbound gaps). Here's the state.

## Branch
`feature-inbound-exception-gaps` (created off `dev`, which now contains merged PR #256). Migrations applied locally: head is `123_notification_inbound_exception`.

## 3.2 Damaged stock

**E-05 (G-D1/G-D4) — held stock reported as `available`: fixed.** This was real in your live DB: 99 rows in HOLD/QUARANTINE bins were all `available`.
- `BinStockService.add_stock` / `transfer_stock` now accept `inventory_status`; `_get_or_create_bin_stock` applies it on create **and** re-statuses an existing row.
- `InboundExceptionService.DESTINATION_INVENTORY_STATUS`: `HOLD`→`hold`, `QUARANTINE`→`quality`, `DAMAGED`→`damaged`; wired into `classify_slip_item`, `_move_or_enter` and the scan-time HOLD path (tracking `receiving_status` follows the same map).
- Migration `121` backfills existing rows (**95 rows updated**; 4 zero-quantity rows intentionally skipped — nothing to mis-report).

**E-06 (G-D2) — damaged routed to its own bin.** `DESTINATIONS` is now `{HOLD, QUARANTINE, DAMAGED}`, the bin is provisioned on demand, and migration `122` points the seeded `DAMAGED` reason at `DAMAGED` instead of `QUARANTINE`. `flag_line_item` / `classify_slip_item` validate against the shared set with an actionable hint.

**E-07 (G-D3)** — photo-required rule: **not done** (P2, Phase 4).

## 3.3 Unreadable / unscannable QR

**E-08 (G-Q1) — fixed.** New `POST /inbound/exceptions/unreadable-qr` (permission `inbound_exception.create`) records a `QR_UNREADABLE` exception (destination HOLD, `pending_approval`) from a carton reference, **without decoding anything or creating stock**; repeat reports of the same carton in a session are rejected with `EXCEPTION_ALREADY_ACTIVE`.

**E-09 (G-Q2) — fixed for the dock controls.** `notify_supervisors()` alerts assigned warehouse users (best-effort, after the exception is committed, so alerting can never lose the exception); migration `123` adds the `inbound_exception` notification enum value via `autocommit_block`. Wired to unreadable QR, duplicate identity, excess and unexpected SKU. Verified: **11 notifications created** in the test org.

**E-10 (relabeling, L)** and **E-11 (controlled lookup)** — **not started**.

## 3.4 Other inbound exceptions

**E-13 (G-E3) — fixed.** `ScannedItemTrackingService.find_active_stock()` checks bin stock → serial master → tracking already put away, and `record_scan` hard-stops with **`409 DUPLICATE_SERIAL`**, recording the exception first and creating **no receipt line**. Internal-transfer ASNs are excluded (their serials legitimately exist in the source warehouse), and the previously dead `can_scan()` gate now has a caller. Index `ix_bin_stock_levels_org_batch` added for the lookup.

**E-12 (G-E1/G-E2) — fixed.** `record_scan` compares scanned **eaches** (raw × packaging conversion, matching `approve_slip`) against the ASN line expectation; on breach the over-receipt is held in HOLD with an `EXCESS` exception and the response gains `requires_decision`, `decision_options` (`move_to_hold` / `return_to_sender` / `dispose` — reusing the existing disposition actions rather than inventing vocabulary), `excess_qty`, `expected_qty`, `scanned_qty`.

**E-14 (aggregation, L)** — **not started**.

## 3.5 Returns — not started
I deliberately stopped here. The doc's own phasing makes Returns its own 3–4 week Phase 2, and cramming a partial module would give you unverified scaffolding. `R-01`/`R-02` (registration entity + reference lookup) are teed up as the next todo.

## Verification
- Migrations 121–123 applied to local Postgres; FK/enum/backfill/reason-seed all confirmed by SQL.
- Behaviour harness (in-container, transaction rolled back — zero side effects): segregation statuses, existing-row re-status, unreadable-QR + alerts + duplicate rejection, duplicate-identity hard stop with no receipt line, excess hold with `hold` status, and a within-expectation scan staying decision-free. Re-ran after the last code change.
- `ruff` on touched files: 9 findings, all confirmed pre-existing (checked `dispose` against `HEAD`).

## Judgement calls worth your review
1. **`serial_nos` check** — only serials with no customer/delivery date count as a duplicate, so returns of sold units aren't blocked. `serial_nos` is empty in your DB, so I couldn't validate the status vocabulary.
2. **Excess response** uses existing disposition actions instead of the doc's `REJECT_EXCESS` / `ACCEPT_TO_HOLD` vocabulary — that matches open question #7, and I did not seed unused codes.
3. **Excess semantics**: the scan is still recorded on the session (traceable, like `unexpected_known_sku`) while the units sit in HOLD pending disposition.
4. Removed a leftover `SCAN DEBUG` log that printed raw QR payloads on every scan.

Made changes.
