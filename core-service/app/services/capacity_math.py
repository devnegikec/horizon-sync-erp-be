"""Shared volume/weight capacity math (single source of truth).

Unit conventions (design doc §4.1):
- packaging dims are mm  -> volume m³ = L×W×H / 1e9
- packaging weight g     -> kg = g / 1000
- bin volume limit cc (cm³) -> m³ = cc / 1e6
- bin weight limit g     -> kg = g / 1000

Used by ``BinCapacityService``. Kept as a standalone module so future
refactors of ``VolumetricAssignmentService`` can reuse identical formulas.
"""

import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

MM3_PER_M3 = Decimal("1000000000")  # 1e9
G_PER_KG = Decimal("1000")
CC_PER_M3 = Decimal("1000000")  # 1e6 (cc == cm³)


def _dialect(db: Session) -> str:
    try:
        return db.get_bind().dialect.name
    except Exception:
        return "sqlite"


def _uuid_bind(db: Session, value) -> str:
    """Return the dialect-appropriate string form of a UUID for raw SQL binds.

    The custom GUID type stores UUIDs as 32-char hex on SQLite/CHAR columns but
    as native UUIDs on PostgreSQL, so raw ``text()`` parameters must match.
    """
    v = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    return str(v) if _dialect(db) == "postgresql" else v.hex


def _normalize_uuid_key(value) -> str:
    """Normalize a UUID (hex or hyphenated) to its hyphenated string form."""
    s = str(value)
    if len(s) == 32 and "-" not in s:
        try:
            s = str(uuid.UUID(s))
        except ValueError:
            pass
    return s


_BIN_OCCUPANCY_SQL = text(
    """
    SELECT
        COALESCE(SUM(
            bsl.quantity_on_hand
            * COALESCE(ipu.length_mm, base.length_mm)
            * COALESCE(ipu.width_mm, base.width_mm)
            * COALESCE(ipu.height_mm, base.height_mm)
        ), 0) AS occupied_mm3,
        COALESCE(SUM(
            bsl.quantity_on_hand * COALESCE(ipu.weight_grams, base.weight_grams)
        ), 0) AS occupied_grams
    FROM bin_stock_levels bsl
    LEFT JOIN item_packaging_units ipu ON ipu.id = bsl.packaging_unit_id
    LEFT JOIN item_packaging_units base
        ON base.item_id = bsl.item_id AND base.is_base_unit = TRUE
    WHERE bsl.bin_location_id = :bin_id
      AND bsl.quantity_on_hand > 0
    """
)

_WAREHOUSE_OCCUPANCY_SQL = text(
    """
    SELECT
        wl.id AS bin_id,
        COALESCE(SUM(
            bsl.quantity_on_hand
            * COALESCE(ipu.length_mm, base.length_mm)
            * COALESCE(ipu.width_mm, base.width_mm)
            * COALESCE(ipu.height_mm, base.height_mm)
        ), 0) AS occupied_mm3,
        COALESCE(SUM(
            bsl.quantity_on_hand * COALESCE(ipu.weight_grams, base.weight_grams)
        ), 0) AS occupied_grams
    FROM warehouse_locations wl
    LEFT JOIN bin_stock_levels bsl ON bsl.bin_location_id = wl.id
    LEFT JOIN item_packaging_units ipu ON ipu.id = bsl.packaging_unit_id
    LEFT JOIN item_packaging_units base
        ON base.item_id = bsl.item_id AND base.is_base_unit = TRUE
    WHERE wl.warehouse_id = :warehouse_id
      AND wl.location_type = 'bin'
      AND wl.is_active = TRUE
    GROUP BY wl.id
    """
)


def compute_bin_occupancy(
    db: Session,
    bin_id,
    use_volume: bool = True,
    use_weight: bool = True,
) -> tuple[Decimal, Decimal]:
    """Return (occupied_m3, occupied_kg) for one bin."""
    row = db.execute(
        _BIN_OCCUPANCY_SQL, {"bin_id": _uuid_bind(db, bin_id)}
    ).fetchone()
    if row is None:
        return Decimal("0"), Decimal("0")
    mm3 = Decimal(str(row[0]))
    grams = Decimal(str(row[1]))
    occupied_m3 = (mm3 / MM3_PER_M3) if use_volume else Decimal("0")
    occupied_kg = (grams / G_PER_KG) if use_weight else Decimal("0")
    return occupied_m3, occupied_kg


def compute_warehouse_bin_occupancy(
    db: Session,
    warehouse_id,
    use_volume: bool = True,
    use_weight: bool = True,
) -> dict[str, tuple[Decimal, Decimal]]:
    """Return {str(bin_id): (occupied_m3, occupied_kg)} for all active bins."""
    rows = db.execute(
        _WAREHOUSE_OCCUPANCY_SQL, {"warehouse_id": _uuid_bind(db, warehouse_id)}
    ).fetchall()
    result: dict[str, tuple[Decimal, Decimal]] = {}
    for row in rows:
        mm3 = Decimal(str(row[1]))
        grams = Decimal(str(row[2]))
        result[_normalize_uuid_key(row[0])] = (
            (mm3 / MM3_PER_M3) if use_volume else Decimal("0"),
            (grams / G_PER_KG) if use_weight else Decimal("0"),
        )
    return result
