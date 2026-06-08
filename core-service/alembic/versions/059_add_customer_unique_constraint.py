"""add unique constraint on customers(organization_id, customer_code)

Revision ID: 059_add_customer_unique_constraint
Revises: 058_add_customer_tax_exemption_columns
Create Date: 2026-06-08 12:45:00.000000

Migration 041 created a non-unique index ``ix_customers_code`` on
customers(organization_id, customer_code) during the baseline setup.
This migration replaces that with a proper UNIQUE constraint so the table
can participate in ``ON CONFLICT`` UPSERT statements.

The non-unique index is dropped first (it is redundant once the unique
constraint exists). If the constraint already exists, the migration is a no-op.
"""
import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "059_add_customer_unique_constraint"
down_revision = "058_add_customer_tax_exemption_columns"
branch_labels = None
depends_on = None


def _constraint_exists(inspector, table: str, name: str) -> bool:
    unique_constraints = inspector.get_unique_constraints(table)
    if any(uc["name"] == name for uc in unique_constraints):
        return True
    # A unique constraint is backed by a unique index; also check indexes
    # in case it was created as a bare unique index.
    indexes = inspector.get_indexes(table)
    return any(ix["name"] == name and ix.get("unique") for ix in indexes)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if not inspector.has_table("customers"):
        return

    # The non-unique index created in 041 is redundant once the unique
    # constraint exists. Drop it first so PostgreSQL doesn't keep two
    # indexes on the same columns.
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_customers_code"))

    if _constraint_exists(inspector, "customers", "uq_customers_org_code"):
        return

    conn.execute(
        sa.text(
            "ALTER TABLE customers ADD CONSTRAINT uq_customers_org_code "
            "UNIQUE (organization_id, customer_code)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("ALTER TABLE customers DROP CONSTRAINT IF EXISTS uq_customers_org_code")
    )
