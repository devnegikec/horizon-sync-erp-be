"""Add inventory_status to bin_stock_levels

Revision ID: 089_add_inventory_status_to_bin_stock_levels
Revises: 088_merge_vehicle_arrival_heads
Create Date: 2026-08-27

Adds a string ``inventory_status`` column to ``bin_stock_levels`` (PR-01 / T-01).
Allowed values: ``available/blocked/damaged/hold/quality/reserved``, default
``available``. Enables excluding non-pickable stock from FEFO/FIFO allocation.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_index

revision: str = "089_add_inventory_status_to_bin_stock_levels"
down_revision: str | Sequence[str] | None = "088_merge_vehicle_arrival_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_column("bin_stock_levels", "inventory_status"):
        op.add_column(
            "bin_stock_levels",
            sa.Column(
                "inventory_status",
                sa.String(20),
                nullable=False,
                server_default="available",
            ),
        )
    if not has_index("bin_stock_levels", "ix_bin_stock_levels_inventory_status"):
        op.create_index(
            "ix_bin_stock_levels_inventory_status",
            "bin_stock_levels",
            ["inventory_status"],
        )


def downgrade() -> None:
    op.drop_index("ix_bin_stock_levels_inventory_status", table_name="bin_stock_levels")
    op.drop_column("bin_stock_levels", "inventory_status")
