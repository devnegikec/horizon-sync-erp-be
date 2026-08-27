"""Add qr_code to warehouse_locations

Revision ID: 090_add_qr_code_to_warehouse_locations
Revises: 089_add_inventory_status_to_bin_stock_levels
Create Date: 2026-08-27

The ``WarehouseLocation`` model declares ``qr_code`` (String(5), nullable, unique)
for quick bin lookup, but no migration had created the column — causing
``UndefinedColumn`` errors on the location-tree and 3D-layout endpoints.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_index

revision: str = "090_add_qr_code_to_warehouse_locations"
down_revision: str | Sequence[
    str
] | None = "089_add_inventory_status_to_bin_stock_levels"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_column("warehouse_locations", "qr_code"):
        op.add_column(
            "warehouse_locations",
            sa.Column("qr_code", sa.String(5), nullable=True),
        )
    if not has_index("warehouse_locations", "ix_warehouse_locations_qr_code"):
        op.create_index(
            "ix_warehouse_locations_qr_code",
            "warehouse_locations",
            ["qr_code"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_warehouse_locations_qr_code", table_name="warehouse_locations")
    op.drop_column("warehouse_locations", "qr_code")
