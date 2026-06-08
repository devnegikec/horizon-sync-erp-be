"""add tax exemption columns to customers

Revision ID: 058_add_customer_tax_exemption_columns
Revises: 057_reconcile_schema_with_models
Create Date: 2026-06-08 12:30:00.000000

Adds the tax-exemption fields described in the tax-and-charges design spec to
the ``customers`` table:

- ``is_tax_exempt`` (BOOLEAN, NOT NULL, default false)
- ``tax_exemption_certificate_no`` (VARCHAR(100), nullable)

The columns are added with ``IF NOT EXISTS`` so this migration is idempotent
and safe to run against databases that already have them (e.g. ones brought
in line by the 057 reconciliation migration).
"""
import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "058_add_customer_tax_exemption_columns"
down_revision = "057_reconcile_schema_with_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if not inspector.has_table("customers"):
        return

    conn.execute(
        sa.text(
            'ALTER TABLE customers '
            'ADD COLUMN IF NOT EXISTS is_tax_exempt BOOLEAN NOT NULL DEFAULT false'
        )
    )
    conn.execute(
        sa.text(
            'ALTER TABLE customers '
            'ADD COLUMN IF NOT EXISTS tax_exemption_certificate_no VARCHAR(100)'
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("ALTER TABLE customers DROP COLUMN IF EXISTS tax_exemption_certificate_no")
    )
    conn.execute(
        sa.text("ALTER TABLE customers DROP COLUMN IF EXISTS is_tax_exempt")
    )
