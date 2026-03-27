"""Add new B2B billing invoice types

Task 1F-1: Add support for setup fee, overage, addon, and credit adjustment invoice types
for the B2B billing system API endpoints.

Revision ID: 037
Revises: 036
Create Date: 2026-03-27 16:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '037_add_b2b_billing_invoice_types'
down_revision = '036_add_payment_reminder_system'
branch_labels = None
depends_on = None


def upgrade():
    """Add new B2B billing invoice types"""
    
    # Add new invoice type values to existing enum
    # PostgreSQL requires this approach for adding enum values
    op.execute("ALTER TYPE invoicetype ADD VALUE IF NOT EXISTS 'setup_fee'")
    op.execute("ALTER TYPE invoicetype ADD VALUE IF NOT EXISTS 'overage'") 
    op.execute("ALTER TYPE invoicetype ADD VALUE IF NOT EXISTS 'addon'")
    op.execute("ALTER TYPE invoicetype ADD VALUE IF NOT EXISTS 'credit_adjustment'")


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