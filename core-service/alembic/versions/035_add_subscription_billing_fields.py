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
    conn = op.get_bind()
    from sqlalchemy.engine.reflection import Inspector
    existing = set(Inspector.from_engine(conn).get_table_names())

    # invoicetype is NOT a PostgreSQL enum in this codebase — the Invoice model
    # uses String(50) for invoice_type. Skip the ALTER TYPE entirely.
    # The billingcycle enum is also not needed as a PG enum (model uses String).

    # invoices is created by migration 041 (or create_all) — skip on fresh DB
    if 'invoices' not in existing:
        return

    inspector = Inspector.from_engine(conn)
    existing_cols = {c['name'] for c in inspector.get_columns('invoices')}

    cols_to_add = [
        ('billing_cycle', sa.Column('billing_cycle', sa.String(20), nullable=True)),
        ('subscription_period_start', sa.Column('subscription_period_start', sa.DateTime(timezone=True), nullable=True)),
        ('subscription_period_end', sa.Column('subscription_period_end', sa.DateTime(timezone=True), nullable=True)),
        ('seat_count', sa.Column('seat_count', sa.Integer(), nullable=True)),
        ('credit_usage', sa.Column('credit_usage', sa.Numeric(15, 2), nullable=True)),
    ]

    with op.batch_alter_table('invoices') as batch_op:
        for col_name, col_def in cols_to_add:
            if col_name not in existing_cols:
                batch_op.add_column(col_def)

    existing_indexes = {i['name'] for i in inspector.get_indexes('invoices')}
    if 'ix_invoices_billing_cycle' not in existing_indexes:
        op.create_index('ix_invoices_billing_cycle', 'invoices', ['billing_cycle'])
    if 'ix_invoices_subscription_period' not in existing_indexes:
        op.create_index('ix_invoices_subscription_period', 'invoices',
                        ['subscription_period_start', 'subscription_period_end'])


def downgrade():
    """Remove subscription billing fields from invoices table"""
    conn = op.get_bind()
    from sqlalchemy.engine.reflection import Inspector
    existing = set(Inspector.from_engine(conn).get_table_names())

    if 'invoices' not in existing:
        return

    inspector = Inspector.from_engine(conn)
    existing_indexes = {i['name'] for i in inspector.get_indexes('invoices')}
    if 'ix_invoices_subscription_period' in existing_indexes:
        op.drop_index('ix_invoices_subscription_period', 'invoices')
    if 'ix_invoices_billing_cycle' in existing_indexes:
        op.drop_index('ix_invoices_billing_cycle', 'invoices')

    existing_cols = {c['name'] for c in inspector.get_columns('invoices')}
    with op.batch_alter_table('invoices') as batch_op:
        for col in ['credit_usage', 'seat_count', 'subscription_period_end',
                    'subscription_period_start', 'billing_cycle']:
            if col in existing_cols:
                batch_op.drop_column(col)

    billing_cycle_enum = sa.Enum(name='billingcycle')
    billing_cycle_enum.drop(conn, checkfirst=True)