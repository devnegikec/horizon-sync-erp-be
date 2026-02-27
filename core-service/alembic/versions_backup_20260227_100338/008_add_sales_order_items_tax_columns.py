"""Add tax columns to sales_order_items table

Revision ID: 008
Revises: 007
Create Date: 2026-02-17

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("sales_order_items")]

    if "tax_template_id" not in columns:
        op.add_column(
            "sales_order_items",
            sa.Column(
                "tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "sales_order_items_tax_template_id_fkey",
            "sales_order_items",
            "tax_templates",
            ["tax_template_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if "tax_rate" not in columns:
        op.add_column(
            "sales_order_items",
            sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True, server_default="0"),
        )

    if "tax_amount" not in columns:
        op.add_column(
            "sales_order_items",
            sa.Column(
                "tax_amount", sa.Numeric(15, 2), nullable=True, server_default="0"
            ),
        )

    if "total_amount" not in columns:
        op.add_column(
            "sales_order_items",
            sa.Column(
                "total_amount",
                sa.Numeric(15, 2),
                nullable=True,
            ),
        )
        # Backfill: total_amount = amount for existing rows
        op.execute(
            "UPDATE sales_order_items SET total_amount = amount WHERE total_amount IS NULL"
        )
        op.alter_column(
            "sales_order_items",
            "total_amount",
            existing_type=sa.Numeric(15, 2),
            nullable=False,
            server_default=sa.text("0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("sales_order_items")]

    if "total_amount" in columns:
        op.drop_column("sales_order_items", "total_amount")

    if "tax_amount" in columns:
        op.drop_column("sales_order_items", "tax_amount")

    if "tax_rate" in columns:
        op.drop_column("sales_order_items", "tax_rate")

    if "tax_template_id" in columns:
        op.drop_constraint(
            "sales_order_items_tax_template_id_fkey",
            "sales_order_items",
            type_="foreignkey",
        )
        op.drop_column("sales_order_items", "tax_template_id")
