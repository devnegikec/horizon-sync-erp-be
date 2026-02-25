"""Add invoice document-level discount_type and discount_value

Revision ID: 013_invoice_discount
Revises: 012
Create Date: 2026-02-24

discount_amount already exists; add discount_type and discount_value for UI.
"""

import sqlalchemy as sa
from alembic import op

revision = "013_invoice_discount"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("invoices")]
    if "discount_type" not in columns:
        op.add_column(
            "invoices",
            sa.Column("discount_type", sa.String(20), nullable=True, server_default="percentage"),
        )
    if "discount_value" not in columns:
        op.add_column(
            "invoices",
            sa.Column("discount_value", sa.Numeric(15, 2), nullable=True, server_default="0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("invoices")]
    for col_name in ("discount_value", "discount_type"):
        if col_name in columns:
            op.drop_column("invoices", col_name)
