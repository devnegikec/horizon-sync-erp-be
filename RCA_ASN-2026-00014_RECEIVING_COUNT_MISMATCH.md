# RCA — ASN-2026-00014 shows 30 units instead of 31

**Reported by:** warehouse ops
**Environment:** BW-staging (org `0cc01d20-6f0f-4266-8042-86d1b73b998a`)
**Investigated:** 2026-10-01
**Status:** Root cause identified and verified against the staging database.
**Data changes made during this investigation: NONE.** (read-only queries only)

---

## 1. The question

> ASN-2026-00014 originally had 40 items. In the receiving scan I rejected one
> box of 8 items and one individual item (visible on slip RS-2026-00009 /
> put-away list PA-2026-00006). Receiving list, put-away list and stock entry
> all show **30**, but I only rejected 9, so it should be **31**.

The expected number is correct: the **first** receiving attempt did produce
**31 good units**. The 30 is a second, different problem.

---

## 2. Short answer

**One further unit (`PHF-Q5G8NR`) was blocked from the second scan session as a
`duplicate_serial` and silently dropped.**

It was blocked because the **earlier, rejected** receiving slip
(`RS-2026-00008`) had already created a `bin_stock_levels` row for it while it
was marked damaged/HOLD — and **rejecting a receiving slip does not reverse the
stock it created.** The stale HOLD row then made the duplicate-identity guard
refuse the re-scan.

So the arithmetic is right, the input was wrong:

```
40 expected
- 1 blocked as duplicate_serial  ← the bug
= 39 actually scanned
- 8 rejected
- 1 damaged / HOLD
= 30 good  → receiving slip, put-away list, stock entry all correctly show 30
```

The user's arithmetic assumed 40 scans. Only **39** ever entered the session
(`scan_sessions.total_boxes_scanned = 39`, `scan_session_items = 39`).

---

## 3. Timeline (UTC, 2026-10-01)

| Time | Event |
|---|---|
| 11:45:12 | Scan session `f788375e-5a62-4623-9c9a-a1012f05631d` opened — **asn_order_id `9e0857a7…` (a different ASN)**, warehouse Bommasandra `36393a71…` |
| 11:53:43 | `PHF-Q5G8NR` scanned in that session |
| 11:54:25 | Slip **RS-2026-00008** generated: `total_items = 40`, lines **31 ok / 8 rejected / 1 damaged** ← exactly the 31 the user expects |
| 11:54:26 | `damaged` exception raised for `PHF-Q5G8NR`; **`bin_stock_levels` row created: `inventory_status = hold`, qty 1, location `HOLD`** |
| 11:56:28 | Slip **RS-2026-00008 rejected** (`rejection_reason = "wrong"`) — **its stock rows are NOT reversed** |
| 11:58:21 | New scan session `00eda013-e7b3-4add-aa4a-e797877d6e6b` opened for the **correct** ASN `3f3ca134…` (ASN-2026-00014), warehouse Delhi `7ed521b8…` |
| 11:58:30.660 | Operator re-scans `PHF-Q5G8NR` → system raises **`duplicate_serial`** (`pending_approval`, destination HOLD) and **does not record the scan** |
| 11:59:08 | Session closed with `total_boxes_scanned = 39` |
| 11:59:08 | Slip **RS-2026-00009** generated from 39 units → **30 ok / 8 rejected / 1 damaged** |
| 11:59:09 | 2nd damaged unit `PHF-BKM4A2` → HOLD stock |
| — | `delivered_qty = 30`; put-away `PA-2026-00006` = 30; stock = 30 |

---

## 4. Root cause

### 4.1 Primary defect — rejecting a receiving slip does not reverse its stock

`InboundService.reject_slip()`
(`core-service/app/services/inbound_service.py:2453`) only:

1. validates the slip is `pending_review`,
2. calls `slip_repo.update_rejection_reason(...)`,
3. calls `tracking_service.reject_items(...)`.

It **never reverses `bin_stock_levels`**. But HOLD/damaged units get a bin-stock
row created at **slip-generation** time (not at put-away time), so a slip that is
rejected after generation leaves that stock behind permanently.

Evidence — `PHF-Q5G8NR` is still sitting in stock today, created 11:54:26 by the
slip that was rejected at 11:56:28:

```
 batch_number | quantity_on_hand | inventory_status |          created_at           | location
--------------+------------------+------------------+-------------------------------+----------
 PHF-Q5G8NR   |            1.000 | hold             | 2026-10-01 11:54:26.403969+00 | HOLD
```

