"""add account_balances table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create account_balances table for tracking account balances over time"""
    op.create_table(
        'account_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('debit_total', sa.Numeric(precision=19, scale=4), nullable=False, server_default='0'),
        sa.Column('credit_total', sa.Numeric(precision=19, scale=4), nullable=False, server_default='0'),
        sa.Column('balance', sa.Numeric(precision=19, scale=4), nullable=False, server_default='0'),
        sa.Column('base_currency_balance', sa.Numeric(precision=19, scale=4), nullable=False, server_default='0'),
        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'as_of_date', name='uq_account_balances_account_date')
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_account_balances_account_id', 'account_balances', ['account_id'])
    op.create_index('idx_account_balances_as_of_date', 'account_balances', ['as_of_date'])
    op.create_index('idx_account_balances_account_date', 'account_balances', ['account_id', 'as_of_date'])


def downgrade() -> None:
    """Drop account_balances table"""
    op.drop_index('idx_account_balances_account_date', table_name='account_balances')
    op.drop_index('idx_account_balances_as_of_date', table_name='account_balances')
    op.drop_index('idx_account_balances_account_id', table_name='account_balances')
    op.drop_table('account_balances')
