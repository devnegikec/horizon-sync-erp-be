# WMS Packing Slip — Parent/Child (Master Pack) Inheritance

> How a packing slip keeps the parent-carton → child-serial relationship of
> QR-serialized master packs, and why it is **inherited from the pick list**
> rather than re-assembled or randomized at packing time.
>
> Related docs: `WMS_PACKING_SLIP_OUTBOUND_FLOW.md`,
> `WMS_PICKLIST_OUTBOUND_EXPLAINED.md`,
> `PACKAGING_UNIT_CONVERSION_FACTOR_VS_ITEMS_PER_MASTER_PACK.md`,
> `parent_child_qr_code.md`.

---

## 1. The 30-second version

A packing slip does **not** re-pack units. It **inherits** the exact child
serials that were already resolved and grouped on the pick list, then
**reconstructs** the parent/child view at read time from QSeal data.

```text
Inbound (QSeal master pack)
   └─▶ Put-away (same parent/child groups)
          └─▶ Pick list (child serials copied to PickListItem.serial_nos)
                 └─▶ Packing slip (child serials copied verbatim)
                        └─▶ Response (parent/child re-resolved from QSeal)
```

No random unit selection happens at any stage — the parent carton and its
children were fixed when the master pack was created at inbound.

---

## 2. The core rule

**The packing service copies `serial_nos` from the pick-list line. It never
computes or regenerates them.**

Both creation paths do this:

### `create_from_orders` (order-driven packing)

```python
self.db.add(
    PackingSlipItem(
        ...
        item_id        = pli.item_id,
        qty            = picked,
        per_case_qty   = pli.per_case_qty,
        case_qty       = pli.case_qty,
        loose_qty      = pli.loose_qty,
        batch_no       = pli.batch_no,
        serial_nos     = pli.serial_nos,      # ← inherited verbatim
        bin_location_id= pli.bin_location_id,
        handling_unit_id = pli.handling_unit_id,
    )
)
```

### `pack_pick_lists` (pick-list-driven packing)

```python
PackingSlipItem(
    ...
    serial_nos = pli.serial_nos,              # ← inherited verbatim
    ...
)
```

Every `PackingSlipItem` field that describes *what* was picked comes straight
off the source `PickListItem`. The packing service only adds staging metadata
(slip number, order/pick-list references, sort order).

---

## 3. Parent/child is reconstructed at read time

The parent/child structure is **not stored** on the packing slip. It is
rebuilt on the fly in `_to_response` from the inherited child serials plus
QSeal metadata:

### Step 1 — `_qseal_context`

Collects **every** serial/batch marker across the slip lines and resolves the
ones that are QSeal child serials:

```python
serials = {s for item in slip.items for s in (item.serial_nos or []) if s}

# QSealParameters lookup → param_by_serial (serial → parent_id, batch, dates)
# QSealTrack lookup      → track_by_id    (parent id → master-carton track)
```

Batch markers stored in `serial_nos` (for batch-tracked lines) simply won't
match any `QSealParameters` row, so they fall through harmlessly.

### Step 2 — `_build_groups`

For each line it decides serialized vs batch, then:

- **Serialized line** → finds the parent track via `param.parent_id`, attaches
  `parent_qseal` (with `capacity` = items-per-master-pack), and emits one
  child entry per inherited serial.
- **Batch line** → emits a single entry with the full (possibly fractional)
  `qty` and no `parent_qseal`.

Result: the response group looks like the receiving-slip / put-away view —
`parent_qseal` on top, `items[]` listing each child serial underneath.

---

## 4. The legacy-flag bug (fixed)

`Item.has_serial_no` is a **legacy WMS flag** that can be `False` even for
items that are QR-serialized (`qr_product_id` set). For example `IPH-17` and
`IPH-18` are serialized but `has_serial_no=False`.

The packing service used to gate serialization on that flag:

```python
# Before (wrong) — QR-serialized items treated as batch
if info.has_serial_no:
    ... parent/child grouping ...
```

This caused master packs on packing slips to be emitted as standalone "batch"
groups with no `parent_qseal` — the **same bug** that previously affected
pick-list grouping (`outbound.py`) and put-away grouping (`put_away.py`).

### The fix

`is_serialized` is now true when **either**:

1. the legacy `has_serial_no` flag is set, **or**
2. any of the line's `serial_nos` resolves to a `QSealParameters` row.

```python
is_serialized = bool(info is not None and info.has_serial_no) or any(
    s in param_by_serial for s in child_serials
)
```

`_qseal_context` likewise collects **all** `serial_nos` without the
`has_serial_no` gate — QSeal child serials resolve, batch markers don't.

This mirrors the already-verified fixes in:

| Service | File | What |
|---|---|---|
| Pick-list grouping | `app/api/v1/endpoints/outbound.py` | `_resolve_pick_qseal_context` + `_build_pick_groups` |
| Put-away grouping | `app/api/v1/endpoints/put_away.py` | `_build_groups` |
| Packing-slip grouping | `app/services/packing_slip_service.py` | `_qseal_context` + `_build_groups` |

---

## 5. Field inheritance map

| `PackingSlipItem` field | Source | Notes |
|---|---|---|
| `item_id` | `pli.item_id` | copied |
| `qty` | `pli.picked_qty` | only lines with `picked_qty > 0` |
| `uom` | `pli.uom` | copied |
| `per_case_qty` | `pli.per_case_qty` | copied |
| `case_qty` | `pli.case_qty` | copied |
| `loose_qty` | `pli.loose_qty` | copied |
| `batch_no` | `pli.batch_no` | copied |
| `serial_nos` | `pli.serial_nos` | **copied verbatim — this is the parent/child inheritance** |
| `bin_location_id` | `pli.bin_location_id` | copied |
| `handling_unit_id` | `pli.handling_unit_id` | copied |

---

## 6. Why it's safe (no double-packing)

Order-based packing (`create_from_orders`) and pick-list-based packing
(`pack_pick_lists`) both target the same pick-list rows. They serialize via
`SELECT ... FOR UPDATE` on the pick lists and reject any pick list already
referenced by an active (non-cancelled) packing slip, so the same picked
serials cannot be packed twice.
