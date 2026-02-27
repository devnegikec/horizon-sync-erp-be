"""Add item-level discount columns (quotation_items, sales_order_items)

Revision ID: 009
Revises: 008
Create Date: 2026-02-24

Item-level discount: type (flat | percentage), value, and computed discount_amount.
Tax is applied on (amount - discount_amount). total_amount = amount - discount_amount + tax_amount.
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def _ensure_discount_columns(conn, table_name: str, inspector) -> None:
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    if "discount_type" not in columns:
        op.add_column(
            table_name,
            sa.Column(
                "discount_type",
                sa.String(20),
                nullable=True,
                server_default="percentage",
            ),
        )
    if "discount_value" not in columns:
        op.add_column(
            table_name,
            sa.Column(
                "discount_value",
                sa.Numeric(15, 2),
                nullable=True,
                server_default="0",
            ),
        )
    if "discount_amount" not in columns:
        op.add_column(
            table_name,
            sa.Column(
                "discount_amount",
                sa.Numeric(15, 2),
                nullable=True,
                server_default="0",
            ),
        )


def _drop_discount_columns(conn, table_name: str, inspector) -> None:
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    for col_name in ("discount_amount", "discount_value", "discount_type"):
        if col_name in columns:
            op.drop_column(table_name, col_name)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    _ensure_discount_columns(conn, "quotation_items", inspector)
    _ensure_discount_columns(conn, "sales_order_items", inspector)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    _drop_discount_columns(conn, "sales_order_items", inspector)
    _drop_discount_columns(conn, "quotation_items", inspector)
