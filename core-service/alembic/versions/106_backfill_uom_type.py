"""Backfill uom_type for existing UOMs.

Revision ID: 106_backfill_uom_type
Revises: 105_add_transfer_pick_created_notification_type
Create Date: 2026-09-02

Standard UOMs seeded before the ``uom_type`` classification was introduced have
a NULL ``uom_type``. Warehouse capacity selection (and any other type-filtered
UOM pickers) rely on ``uom_type`` to show only measurement-type units, so this
migration classifies the known standard UOMs by abbreviation.

Custom UOMs created by organizations are left untouched (NULL) so they are not
miscategorized.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "106_backfill_uom_type"
down_revision: str | Sequence[str] | None = "105_add_transfer_pick_created_notification_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE uoms
        SET uom_type = CASE UPPER(abbreviation)
            -- Quantity / count
            WHEN 'PCS' THEN 'count'
            WHEN 'DOZ' THEN 'count'
            WHEN 'PR'  THEN 'count'
            WHEN 'SET' THEN 'count'
            WHEN 'BOX' THEN 'count'
            WHEN 'CTN' THEN 'count'
            WHEN 'PCK' THEN 'count'
            WHEN 'ROL' THEN 'count'
            WHEN 'SHT' THEN 'count'
            WHEN 'BDL' THEN 'count'
            -- Weight
            WHEN 'KG'  THEN 'weight'
            WHEN 'GM'  THEN 'weight'
            WHEN 'MG'  THEN 'weight'
            WHEN 'MT'  THEN 'weight'
            WHEN 'LB'  THEN 'weight'
            WHEN 'OZ'  THEN 'weight'
            -- Volume
            WHEN 'LTR' THEN 'volume'
            WHEN 'ML'  THEN 'volume'
            WHEN 'CBM' THEN 'volume'
            WHEN 'GAL' THEN 'volume'
            -- Length
            WHEN 'MTR' THEN 'length'
            WHEN 'CM'  THEN 'length'
            WHEN 'MM'  THEN 'length'
            WHEN 'KM'  THEN 'length'
            WHEN 'IN'  THEN 'length'
            WHEN 'FT'  THEN 'length'
            WHEN 'YD'  THEN 'length'
            -- Area
            WHEN 'SQM' THEN 'area'
            WHEN 'SQF' THEN 'area'
            -- Time
            WHEN 'HR'  THEN 'time'
            WHEN 'DAY' THEN 'time'
            WHEN 'MON' THEN 'time'
            WHEN 'YR'  THEN 'time'
            -- Other
            WHEN 'UNIT' THEN 'other'
            WHEN 'LOT'  THEN 'other'
            WHEN 'PLT'  THEN 'other'
            WHEN 'CNT'  THEN 'other'
            WHEN 'BAG'  THEN 'other'
            WHEN 'DRM'  THEN 'other'
            WHEN 'BTL'  THEN 'other'
        END
        WHERE uom_type IS NULL
          AND deleted_at IS NULL
        """
    )


def downgrade() -> None:
    # Reverting would re-hide standard UOMs from type-filtered pickers; this is
    # intentionally a no-op to avoid data loss.
    pass
