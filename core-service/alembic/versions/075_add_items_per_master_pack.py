"""add items_per_master_pack to item_packaging_units

Revision ID: 075_add_items_per_master_pack
Revises: 074_add_pick_list_case_loose_and_assignment
Create Date: 2026-08-19

Adds:
- ``item_packaging_units.items_per_master_pack`` (Integer, nullable) — number of
  items grouped under a master pack, used to auto-populate the QR block
  "Items per Master Pack" setting.
"""

import sqlalchemy as sa

from alembic import op

from app.alembic_guards import has_column, has_table

# revision identifiers, used by Alembic.
revision = "075_add_items_per_master_pack"
down_revision = "074_add_pick_list_case_loose_and_assignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table("item_packaging_units") and not has_column(
        "item_packaging_units", "items_per_master_pack"
    ):
        op.add_column(
            "item_packaging_units",
            sa.Column("items_per_master_pack", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    if has_table("item_packaging_units") and has_column(
        "item_packaging_units", "items_per_master_pack"
    ):
        op.drop_column("item_packaging_units", "items_per_master_pack")
