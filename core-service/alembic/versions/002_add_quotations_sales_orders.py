"""Add quotations and sales orders tables

Revision ID: 002
Revises: 001
Create Date: 2026-01-26 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get inspector to check if tables exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create enum types
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'quotationstatus') THEN CREATE TYPE quotationstatus AS ENUM ('draft', 'sent', 'accepted', 'rejected', 'expired'); END IF; END$$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'salesorderstatus') THEN CREATE TYPE salesorderstatus AS ENUM ('draft', 'confirmed', 'partially_delivered', 'delivered', 'closed', 'cancelled'); END IF; END$$;"
    )

    # Create quotations table
    if "quotations" not in tables:
        op.create_table(
            "quotations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quotation_no", sa.String(length=100), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quotation_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "draft",
                    "sent",
                    "accepted",
                    "rejected",
                    "expired",
                    name="quotationstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="draft",
            ),
            sa.Column(
                "grand_total",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "currency", sa.String(length=10), nullable=False, server_default="INR"
            ),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["customer_id"],
                ["customers.id"],
                name="quotations_customer_id_fkey",
                ondelete="RESTRICT",
            ),
        )

        # Create indexes for quotations
        op.create_index(
            op.f("ix_quotations_organization_id"),
            "quotations",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_quotations_customer_id"),
            "quotations",
            ["customer_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_quotations_status"),
            "quotations",
            ["status"],
            unique=False,
        )

    # Create quotation_items table
    if "quotation_items" not in tables:
        op.create_table(
            "quotation_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("quotation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("qty", sa.Numeric(precision=15, scale=3), nullable=False),
            sa.Column("uom", sa.String(length=50), nullable=False),
            sa.Column("rate", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["quotation_id"],
                ["quotations.id"],
                name="quotation_items_quotation_id_fkey",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["item_id"],
                ["items.id"],
                name="quotation_items_item_id_fkey",
                ondelete="RESTRICT",
            ),
        )

        # Create indexes for quotation_items
        op.create_index(
            op.f("ix_quotation_items_organization_id"),
            "quotation_items",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_quotation_items_quotation_id"),
            "quotation_items",
            ["quotation_id"],
            unique=False,
        )

    # Create sales_orders table
    if "sales_orders" not in tables:
        op.create_table(
            "sales_orders",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sales_order_no", sa.String(length=100), nullable=False),
            sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "draft",
                    "confirmed",
                    "partially_delivered",
                    "delivered",
                    "closed",
                    "cancelled",
                    name="salesorderstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="draft",
            ),
            sa.Column(
                "grand_total",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "currency", sa.String(length=10), nullable=False, server_default="INR"
            ),
            sa.Column("reference_type", sa.String(length=50), nullable=True),
            sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["customer_id"],
                ["customers.id"],
                name="sales_orders_customer_id_fkey",
                ondelete="RESTRICT",
            ),
        )

        # Create indexes for sales_orders
        op.create_index(
            op.f("ix_sales_orders_organization_id"),
            "sales_orders",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_sales_orders_customer_id"),
            "sales_orders",
            ["customer_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_sales_orders_status"),
            "sales_orders",
            ["status"],
            unique=False,
        )

    # Create sales_order_items table
    if "sales_order_items" not in tables:
        op.create_table(
            "sales_order_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("sales_order_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("qty", sa.Numeric(precision=15, scale=3), nullable=False),
            sa.Column("uom", sa.String(length=50), nullable=False),
            sa.Column("rate", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column(
                "billed_qty",
                sa.Numeric(precision=15, scale=3),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "delivered_qty",
                sa.Numeric(precision=15, scale=3),
                nullable=False,
                server_default="0",
            ),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["sales_order_id"],
                ["sales_orders.id"],
                name="sales_order_items_sales_order_id_fkey",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["item_id"],
                ["items.id"],
                name="sales_order_items_item_id_fkey",
                ondelete="RESTRICT",
            ),
        )

        # Create indexes for sales_order_items
        op.create_index(
            op.f("ix_sales_order_items_organization_id"),
            "sales_order_items",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_sales_order_items_sales_order_id"),
            "sales_order_items",
            ["sales_order_id"],
            unique=False,
        )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("sales_order_items")
    op.drop_table("sales_orders")
    op.drop_table("quotation_items")
    op.drop_table("quotations")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS salesorderstatus")
    op.execute("DROP TYPE IF EXISTS quotationstatus")
