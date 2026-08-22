"""add missing columns to pick_list_items

Revision ID: 073_add_missing_pick_list_item_columns
Revises: 072_add_bin_capacity_columns
Create Date: 2026-08-18

The PickListItem model (app/models/pick_list.py) declares ``extra_data``,
``created_at`` and ``updated_at`` columns, but they were never added by the
migrations that created/extended the ``pick_list_items`` table (045 created
it without them; 047 only added ``bin_location_id``). This migration adds
them so pick list creation no longer fails with
``UndefinedColumn: column "extra_data" does not exist``.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

from app.alembic_guards import has_column, has_table

# revision identifiers, used by Alembic.
revision = "073_add_missing_pick_list_item_columns"
down_revision = "072_add_bin_capacity_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table("pick_list_items"):
        return

    if not has_column("pick_list_items", "extra_data"):
        op.add_column(
            "pick_list_items", sa.Column("extra_data", postgresql.JSONB(), nullable=True)
        )
    if not has_column("pick_list_items", "created_at"):
        op.add_column(
            "pick_list_items",
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not has_column("pick_list_items", "updated_at"):
        op.add_column(
            "pick_list_items",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if not has_table("pick_list_items"):
        return
    for column in ("updated_at", "created_at", "extra_data"):
        if has_column("pick_list_items", column):
            op.drop_column("pick_list_items", column)
