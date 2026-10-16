"""Add the legacy string UOM cache used by the item-group ORM model.

Revision ID: 118_add_item_group_default_uom_cache
Revises: 117_add_missing_item_group_columns
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.alembic_guards import has_column, has_table

revision: str = "118_add_item_group_default_uom_cache"
down_revision: str | Sequence[str] | None = "117_add_missing_item_group_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("item_groups") and not has_column("item_groups", "default_uom"):
        op.add_column(
            "item_groups",
            sa.Column("default_uom", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    if has_column("item_groups", "default_uom"):
        op.drop_column("item_groups", "default_uom")
