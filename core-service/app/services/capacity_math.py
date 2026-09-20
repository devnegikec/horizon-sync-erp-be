"""Shared volume/weight capacity math (single source of truth).

Unit conventions (design doc §4.1):
- packaging dims are mm  -> volume m³ = L×W×H / 1e9
- packaging weight g     -> kg = g / 1000
- bin volume limit cc (cm³) -> m³ = cc / 1e6
- bin weight limit g     -> kg = g / 1000

MC-aware occupancy (design doc §4):
Stock ``quantity_on_hand`` is always in Eaches. When a stock row's packaging
unit is a master carton (``conversion_factor = c > 1``), the occupied volume is
computed as full cartons + loose remainder, so an intact 12-pack occupies
``1 × V_mc`` (not ``12 × V_mc``) and re-cubes automatically as Eaches are
picked:

    n_full  = floor(qty / c)
    n_loose = qty - n_full * c
    V_row   = n_full * V_pu + n_loose * V_ic
    W_row   = n_full * W_pu + n_loose * W_ic

Used by ``BinCapacityService`` (reporting) and ``BinStockService``
(enforcement).
"""

import uuid
from decimal import Decimal

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, aliased

from app.models.bin_stock_level import BinStockLevel
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.warehouse_location import WarehouseLocation

MM3_PER_M3 = Decimal("1000000000")  # 1e9
G_PER_KG = Decimal("1000")
CC_PER_M3 = Decimal("1000000")  # 1e6 (cc == cm³)
MM3_PER_CC = Decimal("1000")  # mm³ → cc


def _normalize_uuid_key(value) -> str:
    """Normalize a UUID (hex or hyphenated) to its hyphenated string form."""
    s = str(value)
    if len(s) == 32 and "-" not in s:
        try:
            s = str(uuid.UUID(s))
        except ValueError:
            pass
    return s


def _num(value) -> Decimal | None:
    """Convert a DB numeric/None to Decimal or None."""
    return Decimal(str(value)) if value is not None else None


def _dims_volume_mm3(l, w, h) -> Decimal | None:
    """Volume in mm³ from three dimension values, or None if any is missing."""
    if l is None or w is None or h is None:
        return None
    return _num(l) * _num(w) * _num(h)  # type: ignore[operator]


def _row_occupied(
    qty,
    conversion_factor,
    pu_length,
    pu_width,
    pu_height,
    pu_weight,
    base_length,
    base_width,
    base_height,
    base_weight,
) -> tuple[Decimal, Decimal]:
    """Return (volume_mm3, weight_grams) for one bin-stock row.

    Missing dimensions contribute 0 (unmeasured); missing weights contribute 0.
    ``qty`` is in Eaches. ``conversion_factor`` converts Eaches → packaging-unit
    count (MC) so an intact carton counts once, not ``c`` times.
    """
    qty_d = _num(qty) or Decimal("0")
    c = _num(conversion_factor)
    if c is None or c < 1:
        c = Decimal("1")

    n_full = qty_d // c
    n_loose = qty_d - n_full * c

    # Effective packaging-unit dims: fall back per-dimension to the base unit.
    l = _num(pu_length) if pu_length is not None else _num(base_length)
    w = _num(pu_width) if pu_width is not None else _num(base_width)
    h = _num(pu_height) if pu_height is not None else _num(base_height)
    pu_vol = _dims_volume_mm3(l, w, h) or Decimal("0")

    base_vol = (
        _dims_volume_mm3(_num(base_length), _num(base_width), _num(base_height))
        or Decimal("0")
    )

    vol = n_full * pu_vol + n_loose * base_vol

    pu_w = _num(pu_weight) if pu_weight is not None else _num(base_weight)
    base_w = _num(base_weight)
    weight = n_full * (pu_w or Decimal("0")) + n_loose * (base_w or Decimal("0"))

    return vol, weight


