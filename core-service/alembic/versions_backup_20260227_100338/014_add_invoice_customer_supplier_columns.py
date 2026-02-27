"""Add customer_id and supplier_id to invoices

Revision ID: 014_invoice_party
Revises: 013_invoice_discount
Create Date: 2026-02-25

Some DBs have invoices without customer_id/supplier_id; add if missing.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "014_invoice_party"
down_revision = "013_invoice_discount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("invoices")]
    if "customer_id" not in columns:
        op.add_column(
            "invoices",
            sa.Column(
                "customer_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
    if "supplier_id" not in columns:
        op.add_column(
            "invoices",
            sa.Column(
                "supplier_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("invoices")]
    for col_name in ("supplier_id", "customer_id"):
        if col_name in columns:
            op.drop_column("invoices", col_name)
