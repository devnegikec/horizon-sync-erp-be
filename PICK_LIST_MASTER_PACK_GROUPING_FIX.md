# Pick List Master-Pack Grouping Fix (QR-Serialized Items)

> Status: **Fixed**
> Service: `core-service` (WMS Outbound / Pick List Bin Resolution)
> Date: 2026-09-24
> Branch: `feature/BULK_PUTAWAY_API_PLAN`

---

## 1. Symptom

When generating a pick list from a confirmed order (auto bin resolution), QR-serialized
items that should be grouped as **one master carton per pick line** were instead split
into irregular fragments.

Example (`IPHONE-18`, order `ORD-2026-00024`, pick list `PL-2026-00051`):

| Batch | Expected | Actual |
|---|---|---|
| `BT-SEP-20-*` | 3 groups × 4 | 3 groups × 4 ✅ |
| `BT-SEP-24-MNF3-1` | 2 groups × 4 | **3 + 1 + 2 + 1 + 1** ❌ |

`IPHONE-17` showed the same pattern (`2 + 1 + 1` instead of `1 × 4`).

The bins suggested by the pick list were correct; only the master-carton grouping was
broken — serials from **five different cartons** were mixed into one order line.

---

## 2. Root Cause

1. **Serialization is detected by the wrong flag.**
   `IPHONE-18` / `IPHONE-17` are QR-serialized via `Item.qr_product_id`, but their legacy
   `has_serial_no` flag is `False`. `PickListService.resolve_bin_locations` only treated
   `has_serial_no == True` items as "serialized", so these items fell into the
   **batch-tracked** allocation path.

2. **QR-serialized items store one bin-stock row per unit.**
   Each unit serial is a separate `bin_stock_levels` row with `batch_number` = serial and
   `quantity_on_hand = 1`. The batch-tracked path assigned `serial_nos = [batch_number]`
   per row and, because `len(allocations) > 1`, **split every 4-unit master-pack line
   into four single-serial lines**.

3. **`created_at` order interleaves cartons.**
   Put-away stored the per-serial rows in scan order, not carton order, so the FIFO
   ordering used for allocation picked serials across cartons:

   ```
   04:29:00 ttk-7OK5QN -> QSL8407202  (pack 1)
   04:29:01 ttk-Q86WSI -> QSL27B39FE  (pack 2)
   04:29:01 ttk-Y2NHFF -> QSL4018D83  (pack 3)
   04:29:02 ttk-NN6IXD -> QSL4018D83  (pack 3)
   04:29:03 ttk-ANDXH6 -> QSL3A16AE1  (pack 4)
   04:29:04 ttk-A4FFTQ -> QSLCADC330  (pack 5)
   04:29:05 ttk-JCG9NK -> QSL8407202  (pack 1)
   04:29:05 ttk-YTU5MH -> QSL8407202  (pack 1)
   ...
   ```

   Eight serials spanning five cartons → groups `3, 1, 2, 1, 1`.

---

## 3. Fix

In `core-service/app/services/pick_list_service.py`:

1. Added a second serialization set in `resolve_bin_locations`:

   ```python
   qr_serialized_item_ids = {
       item_id
       for (item_id,) in self.db.query(Item.id)
       .filter(
           Item.id.in_([it.item_id for it in pick_list.items]),
           Item.qr_product_id.isnot(None),
       )
       .all()
   }
   ```

   The legacy `serialized_item_ids` (`has_serial_no == True`, scan-time capture) is
   left unchanged.

2. Added `_resolve_qr_serialized_item()`, which:

   - Resolves each available serial → QSeal parent via
     `QSealParameters.serial_number → parent_id`.
   - Groups available bin-stock rows by `(bin_location_id, parent_id)`.
   - Orders groups FEFO/FIFO **at the parent level** (earliest expiry first, then
     earliest arrival among the carton's rows).
   - Allocates **whole cartons** to the pick line, keeping a master-pack line intact
     (partial remainder lines take only what they need from one carton).
   - Pre-assigns the carton's unit serials onto `PickListItem.serial_nos` at generation.

   Master-pack lines are no longer split into per-serial lines, and serials stay within
   one carton.

---

## 4. Behavior Changes

- **Before:** QR-serialized master-pack lines were split into N single-unit lines, and
  serials were allocated by raw per-serial FIFO (mixing cartons).
- **After:** each master-pack line keeps its full quantity and carries the serials of
  exactly one QSeal carton. `picked_qty` still starts at `0`; serials are pre-assigned
  for display/grouping and scan validation.
- Non-QR items (`has_serial_no=True` legacy serials and batch-tracked items) are
  **unaffected**.

---

## 5. Verification

Simulated the new allocation against live data for `IPHONE-18` (20 units = 5 cartons):

```
line 1: QSLFFD1622 ×4   (BT-SEP-20-ZD0A-1)
line 2: QSLAC030BC ×4   (BT-SEP-20-ZD0A-1)
line 3: QSL848ACF2 ×4   (BT-SEP-20-ZD0A-1)
line 4: QSL8407202 ×4   (BT-SEP-24-MNF3-1)
line 5: QSL27B39FE ×4   (BT-SEP-24-MNF3-1)
```

- `python -m py_compile app/services/pick_list_service.py` → OK
- Module import + attribute check → OK
- No lint/type errors reported.

---

## 6. Files Changed

- `core-service/app/services/pick_list_service.py`
  - `resolve_bin_locations`: added `qr_serialized_item_ids` + routing to the new path.
  - `_resolve_qr_serialized_item` (new): carton-grouped serial allocation.

---

## 7. Rollout Notes

- Existing pick lists generated **before** this fix still contain the old broken lines.
  Cancel the affected pick list (releases reserved stock) and regenerate it from the
  order to get correct master-pack grouping.
- No database migration is required.
