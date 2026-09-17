"""Rename stock_levels.product_id -> item_id.

Revision ID: 080_rename_stock_levels_product_id
Revises: 079_packaging_types

The column already references ``items.id``; only its name was misleading.
The SQLAlchemy model keeps the attribute name ``product_id`` mapped to the
renamed column for backward compatibility (see ``app/models/stock_level.py``).
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint

revision: str = "080_rename_stock_levels_product_id"
down_revision: str | Sequence[str] | None = "079_packaging_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_constraint("stock_levels", "uq_stock_levels_product_warehouse"):
        op.drop_constraint("uq_stock_levels_product_warehouse", "stock_levels", type_="unique")

    if has_column("stock_levels", "product_id"):
        op.alter_column(
            "stock_levels",
            "product_id",
            new_column_name="item_id",
            existing_type=postgresql.UUID(as_uuid=True),
        )

    if not has_constraint("stock_levels", "uq_stock_levels_item_warehouse"):
        op.create_unique_constraint(
            "uq_stock_levels_item_warehouse", "stock_levels", ["item_id", "warehouse_id"]
        )


def downgrade() -> None:
    if has_constraint("stock_levels", "uq_stock_levels_item_warehouse"):
        op.drop_constraint("uq_stock_levels_item_warehouse", "stock_levels", type_="unique")

    if has_column("stock_levels", "item_id"):
        op.alter_column(
            "stock_levels",
            "item_id",
            new_column_name="product_id",
            existing_type=postgresql.UUID(as_uuid=True),
        )

    if not has_constraint("stock_levels", "uq_stock_levels_product_warehouse"):
        op.create_unique_constraint(
            "uq_stock_levels_product_warehouse", "stock_levels", ["product_id", "warehouse_id"]
        )
