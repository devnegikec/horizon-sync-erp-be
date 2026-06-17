"""Add warehouse_floor_plans table for dynamic layout generation

Revision ID: 060_add_warehouse_floor_plans
Revises: 059_add_bin_reservations_expiry_position_z
Create Date: 2026-06-17

Phase 0 of the 3D Warehouse View — Dynamic Layout Designer:
- warehouse_floor_plans: stores zone/aisle/bay configuration used by the
  FloorPlanGeneratorService to auto-generate WarehouseLocation rows with
  correct position_x / position_y / position_z values.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "060_add_warehouse_floor_plans"
down_revision = "059_add_bin_reservations_expiry_position_z"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warehouse_floor_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Serialised FloorPlanConfig (zones → aisles → bays spec)",
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("warehouse_floor_plans")