def _iter_bin_stock_rows(db: Session, *, warehouse_id=None, bin_id=None):
    """Yield (bin_location_id, qty, packaging-unit fields, base-unit fields).

    Stock is aggregated per (bin, item, packaging unit) so serialized
    master-pack stock — stored as one bin-stock row per serial with
    ``quantity_on_hand = 1`` — still sums to full master cartons for the
    ``floor(qty / c)`` volume/count math. When a stock row has no explicit
    ``packaging_unit_id``, the item's active master-pack unit
    (``conversion_factor > 1``) is used as a fallback, so MC outer volume and
    master-pack count work end-to-end even when the pointer was never wired.
    """
    base = aliased(ItemPackagingUnit)

    query = (
        db.query(
            BinStockLevel.bin_location_id,
            BinStockLevel.item_id,
            BinStockLevel.packaging_unit_id,
            func.sum(BinStockLevel.quantity_on_hand),
            func.max(base.length_mm),
            func.max(base.width_mm),
            func.max(base.height_mm),
            func.max(base.weight_grams),
        )
        .outerjoin(
            base,
            and_(
                base.item_id == BinStockLevel.item_id,
                base.is_base_unit.is_(True),
            ),
        )
        .group_by(
            BinStockLevel.bin_location_id,
            BinStockLevel.item_id,
            BinStockLevel.packaging_unit_id,
        )
    )

    if warehouse_id is not None:
        query = query.join(
            WarehouseLocation,
            WarehouseLocation.id == BinStockLevel.bin_location_id,
        ).filter(
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.location_type == "bin",
            WarehouseLocation.is_active.is_(True),
        )
    if bin_id is not None:
        query = query.filter(BinStockLevel.bin_location_id == bin_id)
    query = query.filter(BinStockLevel.quantity_on_hand > 0)

    rows = query.all()

    # Per-item cache for the master-pack fallback (avoids an N+1 query per row).
    mc_cache: dict[uuid.UUID, ItemPackagingUnit | None] = {}
    for row in rows:
        bin_loc_id, item_id, packaging_unit_id, qty, bl, bw, bh, bwt = row

        pu: ItemPackagingUnit | None = None
        if packaging_unit_id is not None:
            pu = db.get(ItemPackagingUnit, packaging_unit_id)
        if pu is None:
            if item_id not in mc_cache:
                mc_cache[item_id] = (
                    db.query(ItemPackagingUnit)
                    .filter(
                        ItemPackagingUnit.item_id == item_id,
                        ItemPackagingUnit.is_base_unit.is_(False),
                        ItemPackagingUnit.conversion_factor > 1,
                        ItemPackagingUnit.is_active.is_(True),
                    )
                    .order_by(ItemPackagingUnit.conversion_factor.asc())
                    .first()
                )
            pu = mc_cache[item_id]

        cf = _num(pu.conversion_factor) if pu is not None else None
        yield (
            bin_loc_id,
            _num(qty) or Decimal("0"),
            cf,
            _num(pu.length_mm) if pu is not None else None,
            _num(pu.width_mm) if pu is not None else None,
            _num(pu.height_mm) if pu is not None else None,
            _num(pu.weight_grams) if pu is not None else None,
            _num(bl),
            _num(bw),
            _num(bh),
            _num(bwt),
        )


def compute_bin_occupancy(
    db: Session,
    bin_id,
    use_volume: bool = True,
    use_weight: bool = True,
) -> tuple[Decimal, Decimal]:
    """Return (occupied_m3, occupied_kg) for one bin."""
    total_mm3 = Decimal("0")
    total_g = Decimal("0")
    for row in _iter_bin_stock_rows(db, bin_id=bin_id):
        mm3, grams = _row_occupied(*row[1:])
        total_mm3 += mm3
        total_g += grams

    occupied_m3 = (total_mm3 / MM3_PER_M3) if use_volume else Decimal("0")
    occupied_kg = (total_g / G_PER_KG) if use_weight else Decimal("0")
    return occupied_m3, occupied_kg


def compute_warehouse_bin_occupancy(
    db: Session,
    warehouse_id,
    use_volume: bool = True,
    use_weight: bool = True,
) -> dict[str, tuple[Decimal, Decimal]]:
    """Return {str(bin_id): (occupied_m3, occupied_kg)} for all bins."""
    totals: dict[str, tuple[Decimal, Decimal]] = {}
    for row in _iter_bin_stock_rows(db, warehouse_id=warehouse_id):
        bin_key = _normalize_uuid_key(row[0])
        mm3, grams = _row_occupied(*row[1:])
        prev_mm3, prev_g = totals.get(bin_key, (Decimal("0"), Decimal("0")))
        totals[bin_key] = (prev_mm3 + mm3, prev_g + grams)

    result: dict[str, tuple[Decimal, Decimal]] = {}
    for bin_key, (mm3, grams) in totals.items():
        result[bin_key] = (
            (mm3 / MM3_PER_M3) if use_volume else Decimal("0"),
            (grams / G_PER_KG) if use_weight else Decimal("0"),
        )
    return result