### 4.2 Secondary defect — the duplicate guard can't tell "rejected" stock from real stock

`ScannedItemTrackingService.find_active_stock()`
(`core-service/app/services/scanned_item_tracking_service.py:421`) returns a hit
for **any** `bin_stock_levels` row with `quantity_on_hand > 0` for that identity.
It does not consider whether the originating receipt is still valid.

`InboundService._reject_duplicate_active_stock()`
(`inbound_service.py:684`) then hard-stops the scan with
`DUPLICATE_SERIAL` and records a `pending_approval` exception.

So a *rejected* receipt permanently poisons the identity: the physical unit can
never be received again.

### 4.3 Contributing defect — the loss is silent

The blocked scan is a `StateError` (`DUPLICATE_SERIAL`) plus a queued
`inbound_exceptions` row. Nothing in the scan/close-session flow tells the
operator that a unit was dropped, so the session was closed believing all units
were captured. The `duplicate_serial` exception for `PHF-Q5G8NR` is still
`pending_approval`.

### 4.4 Contributing factor — one ASN was scanned under another

The first session was opened against a **different ASN** (`9e0857a7…`) at a
different warehouse, scanned units from ASN-2026-00014's cartons, and was then
rejected as "wrong". That is what created the poisoned identity in the first
place. Worth understanding operationally, but the numbers only went wrong
because of 4.1 + 4.2.

---

## 5. Evidence (all read-only)

### 5.1 The ASN line

```sql
SELECT a.asn_order_no, a.status, i.qty, i.delivered_qty, i.extra_data
FROM asn_order_items i JOIN asn_orders a ON a.id = i.asn_order_id
WHERE a.asn_order_no = 'ASN-2026-00014';
-- ASN-2026-00014 | partially_delivered | 40.000 | 30.000 | {"no_of_cases": 5, "items_per_master_pack": 8}
```

Item: `PPI-SKO-7` / `ITM-2026-00006`; base unit Each (×1), master pack of 8 (×8).
5 cartons × 8 = 40. ✔

### 5.2 Both slips

```sql
SELECT slip_number, status, total_boxes, total_items, rejection_reason, created_at
FROM receiving_slips WHERE slip_number IN ('RS-2026-00008','RS-2026-00009');
-- RS-2026-00008 | rejected | 5 | 40 | wrong   | 2026-10-01 11:54:25
-- RS-2026-00009 | putaway_in_progress | 5 | 30 | (null) | 2026-10-01 11:59:08
```

RS-2026-00008 line flags — this is the "31" the user remembers:

```
RS-2026-00008:  rejected  8 lines /  8 units
                damaged   1 line  /  1 unit
                ok       31 lines / 31 units      <-- expected result
```

RS-2026-00009 line flags:

```
RS-2026-00009:  rejected  8 lines /  8 units
                damaged   1 line  /  1 unit
                ok       30 lines / 30 units      <-- what shipped
```

### 5.3 The scanned-vs-cartons gap

Carton membership comes from QSeal (`qseal_parameters` → `qseal_tracks`):

| Carton (master pack) | Capacity | Scanned in session 2 | Not scanned |
|---|---|---|---|
| `QSL97D791B` (MP-BT-OCT-01--1) | 8 | 8 | — |
| `QSL41EBB06` (MP-BT-OCT-01--2) | 8 | 8 | — |
| `QSL33EF9C9` (MP-BT-OCT-01--3) | 8 | 8 | — |
| `QSL35F771A` (MP-BT-OCT-01--4) | 8 | **7** | **`PHF-Q5G8NR`** |
| `QSL6969AE9` (MP-BT-OCT-01--5) | 8 | 8 | — |

Disposition of the 39 scanned units (by carton):

```
QSL33EF9C9 | ok       | 8
QSL35F771A | ok       | 7
QSL41EBB06 | ok       | 7
QSL41EBB06 | damaged  | 1
QSL6969AE9 | rejected | 8      <-- "one box of 8"
QSL97D791B | ok       | 8
```

So the "box of 8" rejected = carton `QSL6969AE9`; the "one individual item" =
`PHF-BKM4A2` (damaged). 9 non-good, matching the report.

### 5.4 The smoking gun — two exceptions for the same serial

```sql
SELECT exception_type, status, qr_identifier, session_id, slip_id, created_at
FROM inbound_exceptions WHERE qr_identifier = 'PHF-Q5G8NR';
```

