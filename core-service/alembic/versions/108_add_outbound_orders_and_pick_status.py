"""Add outbound orders and extend pick list status lifecycle.

Creates the upstream outbound order tables (outbound_orders and
outbound_order_items) so imported ASN/SAP order files become orders rather
than pick lists, and extends the ``pickliststatus`` enum with the new
order-driven lifecycle values.

Revision ID: 108_add_outbound_orders_and_pick_status
Revises: 107_warehouse_total_capacity_numeric
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "108_add_outbound_orders_and_pick_status"
down_revision: str | Sequence[str] | None = "107_warehouse_total_capacity_numeric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PICKLIST_STATUSES = [
    "confirmed",
    "pending_picking",
    "pick_complete",
    "ready_for_dispatch",
    "in_transit",
    "delivered",
]


def _create_enum_if_not_exists(conn, name: str, values: list[str]) -> None:
    """Create a postgres enum type if it doesn't already exist."""
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": name},
    ).scalar()
    if not exists:
        conn.execute(sa.text(f"CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in values)})"))


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Extend the existing pickliststatus enum (idempotent).
    for value in NEW_PICKLIST_STATUSES:
        conn.execute(
            sa.text(f"ALTER TYPE pickliststatus ADD VALUE IF NOT EXISTS '{value}'")
        )

    # 2) Create the new outbound order enum types.
    _create_enum_if_not_exists(conn, "outboundordertype", ["asn", "sap"])
    _create_enum_if_not_exists(
        conn,
        "outboundorderstatus",
        ["draft", "confirmed", "pending_picking", "completed", "cancelled"],
    )
    _create_enum_if_not_exists(
        conn,
        "outboundorderitemstockstatus",
        ["in_stock", "out_of_stock"],
    )

    # 3) Create outbound_orders.
    op.create_table(
        "outbound_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("order_no", sa.String(100), nullable=False),
        sa.Column(
            "order_type",
            postgresql.ENUM(
                "asn", "sap", name="outboundordertype", create_type=False
            ),
            nullable=False,
            server_default="sap",
        ),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "confirmed",
                "pending_picking",
                "completed",
                "cancelled",
                name="outboundorderstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("invoice_reference", sa.String(255), nullable=True),
        sa.Column("source_filename", sa.String(255), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
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
        "ix_outbound_orders_organization_id",
        "outbound_orders",
        ["organization_id"],
    )
    op.create_index(
        "ix_outbound_orders_warehouse_id",
        "outbound_orders",
        ["warehouse_id"],
    )

    # 4) Create outbound_order_items.
    op.create_table(
        "outbound_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "outbound_order_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("uom", sa.String(50), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("per_case_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("case_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("loose_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("batch_no", sa.String(100), nullable=True),
        sa.Column(
            "stock_status",
            postgresql.ENUM(
                "in_stock",
                "out_of_stock",
                name="outboundorderitemstockstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="out_of_stock",
        ),
        sa.Column("available_qty", sa.Numeric(15, 3), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
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
            ["outbound_order_id"], ["outbound_orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["warehouse_id"], ["warehouses_extended.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbound_order_items_organization_id",
        "outbound_order_items",
        ["organization_id"],
    )
    op.create_index(
        "ix_outbound_order_items_outbound_order_id",
        "outbound_order_items",
        ["outbound_order_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbound_order_items_outbound_order_id",
        table_name="outbound_order_items",
    )
    op.drop_index(
        "ix_outbound_order_items_organization_id",
        table_name="outbound_order_items",
    )
    op.drop_table("outbound_order_items")
    op.drop_index(
        "ix_outbound_orders_warehouse_id", table_name="outbound_orders"
    )
    op.drop_index(
        "ix_outbound_orders_organization_id", table_name="outbound_orders"
    )
    op.drop_table("outbound_orders")

    # Enum values are intentionally not removed on downgrade: removing an enum
    # value in postgres requires dropping/recreating the type and rewrites all
    # referencing columns, which is unsafe for a reversible rollback.
    op.execute("DROP TYPE IF EXISTS outboundorderitemstockstatus")
    op.execute("DROP TYPE IF EXISTS outboundorderstatus")
    op.execute("DROP TYPE IF EXISTS outboundordertype")
