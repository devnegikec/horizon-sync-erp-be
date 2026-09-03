"""Backfill uom_type for existing UOMs.

Revision ID: 106_backfill_uom_type
Revises: 105_add_transfer_pick_created_notification_type
Create Date: 2026-09-02

Standard UOMs seeded before the ``uom_type`` classification was introduced have
a NULL ``uom_type``. Warehouse capacity selection (and any other type-filtered
UOM pickers) rely on ``uom_type`` to show only measurement-type units, so this
migration classifies the known standard UOMs by their canonical name.

Custom UOMs created by organizations are left untouched (NULL). Matching on the
canonical name (rather than only the abbreviation) avoids miscategorizing a
custom unit that reuses a standard abbreviation such as ``KG`` or ``PCS``.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "106_backfill_uom_type"
down_revision: str | Sequence[str] | None = (
    "105_add_transfer_pick_created_notification_type"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE uoms
        SET uom_type = CASE UPPER(name)
            -- Quantity / count
            WHEN 'PIECE' THEN 'count'
            WHEN 'DOZEN' THEN 'count'
            WHEN 'PAIR' THEN 'count'
            WHEN 'SET' THEN 'count'
            WHEN 'BOX' THEN 'count'
            WHEN 'CARTON' THEN 'count'
            WHEN 'PACK' THEN 'count'
            WHEN 'ROLL' THEN 'count'
            WHEN 'SHEET' THEN 'count'
            WHEN 'BUNDLE' THEN 'count'
            -- Weight
            WHEN 'KILOGRAM' THEN 'weight'
            WHEN 'GRAM' THEN 'weight'
            WHEN 'MILLIGRAM' THEN 'weight'
            WHEN 'METRIC TON' THEN 'weight'
            WHEN 'POUND' THEN 'weight'
            WHEN 'OUNCE' THEN 'weight'
            -- Volume
            WHEN 'LITER' THEN 'volume'
            WHEN 'MILLILITER' THEN 'volume'
            WHEN 'CUBIC METER' THEN 'volume'
            WHEN 'GALLON' THEN 'volume'
            -- Length
            WHEN 'METER' THEN 'length'
            WHEN 'CENTIMETER' THEN 'length'
            WHEN 'MILLIMETER' THEN 'length'
            WHEN 'KILOMETER' THEN 'length'
            WHEN 'INCH' THEN 'length'
            WHEN 'FOOT' THEN 'length'
            WHEN 'YARD' THEN 'length'
            -- Area
            WHEN 'SQUARE METER' THEN 'area'
            WHEN 'SQUARE FOOT' THEN 'area'
            -- Time
            WHEN 'HOUR' THEN 'time'
            WHEN 'DAY' THEN 'time'
            WHEN 'MONTH' THEN 'time'
            WHEN 'YEAR' THEN 'time'
            -- Other
            WHEN 'UNIT' THEN 'other'
            WHEN 'LOT' THEN 'other'
            WHEN 'PALLET' THEN 'other'
            WHEN 'CONTAINER' THEN 'other'
            WHEN 'BAG' THEN 'other'
            WHEN 'DRUM' THEN 'other'
            WHEN 'BOTTLE' THEN 'other'
        END
        WHERE uom_type IS NULL
          AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    # Reverting would re-hide standard UOMs from type-filtered pickers; this is
    # intentionally a no-op to avoid data loss.
    pass
