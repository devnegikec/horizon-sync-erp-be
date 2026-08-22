"""add bin capacity planning columns

Revision ID: 072_add_bin_capacity_columns
Revises: 071_add_unique_constraint_items_org_item_code
Create Date: 2026-08-14
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_table

# revision identifiers, used by Alembic.
revision = "072_add_bin_capacity_columns"
down_revision = "071_add_unique_constraint_items_org_item_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # warehouses_extended: dimension toggles + threshold defaults
    if has_table("warehouses_extended"):
        for name, type_, default in [
            ("use_volume", sa.Boolean(), "true"),
            ("use_weight", sa.Boolean(), "false"),
            ("full_threshold_pct", sa.Numeric(5, 3), "0.90"),
            ("almost_full_threshold_pct", sa.Numeric(5, 3), "0.70"),
        ]:
            if not has_column("warehouses_extended", name):
                op.add_column(
                    "warehouses_extended",
                    sa.Column(name, type_, nullable=False, server_default=default),
                )

    # warehouse_locations: thresholds (nullable per-bin overrides) + cached state
    if has_table("warehouse_locations"):
        for name, type_, default in [
            ("full_threshold_pct", sa.Numeric(5, 3), None),
            ("almost_full_threshold_pct", sa.Numeric(5, 3), None),
            ("capacity_volume_pct", sa.Numeric(6, 2), None),
            ("capacity_weight_pct", sa.Numeric(6, 2), None),
            ("bin_state", sa.String(20), None),
            ("is_available", sa.Boolean(), "true"),
        ]:
            if not has_column("warehouse_locations", name):
                op.add_column(
                    "warehouse_locations",
                    sa.Column(
                        name,
                        type_,
                        nullable=(default is None),
                        server_default=default,
                    ),
                )


def downgrade() -> None:
    targets = [
        (
            "warehouses_extended",
            [
                "use_volume",
                "use_weight",
                "full_threshold_pct",
                "almost_full_threshold_pct",
            ],
        ),
        (
            "warehouse_locations",
            [
                "full_threshold_pct",
                "almost_full_threshold_pct",
                "capacity_volume_pct",
                "capacity_weight_pct",
                "bin_state",
                "is_available",
            ],
        ),
    ]
    for table, columns in targets:
        if not has_table(table):
            continue
        for name in columns:
            if has_column(table, name):
                op.drop_column(table, name)
