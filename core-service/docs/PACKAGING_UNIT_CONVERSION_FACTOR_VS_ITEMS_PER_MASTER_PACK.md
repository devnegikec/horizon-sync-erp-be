# `conversion_factor` vs `items_per_master_pack` on Item Packaging Units

Two fields on `item_packaging_units` both express "how many units fit in a pack",
but they answer **different** questions and are consumed by **different** parts
of the system. This document clarifies each and when they must be set.

## Field definitions

### `conversion_factor` — physical pack size (required)

**"Number of base units (Eaches) in this packaging unit."** This is the classic
UOM / pack-hierarchy count, item-scoped:

| Packaging unit | `conversion_factor` |
|---|---|
| `Each` (base) | `1` |
| `Box of 12` | `12` |
| `Case` | `24` |
| `Pallet` | `144` |

Constraints (enforced in `app/models/item_packaging_unit.py`):

- `NOT NULL`
- `CHECK (conversion_factor > 0)`

So it is **always required**, including the base "Each" unit (which must be `1`).

### `items_per_master_pack` — QR master-pack grouping size (optional)

**"Number of items grouped under one master pack, used to auto-populate the QR
block 'Items per Master Pack' setting."** Added by Alembic migration
`075_add_items_per_master_pack`. It is `Integer`, **nullable**, and semantically
tied to QSeal parent/child serialization: how many child serials sit under a
single parent (master pack) QR.

### `uom_conversions.conversion_factor` — UOM ↔ UOM math (Settings → Items & UOM)

A **third**, separate "factor" field lives in the `uom_conversions` table (the
"Units of Measure / UOM Conversions" screen). It converts quantities between two
units of measure, e.g. **1 Pack = 4 Pieces**:

| From UOM | To UOM | `conversion_factor` |
|---|---|---|
| `Pack` (PK) | `Piece` (PC) | `4` |

Conversion semantics (`app/services/uom_conversion_service.py`):

- forward (`from_uom → to_uom`): `quantity × factor`
- reverse (`to_uom → from_uom`): `quantity ÷ factor`

So with `Pack → Piece = 4`: `2 Packs = 8 Pieces` and `8 Pieces = 2 Packs`.

**For a "1 box of 4" master-pack item, set** (and delete any no-op
`Piece → Piece = 1` row):

| From UOM | To UOM | Factor |
|---|---|---|
| `Pack` (PK) | `Piece` (PC) | `4` |

Keep `items_per_master_pack = 4` on the item's base `Each` packaging unit — that
is what drives QR master-pack grouping; the `uom_conversions` factor is what
keeps the UOM quantity math (Packs ↔ Pieces) consistent.

> **Base UOM warning:** if an item's base UOM is `Pack`, stock is counted in
> Packs and `Pack → Piece = 4` lets quantities be expressed in Pieces when
> needed. If you actually track stock in Pieces, set the base UOM to `Piece`
> instead — otherwise the base UOM and the conversion will disagree downstream.

## Where each is used

### `conversion_factor`

| Location | Usage |
|---|---|
| `app/services/inbound_service.py` | `eaches_qty = raw_quantity * pu.conversion_factor` (scan → base units) |
| `app/services/stock_entry_service.py` | Stock-entry quantity conversion |
| `app/services/outbound_order_service.py` (`_resolve_packaging`) | Fallback "items per case" for **non-base** units |
| `app/services/qr_product_service.py` | Copied into QR product packaging details |

### `items_per_master_pack`

| Location | Usage |
|---|---|
| `app/services/put_away_service.py` (`_items_per_master_pack`) | Group unit serials into master packs during put-away |
| `app/services/outbound_order_service.py` (`_resolve_packaging`) | Split pick lines into master-pack-sized boxes (base unit) |
| `app/services/location_suggestion_service.py` (`_items_per_master_pack`) | Pack-first bin suggestions (`_score_pick_by_pack`) |
| `app/services/organization_onboarding_service.py` (`_resolve_item_master_pack_size`) | QR block "Items per Master Pack" auto-population |
| `app/services/item_service.py` (`get_items_for_picker`) | Picker dropdown master-pack size |
| `app/services/qseal_service.py` | Parent/child auto-linking (`master_pack_size`) |

## Comparison

