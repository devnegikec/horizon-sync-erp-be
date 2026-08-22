"""add assigned_to to pick_lists and case/loose columns to pick_list_items

Revision ID: 074_add_pick_list_case_loose_and_assignment
Revises: 073_add_missing_pick_list_item_columns
Create Date: 2026-08-18

Adds:
- ``pick_lists.assigned_to`` (UUID, nullable) — worker assigned to the pick list.
- ``pick_list_items.per_case_qty`` (Numeric, nullable) — pieces per case/box.
- ``pick_list_items.case_qty`` (Numeric, nullable) — number of cases/boxes to pick.
- ``pick_list_items.loose_qty`` (Numeric, nullable) — loose pieces to pick.

These support the packing-slip import (case + loose coexist per SKU) and
worker assignment for pick lists.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

# revision identifiers, used by Alembic.
revision = "074_add_pick_list_case_loose_and_assignment"
down_revision = "073_add_missing_pick_list_item_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table("pick_lists") and not has_column("pick_lists", "assigned_to"):
        op.add_column(
            "pick_lists",
            sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        )

    if has_table("pick_list_items"):
        if not has_column("pick_list_items", "per_case_qty"):
            op.add_column(
                "pick_list_items",
                sa.Column("per_case_qty", sa.Numeric(15, 3), nullable=True),
            )
        if not has_column("pick_list_items", "case_qty"):
            op.add_column(
                "pick_list_items",
                sa.Column("case_qty", sa.Numeric(15, 3), nullable=True),
            )
        if not has_column("pick_list_items", "loose_qty"):
            op.add_column(
                "pick_list_items",
                sa.Column("loose_qty", sa.Numeric(15, 3), nullable=True),
            )


def downgrade() -> None:
    if has_table("pick_lists") and has_column("pick_lists", "assigned_to"):
        op.drop_column("pick_lists", "assigned_to")

    if has_table("pick_list_items"):
        for column in ("loose_qty", "case_qty", "per_case_qty"):
            if has_column("pick_list_items", column):
                op.drop_column("pick_list_items", column)
