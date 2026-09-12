"""Close UOM scalability gaps (Section 5 of PRODUCT_ITEM_UOM_ARCHITECTURE.md).

- Add uoms.is_active.
- Backfill uoms.uom_type / precision for rows missing them.
- Backfill uom_conversions.from_uom_id / to_uom_id from the legacy name caches.
- Backfill packaging_types.uom_id (map each pack type to a count UOM).
- Add an ID-based partial unique index on uom_conversions.

Revision ID: 086_uom_scalability_closers
Revises: 085_reconcile_qseal_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_index

revision: str = "086_uom_scalability_closers"
down_revision: str | Sequence[str] | None = "085_reconcile_qseal_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (uom_type, precision) keyed by lower-cased name or abbreviation.
UOM_TYPE_MAP: dict[str, tuple[str, int]] = {
    # weight
    "kg": ("weight", 3), "kilogram": ("weight", 3),
    "gm": ("weight", 0), "gram": ("weight", 0), "g": ("weight", 0),
    "lb": ("weight", 2), "pound": ("weight", 2),
    "oz": ("weight", 2), "ounce": ("weight", 2),
    "mg": ("weight", 0), "ton": ("weight", 2), "tn": ("weight", 2),
    # volume
    "l": ("volume", 2), "ltr": ("volume", 2), "liter": ("volume", 2),
    "litre": ("volume", 2), "ml": ("volume", 0), "cl": ("volume", 1),
    "gal": ("volume", 2), "gallon": ("volume", 2),
    # length
    "m": ("length", 2), "mtr": ("length", 2), "meter": ("length", 2),
    "metre": ("length", 2), "cm": ("length", 1), "mm": ("length", 0),
    "ft": ("length", 1), "in": ("length", 1), "yd": ("length", 1),
    "yard": ("length", 1),
    # area
    "sqm": ("area", 2), "sqf": ("area", 2), "sqi": ("area", 2),
    # time
    "yr": ("time", 0), "year": ("time", 0), "mo": ("time", 0),
    "month": ("time", 0), "day": ("time", 0), "wk": ("time", 0),
    "week": ("time", 0), "hr": ("time", 1), "hour": ("time", 1),
    "min": ("time", 0), "sec": ("time", 0),
    # count
    "pc": ("count", 0), "pcs": ("count", 0), "piece": ("count", 0),
    "ea": ("count", 0), "each": ("count", 0), "unit": ("count", 0),
    "set": ("count", 0), "roll": ("count", 0), "rol": ("count", 0),
    "sheet": ("count", 0), "sht": ("count", 0), "nos": ("count", 0),
    # measurement extras
    "cbm": ("volume", 2), "cubicmeter": ("volume", 2), "km": ("length", 2),
    "kilometer": ("length", 2), "doz": ("count", 0), "dozen": ("count", 0),
    "mt": ("weight", 3), "metricton": ("weight", 3), "pr": ("count", 0),
    "pair": ("count", 0),
    # physical pack units (countable; see 5.3 — ideally moved to packaging_types)
    "bag": ("count", 0), "box": ("count", 0), "btl": ("count", 0),
    "bottle": ("count", 0), "ctn": ("count", 0), "carton": ("count", 0),
    "drm": ("count", 0), "drum": ("count", 0), "plt": ("count", 0),
    "pallet": ("count", 0), "pck": ("count", 0), "pk": ("count", 0),
    "pack": ("count", 0), "cnt": ("count", 0), "container": ("count", 0),
    "bdl": ("count", 0), "bundle": ("count", 0), "lot": ("count", 0),
}


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. uoms.is_active ───────────────────────────────────────────────────
    if not has_column("uoms", "is_active"):
        op.add_column(
            "uoms",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )
    if not has_index("uoms", "ix_uoms_is_active"):
        op.create_index("ix_uoms_is_active", "uoms", ["is_active"])

    # ── 2. Backfill uoms.uom_type / precision ──────────────────────────────
    rows = bind.execute(
        sa.text("SELECT id, name, abbreviation, uom_type FROM uoms")
    ).fetchall()
    for row in rows:
        mapping = row._mapping
        if mapping["uom_type"]:
            continue  # already typed — do not overwrite
        key = (mapping["name"] or "").strip().lower()
        abbr = (mapping["abbreviation"] or "").strip().lower()
        mapped = UOM_TYPE_MAP.get(key) or UOM_TYPE_MAP.get(abbr)
        if mapped:
            uom_type, precision = mapped
            bind.execute(
                sa.text(
                    "UPDATE uoms SET uom_type = :t, precision = :p WHERE id = :id"
                ),
                {"t": uom_type, "p": precision, "id": mapping["id"]},
            )

    # ── 3. Backfill uom_conversions.from_uom_id / to_uom_id ────────────────
    bind.execute(
        sa.text(
            """
            UPDATE uom_conversions c
            SET from_uom_id = u.id
            FROM uoms u
            WHERE c.from_uom_id IS NULL
              AND u.organization_id = c.organization_id
              AND (u.name = c.from_uom OR u.abbreviation = c.from_uom)
              AND u.deleted_at IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE uom_conversions c
            SET to_uom_id = u.id
            FROM uoms u
            WHERE c.to_uom_id IS NULL
              AND u.organization_id = c.organization_id
              AND (u.name = c.to_uom OR u.abbreviation = c.to_uom)
              AND u.deleted_at IS NULL
            """
        )
    )

    # ── 4. Backfill packaging_types.uom_id (map to a count UOM) ────────────
    pts = bind.execute(
        sa.text("SELECT id, organization_id FROM packaging_types WHERE uom_id IS NULL")
    ).fetchall()
    for pt in pts:
        mapping = pt._mapping
        org = mapping["organization_id"]
        count_uom = bind.execute(
            sa.text(
                """
                SELECT id FROM uoms
                WHERE organization_id = :org
                  AND deleted_at IS NULL
                  AND (LOWER(abbreviation) IN ('ea', 'pcs', 'pc', 'unit', 'each')
                       OR uom_type = 'count')
                ORDER BY CASE LOWER(abbreviation)
                    WHEN 'ea' THEN 0 WHEN 'pcs' THEN 1 WHEN 'pc' THEN 2
                    WHEN 'unit' THEN 3 WHEN 'each' THEN 4 ELSE 5 END
                LIMIT 1
                """
            ),
            {"org": org},
        ).fetchone()
        if count_uom is not None:
            bind.execute(
                sa.text("UPDATE packaging_types SET uom_id = :uid WHERE id = :id"),
                {"uid": count_uom._mapping["id"], "id": mapping["id"]},
            )

    # ── 5. ID-based partial unique index on uom_conversions ────────────────
    if not has_index("uom_conversions", "uq_uom_conv_org_item_ids"):
        op.create_index(
            "uq_uom_conv_org_item_ids",
            "uom_conversions",
            ["organization_id", "item_id", "from_uom_id", "to_uom_id"],
            unique=True,
            postgresql_where=sa.text(
                "deleted_at IS NULL AND from_uom_id IS NOT NULL AND to_uom_id IS NOT NULL"
            ),
        )


def downgrade() -> None:
    if has_index("uom_conversions", "uq_uom_conv_org_item_ids"):
        op.drop_index(
            "uq_uom_conv_org_item_ids",
            table_name="uom_conversions",
        )
    if has_index("uoms", "ix_uoms_is_active"):
        op.drop_index("ix_uoms_is_active", table_name="uoms")
    if has_column("uoms", "is_active"):
        op.drop_column("uoms", "is_active")
