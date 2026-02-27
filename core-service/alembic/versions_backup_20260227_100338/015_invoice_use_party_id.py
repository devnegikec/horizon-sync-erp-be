"""Use party_id on invoices; drop customer_id and supplier_id

Revision ID: 015_invoice_party_id
Revises: 014_invoice_party
Create Date: 2026-02-25

DB uses a single party_id (customer or supplier by invoice_type). Revert
customer_id/supplier_id from 014 and ensure party_id exists.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "015_invoice_party_id"
down_revision = "014_invoice_party"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("invoices")]

    # Ensure party_id exists (add if missing)
    if "party_id" not in columns:
        op.add_column(
            "invoices",
            sa.Column(
                "party_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        columns = [col["name"] for col in inspector.get_columns("invoices")]

    # Migrate data: copy customer_id/supplier_id into party_id where party_id is null
    if "customer_id" in columns and "supplier_id" in columns:
        op.execute(
            sa.text("""
                UPDATE invoices
                SET party_id = COALESCE(party_id, customer_id)
                WHERE UPPER(invoice_type::text) = 'SALES' AND customer_id IS NOT NULL
            """)
        )
        op.execute(
            sa.text("""
                UPDATE invoices
                SET party_id = COALESCE(party_id, supplier_id)
                WHERE UPPER(invoice_type::text) = 'PURCHASE' AND supplier_id IS NOT NULL
            """)
        )

    # Drop customer_id and supplier_id if present
    for col_name in ("supplier_id", "customer_id"):
        if col_name in columns:
            op.drop_column("invoices", col_name)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("invoices")]

    # Re-add customer_id and supplier_id
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

    # Backfill from party_id
    if "party_id" in columns:
        op.execute(
            sa.text("""
                UPDATE invoices
                SET customer_id = party_id
                WHERE UPPER(invoice_type::text) = 'SALES' AND party_id IS NOT NULL
            """)
        )
        op.execute(
            sa.text("""
                UPDATE invoices
                SET supplier_id = party_id
                WHERE UPPER(invoice_type::text) = 'PURCHASE' AND party_id IS NOT NULL
            """)
        )

    # Drop party_id
    if "party_id" in columns:
        op.drop_column("invoices", "party_id")