def compute_bin_counts(db: Session, bin_id) -> tuple[Decimal, Decimal]:
    """Return (unit_count_eaches, master_pack_count) for one bin."""
    units = Decimal("0")
    packs = Decimal("0")
    for row in _iter_bin_stock_rows(db, bin_id=bin_id):
        qty = _num(row[1]) or Decimal("0")
        c = _num(row[2])
        units += qty
        if c is not None and c > 1:
            packs += qty // c
    return units, packs


def compute_warehouse_bin_counts(
    db: Session,
    warehouse_id,
) -> dict[str, tuple[Decimal, Decimal]]:
    """Return {str(bin_id): (unit_count_eaches, master_pack_count)}."""
    result: dict[str, tuple[Decimal, Decimal]] = {}
    for row in _iter_bin_stock_rows(db, warehouse_id=warehouse_id):
        key = _normalize_uuid_key(row[0])
        qty = _num(row[1]) or Decimal("0")
        c = _num(row[2])
        units, packs = result.get(key, (Decimal("0"), Decimal("0")))
        units += qty
        if c is not None and c > 1:
            packs += qty // c
        result[key] = (units, packs)
    return result


def compute_item_required_cc_and_grams(
    db: Session,
    item_id,
    packaging_unit_id,
    quantity,
) -> tuple[Decimal | None, Decimal | None]:
    """Return (required_volume_cc, required_weight_grams) for incoming stock.

    ``quantity`` is in Eaches. Returns ``None`` for a dimension when it cannot be
    measured (no dimensions / no weight on either the packaging unit or the base
    unit), matching the "null = unconstrained" convention.
    """
    ipu = db.get(ItemPackagingUnit, packaging_unit_id) if packaging_unit_id else None
    if ipu is None:
        # Match occupancy: fall back to the item's active master-pack unit so
        # enforcement and reporting agree on MC outer dimensions.
        ipu = (
            db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.item_id == item_id,
                ItemPackagingUnit.is_base_unit.is_(False),
                ItemPackagingUnit.conversion_factor > 1,
                ItemPackagingUnit.is_active.is_(True),
            )
            .order_by(ItemPackagingUnit.conversion_factor.asc())
            .first()
        )
    base = (
        db.query(ItemPackagingUnit)
        .filter(
            ItemPackagingUnit.item_id == item_id,
            ItemPackagingUnit.is_base_unit.is_(True),
        )
        .first()
    )

    qty_d = _num(quantity) or Decimal("0")
    c = _num(ipu.conversion_factor) if ipu is not None else Decimal("1")
    if c is None or c < 1:
        c = Decimal("1")

    n_full = qty_d // c
    n_loose = qty_d - n_full * c

    # Effective packaging-unit dims fall back per-dimension to base.
    pu_l = _num(ipu.length_mm) if ipu is not None else None
    pu_w = _num(ipu.width_mm) if ipu is not None else None
    pu_h = _num(ipu.height_mm) if ipu is not None else None
    pu_weight = _num(ipu.weight_grams) if ipu is not None else None

    base_l = _num(base.length_mm) if base is not None else None
    base_w = _num(base.width_mm) if base is not None else None
    base_h = _num(base.height_mm) if base is not None else None
    base_weight = _num(base.weight_grams) if base is not None else None

    l = pu_l if pu_l is not None else base_l
    w = pu_w if pu_w is not None else base_w
    h = pu_h if pu_h is not None else base_h
    pu_vol = _dims_volume_mm3(l, w, h)
    base_vol = _dims_volume_mm3(base_l, base_w, base_h)

    required_cc: Decimal | None = None
    if pu_vol is not None or base_vol is not None:
        vol_mm3 = n_full * (pu_vol or Decimal("0")) + n_loose * (
            base_vol or Decimal("0")
        )
        required_cc = vol_mm3 / MM3_PER_CC

    required_g: Decimal | None = None
    eff_pu_w = pu_weight if pu_weight is not None else base_weight
    if eff_pu_w is not None or base_weight is not None:
        w_full = n_full * (eff_pu_w or Decimal("0"))
        w_loose = n_loose * (base_weight or Decimal("0"))
        required_g = w_full + w_loose

    return required_cc, required_g
