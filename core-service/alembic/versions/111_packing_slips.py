"""Add packing slips and packing slip items.

A packing slip groups picked goods from one or more completed outbound orders
into an internal staging document (many-to-many with orders via item-level
order refs). This adds the ``packing_slips`` and ``packing_slip_items`` tables
and the ``packingslipstatus`` enum.

Revision ID: 111_packing_slips
Revises: 110_unassigned_bin_reservations
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "111_packing_slips"
down_revision: str | Sequence[str] | None = "110_unassigned_bin_reservations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PACKING_SLIP_STATUSES = ["draft", "loading", "dispatched", "cancelled"]


def _create_enum_if_not_exists(conn, name: str, values: list[str]) -> None:
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": name},
    ).scalar()
    if not exists:
        conn.execute(
            sa.text(
                f"CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in values)})"
            )
        )


def upgrade() -> None:
    conn = op.get_bind()

    _create_enum_if_not_exists(conn, "packingslipstatus", PACKING_SLIP_STATUSES)

    op.create_table(
        "packing_slips",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("packing_slip_no", sa.String(100), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                *PACKING_SLIP_STATUSES,
                name="packingslipstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouses_extended.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_packing_slips_organization_id", "packing_slips", ["organization_id"]
    )

    op.create_table(
        "packing_slip_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("packing_slip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pick_list_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("per_case_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("case_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("loose_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("batch_no", sa.String(100), nullable=True),
        sa.Column("serial_nos", postgresql.JSONB(), nullable=True),
        sa.Column("bin_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("handling_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["packing_slip_id"], ["packing_slips.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["bin_location_id"], ["warehouse_locations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["handling_unit_id"], ["handling_units.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_packing_slip_items_organization_id",
        "packing_slip_items",
        ["organization_id"],
    )
    op.create_index("ix_packing_slip_items_order_id", "packing_slip_items", ["order_id"])
    op.create_index(
        "ix_packing_slip_items_pick_list_id", "packing_slip_items", ["pick_list_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_packing_slip_items_pick_list_id", table_name="packing_slip_items")
    op.drop_index("ix_packing_slip_items_order_id", table_name="packing_slip_items")
    op.drop_index(
        "ix_packing_slip_items_organization_id", table_name="packing_slip_items"
    )
    op.drop_table("packing_slip_items")
    op.drop_index("ix_packing_slips_organization_id", table_name="packing_slips")
    op.drop_table("packing_slips")
    op.execute("DROP TYPE IF EXISTS packingslipstatus")