| | `conversion_factor` | `items_per_master_pack` |
|---|---|---|
| Meaning | Base units per physical pack (UOM hierarchy) | Serialized units per QR master pack |
| Scope | Any packaging unit (`Each`/`Box`/`Case`/`Pallet`) | Only master-pack (QSeal) items |
| Required | **Yes** (`NOT NULL`, `> 0`) | No (nullable) |
| Typical value | `Each=1`, `Box=12`, `Case=24` | e.g. `4` (stored on the base "Each" unit) |
| Drives | Quantity → Eaches conversion, capacity math | QR block pack size, put-away/pick pack grouping, pack-first suggestions |

The two fields deliberately overlap ("N units in a pack") — this is called out
as a known overlap in `core-service/docs/PRODUCT_ITEM_UOM_ARCHITECTURE.md`
(section 3.2). The difference is the question each answers: *how the physical
box is counted* vs *how QR master packs are grouped*.

## When must they be set?

- **`conversion_factor` — always.** It is a database constraint; every packaging
  unit (including the base `Each` unit) must carry a positive value.
- **`items_per_master_pack` — only for QR/master-pack serialized items.** Set it
  (in practice on the base "Each" unit) when the item is serialized into master
  packs and you want:
  1. Pick lists to split order quantities into full master-pack boxes.
  2. Put-away to group unit serials into packs.
  3. QR block creation to auto-populate the pack size.
  4. Bin suggestions to prefer whole packs over loose units.

  When `items_per_master_pack` is `NULL`, those pack-aware behaviours fall back
  to `conversion_factor` (for non-base units) or treat the item as
  non-pack-managed.

## Worked example: IPH-17 / IPH-18 (inbound → outbound)

Both demo items share the same packaging config:

| Field | IPH-17 (`ITM-2026-00033`) | IPH-18 (`ITM-2026-00034`) |
|---|---|---|
| Base unit | `Each` — `conversion_factor = 1` | `Each` — `conversion_factor = 1` |
| `items_per_master_pack` | `4` | `4` |
| Serialized units on hand | 200 | 214 |

### 1. Inbound — stock receipt at the mother warehouse

- **IPH-17 (200 phones):** the QR engine (`qseal_service`) reads
  `items_per_master_pack = 4` and auto-links every 4 serials to one parent QR
  (QSealTrack) → **50 master cartons**, each holding 4 child serials.
  `conversion_factor = 1` keeps the counted quantity in **Eaches**
  (200 units, not 50 cartons).
- **IPH-18 (214 phones):** `214 ÷ 4 = 53` full cartons (212 phones)
  **+ 2 loose phones** — a broken/partial carton.

| Product | Eaches | Full master cartons | Loose units |
|---|---|---|---|
| IPH-17 | 200 | 50 | 0 |
| IPH-18 | 214 | 53 | 2 |

`items_per_master_pack` produces the carton grouping; `conversion_factor`
keeps the counted quantity in Eaches.

### 2. Put-away at the mother warehouse

Each master carton is put away as one group. Stock lands as one
`BinStockLevel` row **per serial** (`batch_number = serial`), all rows sharing
the same `parent_id`:

```
IPH-18 → Bin A: 8 full cartons (32 serials)      ← complete packs
         Bin B: 2 loose units (partial carton)   ← broken pack
```

### 3. Outbound — internal transfer to the exit warehouse

Transferring **8 × IPH-17** and **6 × IPH-18**:

- Pick-list generation (`_resolve_packaging`) uses `items_per_master_pack = 4`
  to split lines into boxes:

| Product | Transfer qty | Pick lines (boxes) |
|---|---|---|
| IPH-17 | 8 | `4 + 4` (2 full cartons) |
| IPH-18 | 6 | `4 + 2` (1 full carton + 2 loose) |

- Bin suggestion (`_score_pick_by_pack`) ranks bins holding a **complete carton
  first**; the 2 loose IPH-18 units are not suggested while a full carton still
  exists. The picker moves whole cartons and only breaks one open when the
  order's remainder genuinely requires loose units.

### What breaks if a field is missing or wrong

| Missing / wrong | Inbound symptom | Outbound symptom |
|---|---|---|
| `conversion_factor` missing/wrong | Cartons counted as Eaches (2 cartons → 2 phones) | Wrong quantities on orders / pick lines |
| `items_per_master_pack` missing | No master-carton grouping | Pick list collapses to one line instead of per-carton boxes; suggestions point at loose units |

## Note (bug history)

`outbound_order_service._resolve_packaging` originally only fell back to
**non-base** units' `conversion_factor`, so a base-unit `items_per_master_pack`
was ignored and order-driven pick lists were not split into master-pack boxes.
That was fixed by resolving the base unit's `items_per_master_pack` first.
