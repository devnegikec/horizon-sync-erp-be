"""Add put_away_list_items.serial_nos for master-pack serial grouping.

Put-away lines generated for serialized items are grouped by the item's
``items_per_master_pack``; the unit serials in each master pack are stored on
``put_away_list_items.serial_nos``.

Revision ID: 115_put_away_item_serial_nos
Revises: 114_remove_receiving_stage_bins
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

from app.alembic_guards import has_column, has_table

revision: str = "115_put_away_item_serial_nos"
down_revision: str | Sequence[str] | None = "114_remove_receiving_stage_bins"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("put_away_list_items") and not has_column(
        "put_away_list_items", "serial_nos"
    ):
        op.add_column(
            "put_away_list_items",
            sa.Column("serial_nos", postgresql.JSONB(), nullable=True),
        )


def downgrade() -> None:
    if has_column("put_away_list_items", "serial_nos"):
        op.drop_column("put_away_list_items", "serial_nos")
