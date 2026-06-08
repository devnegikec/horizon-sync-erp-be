"""Add warehouse_locations table for bin-level storage hierarchy

Revision ID: 042_add_warehouse_locations_table
Revises: 041_create_core_tables_baseline
Create Date: 2025-06-15

Creates the warehouse_locations table with full hierarchy support
(Zone → Aisle → Bay → Level → Bin), capacity tracking, and optimistic locking.
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "042_add_warehouse_locations_table"
down_revision = "041_create_core_tables_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    conn = op.get_bind()

    # Drop existing table if it exists (handles schema mismatches from prior model-based creation)
    conn.execute(sa.text("DROP TABLE IF EXISTS warehouse_locations CASCADE"))

    op.create_table(
        "warehouse_locations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "warehouse_id",
            UUID(as_uuid=True),
            sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_location_id",
            UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("location_type", sa.String(20), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("full_path", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "capacity",
            sa.Numeric(15, 3),
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_capacity",
            sa.Numeric(15, 3),
            server_default=sa.text("0"),
        ),
        sa.Column(
            "available_capacity",
            sa.Numeric(15, 3),
            server_default=sa.text("0"),
        ),
        sa.Column("capacity_uom", sa.String(50), nullable=True),
        sa.Column(
            "position_x",
            sa.Numeric(10, 2),
            server_default=sa.text("0"),
        ),
        sa.Column(
            "position_y",
            sa.Numeric(10, 2),
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        # CHECK constraint for location_type enum values
        sa.CheckConstraint(
            "location_type IN ('zone', 'aisle', 'bay', 'level', 'bin')",
            name="chk_location_type",
        ),
    )

    # Indexes
    op.create_index("idx_wl_org", "warehouse_locations", ["organization_id"])
    op.create_index("idx_wl_warehouse", "warehouse_locations", ["warehouse_id"])
    op.create_index("idx_wl_parent", "warehouse_locations", ["parent_location_id"])
    op.create_index("idx_wl_type", "warehouse_locations", ["location_type"])
    op.create_index("idx_wl_active", "warehouse_locations", ["is_active"])
    op.create_index("idx_wl_full_path", "warehouse_locations", ["full_path"])
    op.create_index(
        "idx_wl_warehouse_path",
        "warehouse_locations",
        ["warehouse_id", "full_path"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_wl_warehouse_path", table_name="warehouse_locations")
    op.drop_index("idx_wl_full_path", table_name="warehouse_locations")
    op.drop_index("idx_wl_active", table_name="warehouse_locations")
    op.drop_index("idx_wl_type", table_name="warehouse_locations")
    op.drop_index("idx_wl_parent", table_name="warehouse_locations")
    op.drop_index("idx_wl_warehouse", table_name="warehouse_locations")
    op.drop_index("idx_wl_org", table_name="warehouse_locations")
    op.drop_table("warehouse_locations")
