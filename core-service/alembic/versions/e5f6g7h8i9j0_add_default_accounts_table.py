"""add default_accounts table

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create default_accounts table"""
    op.create_table(
        'default_accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('transaction_type', sa.String(100), nullable=False),
        sa.Column('scenario', sa.String(100), nullable=True),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('organization_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('organization_id', 'transaction_type', 'scenario', name='uq_default_accounts_org_type_scenario'),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_default_accounts_transaction_type', 'default_accounts', ['transaction_type'])
    op.create_index('idx_default_accounts_scenario', 'default_accounts', ['scenario'])
    op.create_index('idx_default_accounts_organization_id', 'default_accounts', ['organization_id'])


def downgrade() -> None:
    """Drop default_accounts table"""
    op.drop_index('idx_default_accounts_organization_id', table_name='default_accounts')
    op.drop_index('idx_default_accounts_scenario', table_name='default_accounts')
    op.drop_index('idx_default_accounts_transaction_type', table_name='default_accounts')
    op.drop_table('default_accounts')
