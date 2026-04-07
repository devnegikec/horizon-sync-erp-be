"""Add subscription billing fields to invoice table

Revision ID: 035_add_subscription_billing_fields
Revises: 034_add_admin_portal_tables
Create Date: 2024-12-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '035_add_subscription_billing_fields'
down_revision = '034_add_admin_portal_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add subscription billing fields to invoices table (Task 1B-1)"""
    
    # Update invoice_type enum to include subscription
    # Note: This may need to be adjusted if enum handling differs in PostgreSQL
    try:
        op.execute("ALTER TYPE invoicetype ADD VALUE 'subscription'")
    except Exception:
        # If enum doesn't exist or value already exists, ignore
        pass
    
    # Add billing_cycle enum type
    billing_cycle_enum = sa.Enum('monthly', 'quarterly', 'yearly', name='billingcycle')
    billing_cycle_enum.create(op.get_bind(), checkfirst=True)
    
    # Add subscription-specific fields to invoices table
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.add_column(sa.Column('billing_cycle', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('subscription_period_start', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('subscription_period_end', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('seat_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('credit_usage', sa.Numeric(15, 2), nullable=True))
    
    # Add indexes for subscription billing queries
    op.create_index('ix_invoices_billing_cycle', 'invoices', ['billing_cycle'])
    op.create_index('ix_invoices_subscription_period', 'invoices', ['subscription_period_start', 'subscription_period_end'])


def downgrade():
    """Remove subscription billing fields from invoices table"""
    
    # Drop indexes
    op.drop_index('ix_invoices_subscription_period', 'invoices')
    op.drop_index('ix_invoices_billing_cycle', 'invoices')
    
    # Remove subscription-specific fields from invoices table
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_column('credit_usage')
        batch_op.drop_column('seat_count')
        batch_op.drop_column('subscription_period_end')
        batch_op.drop_column('subscription_period_start')
        batch_op.drop_column('billing_cycle')
    
    # Drop billing_cycle enum type
    billing_cycle_enum = sa.Enum(name='billingcycle')
    billing_cycle_enum.drop(op.get_bind(), checkfirst=True)