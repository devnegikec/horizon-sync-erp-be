"""Add master-carton estimation knobs to item_packaging_units.

Persists the MC outer-dimension estimation parameters (fill factor, void fill
%, wall thickness) so they can be surfaced in the item API response and edited
per master carton. Existing non-base (master carton) rows are backfilled with
the same defaults the item schema uses.

Revision ID: 120_add_master_carton_estimation_fields
Revises: 119_add_packaging_unit_tracking
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.alembic_guards import has_column, has_table

revision: str = "120_add_master_carton_estimation_fields"
down_revision: str | Sequence[str] | None = "119_add_packaging_unit_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("item_packaging_units"):
        return

    if not has_column("item_packaging_units", "master_pack_fill_factor"):
        op.add_column(
            "item_packaging_units",
            sa.Column("master_pack_fill_factor", sa.Numeric(10, 6), nullable=True),
        )
    if not has_column("item_packaging_units", "master_pack_void_fill_pct"):
        op.add_column(
            "item_packaging_units",
            sa.Column("master_pack_void_fill_pct", sa.Numeric(10, 6), nullable=True),
        )
    if not has_column("item_packaging_units", "master_pack_wall_thickness_mm"):
        op.add_column(
            "item_packaging_units",
            sa.Column(
                "master_pack_wall_thickness_mm", sa.Numeric(10, 2), nullable=True
            ),
        )

    # Backfill existing master-carton (non-base) rows with schema defaults so
    # the UI shows values instead of nulls.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE item_packaging_units
            SET master_pack_fill_factor = 0.75,
                master_pack_void_fill_pct = 0.10,
                master_pack_wall_thickness_mm = 3
            WHERE is_base_unit = false
              AND master_pack_fill_factor IS NULL
            """
        )
    )


def downgrade() -> None:
    if not has_table("item_packaging_units"):
        return

    for column in (
        "master_pack_wall_thickness_mm",
        "master_pack_void_fill_pct",
        "master_pack_fill_factor",
    ):
        if has_column("item_packaging_units", column):
            op.drop_column("item_packaging_units", column)
