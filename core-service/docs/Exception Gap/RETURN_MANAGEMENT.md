# Return Management — inbound exception gaps and the returns chain

Operational reference for the inbound-exception controls and the customer-returns chain that
`INBOUND_EXCEPTION_AND_RETURNS_GAP_ANALYSIS.md` tracks (`E-*` = exception controls, `R-*` =
returns, backlog item IDs referenced throughout this file).

Integration contracts live in:

- `RETURNS_WEB_APP_INTEGRATION.md` — back-office / web app API contract.
- `RETURNS_HANDHELD_INTEGRATION.md` — dock (handheld) API contract.

## Status

| Item                    | Control                                           | Status                                |
| ----------------------- | ------------------------------------------------- | ------------------------------------- |
| `E-05`                  | `inventory_status` on segregated stock + backfill | Done                                  |
| `E-06`                  | Damaged stock routed to its own bin               | Done                                  |
| `E-07`                  | Photo required for damaged lines                  | Not started (P2)                      |
| `E-08`                  | Unreadable / unscannable QR                       | Done                                  |
| `E-09`                  | Supervisor notification on dock exceptions        | Done (dock controls)                  |
| `E-10`                  | Reason-code relabeling                            | Not started                           |
| `E-11`                  | Controlled identity lookup                        | Not started                           |
| `E-12`                  | Scan-time excess detection                        | Done                                  |
| `E-13`                  | Duplicate-identity hard stop                      | Done                                  |
| `E-14`                  | Aggregation mismatch                              | Not started                           |
| `R-01` – `R-05`, `R-08` | Returns chain + Return Slip                       | Done (migration `124_returns_module`) |

## Damaged and held stock

### `E-05` — segregated stock was reported as `available`

Stock physically parked in a segregation bin (`HOLD`, `QUARANTINE`, `DAMAGED`) carried the column
default `available`, so status-based reporting counted damaged, held or quarantined units as
sellable even though the bin itself is non-pickable. This was observed in the live database: 99
rows in `HOLD`/`QUARANTINE` bins were all `available`.

- `BinStockService.add_stock` / `transfer_stock` accept `inventory_status`;
  `_get_or_create_bin_stock` applies it on create **and** re-statuses an existing row.
- `InboundExceptionService.DESTINATION_INVENTORY_STATUS` is the single source of the mapping —
  `HOLD` → `hold`, `QUARANTINE` → `quality`, `DAMAGED` → `damaged`. It is wired into
  `classify_slip_item`, `_move_or_enter` and the scan-time `HOLD` path; the tracking
  `receiving_status` follows the same map.
- Migration `121_backfill_segregated_stock_status` repairs rows created before the change
  (95 rows updated; 4 zero-quantity rows intentionally skipped — nothing to mis-report).

### `E-06` — damaged goods have their own bin

`DESTINATIONS` is `{HOLD, QUARANTINE, DAMAGED}` and the bin is provisioned on demand.
Migration `122_inbound_exception_reason_codes` points the seeded `DAMAGED` reason at `DAMAGED`
instead of collapsing into `QUARANTINE`. `flag_line_item` / `classify_slip_item` validate against
the shared set and return an actionable hint.

### `E-07` — photo required for damaged lines

Not implemented. P2, Phase 4.

## Unreadable / unscannable QR

### `E-08` — report an unreadable carton

`POST /inbound/exceptions/unreadable-qr` (permission `inbound_exception.create`) records a
`QR_UNREADABLE` exception — destination `HOLD`, status `pending_approval` — from a carton
reference, **without decoding anything or creating stock**. Repeat reports of the same carton in a
session are rejected with `EXCEPTION_ALREADY_ACTIVE`.

### `E-09` — supervisor notification

`notify_supervisors()` alerts the assigned warehouse users. It is best-effort and runs _after_ the
exception is committed, so alerting can never lose the exception. Migration
`123_notification_inbound_exception` adds the `inbound_exception` notification enum value via
`autocommit_block`. Wired to unreadable QR, duplicate identity, excess and unexpected SKU.

### `E-10` / `E-11`

Not started — reason-code relabeling and controlled identity lookup.

## Other inbound exceptions

### `E-13` — duplicate identity hard stop

`ScannedItemTrackingService.find_active_stock()` checks bin stock → serial master → tracking
already put away. `record_scan` then hard-stops with `409 DUPLICATE_SERIAL`, recording the
exception first and creating **no receipt line**.

Internal-transfer ASNs are excluded, because their serials legitimately exist in the source
warehouse. The previously dead `can_scan()` gate now has a caller. Index
`ix_bin_stock_levels_org_batch` supports the lookup.

### `E-12` — scan-time excess detection

`record_scan` compares scanned **eaches** (raw quantity × packaging conversion, matching
`approve_slip`) against the ASN line expectation. On breach the over-receipt is held in `HOLD`
with an `EXCESS` exception, and the response gains `requires_decision`, `decision_options`
(`move_to_hold` / `return_to_sender` / `dispose`), `excess_qty`, `expected_qty` and `scanned_qty`.

### `E-14`

Not started — aggregation mismatch.

## Returns chain

Registration → arrival → scan → classification → draft note, plus the Return Slip document, are
implemented by migration `124_returns_module` and `app/services/return_service.py`. API contracts
and the UI rules are in the two `RETURNS_*` integration documents.

Reason codes are tenant-configurable and seeded by migration `124`: `RETURN_GOOD`,
`RETURN_DAMAGED`, `RETURN_SCRAP`. The UI filters the picker server-side via
`GET /inbound/exception-reasons?condition=<condition>`; it must not hard-code a category map.

## Verification

- Migrations `121`–`124` applied to local Postgres; FK, enum, backfill and reason-seed all
  confirmed with SQL.
- Behaviour harness (in-container, transaction rolled back — zero side effects) covering:
  segregation statuses, existing-row re-status, unreadable QR + alerts + duplicate rejection,
  duplicate-identity hard stop with no receipt line, excess hold with `hold` status, and a
  within-expectation scan staying decision-free.

## Decisions and known limitations

1. **`serial_nos` duplicate check** — only serials with no customer/delivery date count as a
   duplicate, so returns of sold units are not blocked. `serial_nos` is empty in the local
   database, so the status vocabulary could not be validated against real data.
2. **Excess response vocabulary** — the response reuses the existing disposition actions instead
   of the gap-analysis `REJECT_EXCESS` / `ACCEPT_TO_HOLD` vocabulary, matching open question #7.
   No unused reason codes were seeded.
3. **Excess semantics** — the scan is still recorded on the session (traceable, like
   `unexpected_known_sku`) while the units sit in `HOLD` pending disposition.
4. **Over-receipt on a return** — `return_session_items.over_receipt` is recorded and returned to
   the client but does not gate note approval. Whether receiving more than expected should block
   approval or only warn is **open question Q7** in `RETURNS_WEB_APP_INTEGRATION.md` §12.
5. Removed a leftover `SCAN DEBUG` log that printed raw QR payloads on every scan.
