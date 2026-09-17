"""Add vehicles, vehicle_arrivals and vehicle_arrival_asns tables.

Revision ID: 076_add_vehicle_arrival_tables
Revises: 075_merge_dev_qseal_heads
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "076_add_vehicle_arrival_tables"
down_revision: str | Sequence[str] | None = "075_merge_dev_qseal_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. vehicles ─────────────────────────────────────────────────────
    op.create_table(
        "vehicles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_no", sa.String(length=100), nullable=False),
        sa.Column("driver_name", sa.String(length=255), nullable=True),
        sa.Column("driver_contact", sa.String(length=50), nullable=True),
        sa.Column("transporter", sa.String(length=255), nullable=True),
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
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "vehicle_no", name="uq_vehicle_org_vehicle_no"
        ),
    )
    op.create_index("ix_vehicles_organization_id", "vehicles", ["organization_id"])

    # ── 2. vehicle_arrivals ─────────────────────────────────────────────
    op.create_table(
        "vehicle_arrivals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses_extended.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dock", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="arrived"
        ),
        sa.Column(
            "arrived_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            nullable=False,
        ),
    )
    op.create_index(
        "ix_vehicle_arrivals_organization_id",
        "vehicle_arrivals",
        ["organization_id"],
    )
    op.create_index(
        "ix_vehicle_arrivals_vehicle_id", "vehicle_arrivals", ["vehicle_id"]
    )

    # ── 3. vehicle_arrival_asns (many-to-many) ──────────────────────────
    op.create_table(
        "vehicle_arrival_asns",
        sa.Column(
            "vehicle_arrival_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_arrivals.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "asn_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asn_orders.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("vehicle_arrival_asns")
    op.drop_index("ix_vehicle_arrivals_vehicle_id", table_name="vehicle_arrivals")
    op.drop_index("ix_vehicle_arrivals_organization_id", table_name="vehicle_arrivals")
    op.drop_table("vehicle_arrivals")
    op.drop_index("ix_vehicles_organization_id", table_name="vehicles")
    op.drop_table("vehicles")
