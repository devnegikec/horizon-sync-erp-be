"""Add quotation-level (total) discount columns

Revision ID: 011
Revises: 010_merge
Create Date: 2026-02-24

Document-level discount: type (flat | percentage), value, and computed discount_amount.
grand_total = sum(line total_amount) - discount_amount.
"""

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("quotations")]

    if "discount_type" not in columns:
        op.add_column(
            "quotations",
            sa.Column("discount_type", sa.String(20), nullable=True, server_default="percentage"),
        )
    if "discount_value" not in columns:
        op.add_column(
            "quotations",
            sa.Column("discount_value", sa.Numeric(15, 2), nullable=True, server_default="0"),
        )
    if "discount_amount" not in columns:
        op.add_column(
            "quotations",
            sa.Column("discount_amount", sa.Numeric(15, 2), nullable=True, server_default="0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("quotations")]
    for col_name in ("discount_amount", "discount_value", "discount_type"):
        if col_name in columns:
            op.drop_column("quotations", col_name)