```
damaged          | pending_approval | PHF-Q5G8NR | f788375e… (session 1) | RS-2026-00008 (rejected) | 11:54:26
duplicate_serial | pending_approval | PHF-Q5G8NR | 00eda013… (session 2) | (null)                   | 11:58:30
```

The unit was **scanned** at 11:58:30 in session 2 — it was rejected by the
duplicate guard, not missed by the operator.

### 5.5 The leftover stock

```sql
SELECT batch_number, quantity_on_hand, inventory_status, created_at
FROM bin_stock_levels
WHERE item_id = '5831d93b-cc73-4d06-b95b-fb5f013d6cd7';
```

9 rows, including the phantom from the rejected slip:

```
PHF-8374RL | 1.000 | available | 11:51:45   ┐
PHF-ZB2ESA | 1.000 | available | 11:51:46   │ all created during session 1
PHF-ON5MVK | 1.000 | available | 11:51:48   │ (11:45–11:54), whose slip
PHF-E3P2B8 | 1.000 | available | 11:51:49   │ RS-2026-00008 was rejected
PHF-RZLIIT | 1.000 | available | 11:51:50   │ at 11:56:28
PHF-Y4IBL1 | 1.000 | available | 11:51:51   │
PHF-75WV4T | 1.000 | available | 11:51:52   ┘
PHF-Q5G8NR | 1.000 | hold      | 11:54:26   <-- the stale HOLD that blocked the re-scan
PHF-BKM4A2 | 1.000 | hold      | 11:59:09   <-- legitimate, from RS-2026-00009
```

> ⚠️ **To confirm before repairing:** the 7 `available` rows in `BN005` were
> created during session 1, whose slip was later rejected. If none of those
> serials were re-scanned and accepted afterwards, they are **orphaned stock from
> a rejected receipt** — the same defect, and it would mean stock is **overstated
> by up to 7** for this item. This was not verified (investigation stopped here).

---

## 6. Why each screen shows 30

All three read the same value, so they agree by construction:

| Screen | Source | Value |
|---|---|---|
| Receiving slip | `receiving_slips.total_items` | 30 |
| ASN delivered qty | `InboundService._sync_asn_delivered_qty` — `SUM(quantity) WHERE flag='ok'` | 30 |
| Put-away list | `put_away_list_items` generated from slip items with `flag='ok'` | 30 |
| Stock entry | created from accepted (`flag='ok'`) slip items | 30 |

`_sync_asn_delivered_qty` is correct — it deliberately excludes rejected and
HOLD items. The bug is upstream: the wrong number of units reached the slip.

---

## 7. Recommended fix

### 7.1 Primary — reverse stock when a slip is rejected (required)

In `InboundService.reject_slip()` (`inbound_service.py:2453`), reverse every
stock effect the slip created, mirroring what `remove_scans()`
(`inbound_service.py:~1624`) already does for scan removal:

- for each slip item with `stock_entered` tracking rows (or a
  `bin_stock_levels` row it owns), call
  `BinStockService.remove_stock(bin_id, item_id, quantity, org_id,
  batch_number, commit=False)`,
- clear `scanned_item_tracking.stock_entered` / `stock_location_id`,
- drop the `inbound_exceptions` rows tied to that slip (or move them to a
  `cancelled` status),
- fail loudly if any reversal fails, rather than leaving partial state,
- commit once at the end.

Consider also handling the same reversal for a **cancelled/abandoned session**
and for `reject_slip_item`.

### 7.2 Secondary — don't treat rejected-receipt stock as active (defence in depth)

`ScannedItemTrackingService.find_active_stock()`
(`scanned_item_tracking_service.py:421`) should ignore `bin_stock_levels` rows
whose originating receipt is not valid — e.g. join through
`scanned_item_tracking.receiving_slip_id` and require the slip status to be one
of `pending_putaway | putaway_in_progress | putaway_complete` (the same set
`_sync_asn_delivered_qty` uses). That alone would have prevented this incident
even with the stock rows still present.

### 7.3 Observability — make a blocked scan loud (strongly recommended)

The operator had no idea a unit was dropped. Options:

- return the list of blocked serials in the **close-session** response and show
  it as a warning ("1 unit not recorded: already in stock"),
- surface pending `duplicate_serial` exceptions on the scan screen and/or block
  closing a session while unresolved exceptions exist,
- count them in the session summary.

