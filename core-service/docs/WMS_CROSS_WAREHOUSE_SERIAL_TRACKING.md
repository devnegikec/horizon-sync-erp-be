# WMS Cross-Warehouse Tracking — Pick → Pack → Dispatch → Receive

> How serialized goods are tracked from one warehouse to another, and why the
> inbound worker does **not** have to open every case / pallet / master carton.
>
> Related docs: `WMS_PACKING_SLIP_OUTBOUND_FLOW.md`,
> `WMS_PACKING_SLIP_PARENT_CHILD_INHERITANCE.md`,
> `ASN_RECEIVING_SLIP_LINK.md`, `ASN_RECEIVING_INTEGRATION_GUIDE.md`,
> `PACKAGING_UNIT_CONVERSION_FACTOR_VS_ITEMS_PER_MASTER_PACK.md`,
> `parent_child_qr_code.md`.

---

## 1. The 30-second version

Physical packing and digital serial tracking are **two independent layers**.
Tracking happens at the **unit-serial** level through a QR parent/child
hierarchy, so a receiving worker scans an **outer QR** (master carton / case /
pallet) and the system expands or verifies its contents — no physical
unpacking is required.

```text
Inbound (mother WH)      master carton (parent QR) ─▶ N unit serials (child QRs)
   └─ Put-away            one BinStockLevel row per serial, sharing parent_id
      └─ Pick list        child serial_nos resolved and grouped
         └─ Packing slip  serial_nos inherited verbatim
            └─ Dispatch   serials → ASN (asn_order_serial_lines) + transfer_out
               └─ Receive destination scans QR → verified vs ASN + transfer_in
```

---

## 2. Two layers that don't conflict

| Layer | Field | Question answered | Granularity |
|---|---|---|---|
| Physical packing | `item_packaging_units.conversion_factor` | "How many Eaches in this case/pallet?" (UOM math) | Case / pallet / box |
| Serial tracking | QSeal parent/child (`items_per_master_pack`) | "Which specific unit serials are inside this master carton?" | Individual unit |

A pallet of cases containing master cartons is a **physical** hierarchy. The
**digital** tracking hierarchy is *master carton → unit serials*. Cases and
pallets are carriers — the QR on them (or on the cartons inside) is what gets
scanned.

---

## 3. End-to-end chain of custody

### 3.1 Inbound (mother warehouse)

The QR engine (`qseal_service`) reads `items_per_master_pack` and links every
`N` child serials to one parent `QSealTrack` (the master carton):

- Parent carton → `QSealTrack` row with `capacity = N`.
- Each unit → `QSealParameters` row with `parent_id` pointing at the track.

Every unit also has its own scannable `ProductItem` serial QR.

### 3.2 Put-away

Stock lands as **one `BinStockLevel` row per serial** (`batch_number = serial`),
all sharing the same `parent_id` (`bin_stock_service` groups children under the
parent track via `qseal_parameters.parent_id → qseal_tracks`).

### 3.3 Pick list → packing slip

Both pick-list items and packing-slip items carry the exact child `serial_nos`
— inherited verbatim, never re-randomized (see
`WMS_PACKING_SLIP_PARENT_CHILD_INHERITANCE.md`). Parent/child is re-resolved at
read time from the QSeal data.

### 3.4 Dispatch — serials propagate into the transfer ASN

`outbound_service._propagate_transfer_serials` runs at dispatch and copies
every picked serial into the destination's ASN:

| Write | Effect |
|---|---|
| `AsnOrderItem.serial_nos` | merged picked serials on the ASN line |
| `asn_order_serial_lines` | one row per serial (`received = false`) |
| `SerialNo.status = "in_transit"` | unit marked in transit |
| `SerialNoHistory(transfer_out)` | custody record (from → to warehouse) |
| `MATERIAL_TRANSFER` stock entry | accounting traceability |

The ASN that reaches the destination therefore already contains the
**complete expected serial list**.

### 3.5 Receive — verification scan, not cataloguing

At the destination, `inbound_service.record_scan`:

1. Decodes the QR (`decode_qr_payload`).
2. Resolves the inventory `Item` (via `ProductItem → QRProduct → Item.qr_product_id`,
   with a SKU/GTIN fallback).
3. Validates the scan against the linked ASN's items.

For an `internal_transfer` ASN, `_verify_and_receive_transfer_serial` then:

- Matches the scanned serial against `asn_order_serial_lines`.
- Atomically claims the line (`UPDATE ... WHERE received = false`) — a duplicate
  scan is rejected.
- Marks `SerialNo.status = "in_stock"` and moves its `warehouse_id` to the
  destination.
- Writes `SerialNoHistory(transfer_in)`.
- Unknown serials (not on the ASN) are hard-stopped as inbound exceptions.

---

## 4. Why no one opens every case

Each physical level has a scannable QR, and scanning the **outer** code reveals
the contents:

| Scan | Endpoint | Result |
|---|---|---|
| Parent carton QR | `qseal_service.get_parent_with_linked_units(parent_id)` | returns **all N child serials** at once |
| Unit QR | `inbound_service.record_scan` | single serial, verified against ASN |
| Any QSeal code (parent or child) | `qseal_service.record_scan` | resolves `QSealTrack` vs `QSealParameters` |

So the receiving worker can:

- scan the **parent carton QR once** → the app lists its N units → receive them
  all **without opening the carton**, or
- scan individual unit QRs when verifying a partial / loose case.

Because the ASN already carries the expected serials from dispatch, receiving is
a **verification scan** (does this serial match the ASN?) rather than a
*cataloguing* exercise (what is in this box?).

---

## 5. Code reference map

| Step | File / function |
|---|---|
| Master-pack grouping | `app/services/qseal_service.py` (`master_pack_size`, parent/child linking) |
| Put-away grouping | `app/services/put_away_service.py` (`_items_per_master_pack`) |
| Pick-list grouping | `app/api/v1/endpoints/outbound.py` (`_build_pick_groups`) |
| Packing-slip inheritance | `app/services/packing_slip_service.py` (`serial_nos=pli.serial_nos`) |
| Dispatch propagation | `app/services/outbound_service.py` (`_propagate_transfer_serials`, `_create_transfer_stock_entry`) |
| Scan resolution | `app/services/inbound_service.py` (`record_scan`) |
| Transfer verification | `app/services/inbound_service.py` (`_verify_and_receive_transfer_serial`) |
| Parent expansion | `app/services/qseal_service.py` (`get_parent_with_linked_units`) |

---

## 6. QSeal hierarchy model

The schema already supports **multi-level** nesting:

- `QSealTrack.parent_id` is self-referential (shipper / pallet / container),
  so a track can nest under another track.
- `QSealParameters.parent_id` links a unit to its master track.
- `qseal_cascade` (parameters) and `app_cascade_map` (track) flag cascade use.

**Current expansion granularity:** `get_parent_with_linked_units` expands **one
level** — a parent track → its linked `QSealParameters` units. A
pallet → case → carton → unit expansion (one scan for the whole pallet) is
modelled in the schema but is not fully wired into inbound auto-expansion yet.

---

## 7. Known caveats

1. **Expansion depth** — one parent QR resolves its direct children; deeper
   pallet/case nesting requires either a scan per carton or additional cascade
   expansion logic.
2. **Legacy flag** — `Item.has_serial_no` is unreliable for QR-serialized items;
   serialization is determined by QSeal resolution, not that flag (fixed in
   pick / put-away / packing grouping).
3. **ASN serial lines only exist for serialized transfers** — non-serialized
   internal transfers verify by quantity (`AsnOrderItem.delivered_qty` /
   `shipped_qty`), not per-serial.
