"""Include ``inventory_status`` in the ``bin_stock_levels`` uniqueness key.

``uq_bin_item_batch`` allowed only one row per (bin, item, batch), so a single
row had to carry one ``inventory_status``. Adding segregated stock
(HOLD / QUARANTINE / DAMAGED) to a row that already held available stock
therefore re-statused every unit in it, silently locking or releasing stock
nobody had touched — and the reverse on the way back.

Rows are now keyed by (bin, item, batch, inventory_status) so each status is
tracked independently.

Safe on existing data: the old key is a strict subset of the new one, so no
duplicates can appear and ``uq_bin_item_batch_status`` cannot fail to build.

Revision ID: 125_bin_stock_status_unique
Revises: 124_returns_module
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_constraint, has_table

revision: str = "125_bin_stock_status_unique"
down_revision: str | Sequence[str] | None = "124_returns_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "bin_stock_levels"
OLD_CONSTRAINT = "uq_bin_item_batch"
NEW_CONSTRAINT = "uq_bin_item_batch_status"
NEW_COLUMNS = ["bin_location_id", "item_id", "batch_number", "inventory_status"]


def upgrade() -> None:
    if not has_table(TABLE):
        return

    # Migration 089 added the column NOT NULL DEFAULT 'available', so this is a
    # defensive sweep for rows that arrived out-of-band and would otherwise sit
    # outside the new key.
    op.execute(
        sa.text(
            f"UPDATE {TABLE} SET inventory_status = 'available' "
            "WHERE inventory_status IS NULL OR inventory_status = ''"
        )
    )

    if has_constraint(TABLE, OLD_CONSTRAINT):
        op.drop_constraint(OLD_CONSTRAINT, TABLE, type_="unique")
    if not has_constraint(TABLE, NEW_CONSTRAINT):
        op.create_unique_constraint(NEW_CONSTRAINT, TABLE, NEW_COLUMNS)


def downgrade() -> None:
    """Restore the (bin, item, batch) key — only while the data still fits it.

    The split is lossless going up but not going down: once two statuses hold
    stock for the same bin/item/batch there is no single row to merge them back
    into. Rather than silently picking one status and discarding the other,
    refuse and report the offending groups so they can be consolidated
    deliberately.
    """
    if not has_table(TABLE):
        return

    collisions = (
        op.get_bind()
        .execute(
            sa.text(
                f"""
                SELECT count(*) FROM (
                    SELECT 1 FROM {TABLE}
                     GROUP BY bin_location_id, item_id, batch_number
                    HAVING count(*) > 1
                ) AS duplicate_groups
                """
            )
        )
        .scalar()
    ) or 0

    if collisions:
        raise RuntimeError(
            f"Cannot restore {OLD_CONSTRAINT}: {collisions} (bin, item, batch) "
            "group(s) now hold stock in more than one inventory_status. "
            "Consolidate them first, then re-run the downgrade."
        )

    if has_constraint(TABLE, NEW_CONSTRAINT):
        op.drop_constraint(NEW_CONSTRAINT, TABLE, type_="unique")
    if not has_constraint(TABLE, OLD_CONSTRAINT):
        op.create_unique_constraint(OLD_CONSTRAINT, TABLE, NEW_COLUMNS[:3])