### 7.4 Process — warn when scanning across ASNs

Session 1 was opened against a different ASN/warehouse and then rejected as
"wrong". Warn (or block) when a scanned serial belongs to another ASN's carton,
so the mistake surfaces immediately instead of after 40 scans.

---

## 8. Data repair — **not performed, needs an explicit decision**

Two separate questions:

**A. Unblock the missing unit.**
`PHF-Q5G8NR` cannot be received while the stale HOLD row exists. The minimal
repair is to remove that `bin_stock_levels` row (and resolve/close the
`duplicate_serial` exception), then receive the unit against ASN-2026-00014.

**B. Decide what RS-2026-00009 and the ASN should say.**
Either:

1. **Accept 30** and record the 1 blocked unit as a short receipt
   (`inbound_short_balances`), or
2. **Reverse RS-2026-00009**, repair the stale stock, and re-scan the full set so
   the receipt is clean — this is the only option that makes
   `delivered_qty = 31`.

Whichever is chosen, check the 7 `available` `BN005` rows (§5.5) first — if they
are orphaned, stock is overstated and a stock correction is also needed.

> I have not touched any row. Say the word and I'll prepare the SQL / API calls
> for whichever option you pick.

---

## 9. Verification checklist for the fix

1. Create a receiving slip for a shipment that includes a damaged unit → HOLD
   stock appears.
2. Reject that slip → assert the HOLD `bin_stock_levels` row is gone and
   tracking rows are cleared.
3. Re-scan the same unit in a new session → assert it is **accepted**, and that
   `duplicate_serial` is not raised.
4. Confirm `delivered_qty`, put-away list and stock all match the accepted count.
5. Regression: rejecting a slip whose units were already put away must also
   restore/reverse the bin stock (or refuse the rejection with a clear message).

---

## 10. Affected artefacts (staging)

| Entity | Id | Note |
|---|---|---|
| ASN | `ASN-2026-00014` / `3f3ca134-6134-48ab-9d51-b25eefc60ab1` | `partially_delivered`, 40 expected / 30 delivered |
| Receiving slip (rejected) | `RS-2026-00008` / `0f0bc524-5252-45ae-b60d-36300266d2c4` | 40 items, `rejected` |
| Receiving slip (live) | `RS-2026-00009` / `2c8874e7-7421-4249-945a-6aeb45bd24f0` | 39 items → 30 good |
| Session 1 | `f788375e-5a62-4623-9c9a-a1012f05631d` | other ASN `9e0857a7…` |
| Session 2 | `00eda013-e7b3-4add-aa4a-e797877d6e6b` | 39 scans |
| Put-away list | `PA-2026-00006` / `bc3d9ac0-8cae-4c39-b372-2651e438678a` | 30 units, pending |
| Blocked serial | `PHF-Q5G8NR` | carton `MP-BT-OCT-01--4` / `QSL35F771A` |
| Exception (blocking) | `3b5cd4d6-3adb-4e2d-8cda-8df8d317d96a` | `duplicate_serial`, `pending_approval`, session 2 |
| Exception (damaged, session 1) | `affa704e-66ea-445b-847b-590a43b73058` | `damaged`, `pending_approval`, tied to rejected slip RS-2026-00008 |
| Exception (damaged, session 2) | `334716e3-a4c2-4f55-b395-b7dd32970046` | `damaged` for `PHF-BKM4A2`, `pending_approval` |

---

## 11. Code references

| File | Line | Role |
|---|---|---|
| `core-service/app/services/inbound_service.py` | 2453 | `reject_slip()` — **missing stock reversal** |
| `core-service/app/services/inbound_service.py` | 684 | `_reject_duplicate_active_stock()` — hard-stops the scan |
| `core-service/app/services/scanned_item_tracking_service.py` | 421 | `find_active_stock()` — matches stale HOLD stock |
| `core-service/app/services/inbound_service.py` | 3445 | `_generate_receiving_slip()` — creates HOLD stock at generation time |
| `core-service/app/services/inbound_service.py` | ~1624 | `remove_scans()` — the reversal pattern to reuse |
| `core-service/app/services/inbound_service.py` | 2305 | `_sync_asn_delivered_qty()` — correct, excludes non-`ok` |
| `core-service/app/services/bin_stock_service.py` | 401 | `remove_stock()` |

---

*Prepared from staging DB reads only. No rows were inserted, updated or deleted.
One pre-existing TCP proxy was used for read access and left untouched.*
