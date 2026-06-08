"""Add new B2B billing invoice types

Task 1F-1: Add support for setup fee, overage, addon, and credit adjustment invoice types
for the B2B billing system API endpoints.

Revision ID: 037
Revises: 036
Create Date: 2026-03-27 16:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = '037_add_b2b_billing_invoice_types'
down_revision = '036_add_payment_reminder_system'
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    """Add new B2B billing invoice types"""
    # invoicetype is NOT a PostgreSQL enum in this codebase — the Invoice model
    # uses String(50) for invoice_type. These values are enforced at the
    # application layer via the InvoiceType Python enum in base.py.
    # Nothing to do at the DB level.
    pass


def downgrade():
    """Remove B2B billing invoice types
    
    Note: PostgreSQL doesn't support removing enum values directly.
    In production, a more complex migration would be needed to:
    1. Create new enum without the values
    2. Update all references
    3. Drop old enum and rename new enum
    
    For development purposes, this is acceptable.
    """
    pass  # Cannot easily remove enum values in PostgreSQL