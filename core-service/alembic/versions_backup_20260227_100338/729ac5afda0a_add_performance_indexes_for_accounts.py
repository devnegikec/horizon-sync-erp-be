"""add_performance_indexes_for_accounts

Revision ID: 729ac5afda0a
Revises: e5f6g7h8i9j0
Create Date: 2026-02-18 14:33:51.426216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '729ac5afda0a'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index for organization_id + parent_account_id (for hierarchy queries)
    op.create_index(
        'idx_accounts_org_parent',
        'accounts',
        ['organization_id', 'parent_account_id'],
        unique=False
    )
    
    # Add composite index for organization_id + status (for filtering active accounts)
    op.create_index(
        'idx_accounts_org_status',
        'accounts',
        ['organization_id', 'status'],
        unique=False
    )
    
    # Add composite index for organization_id + account_type (for type-based queries)
    op.create_index(
        'idx_accounts_org_type',
        'accounts',
        ['organization_id', 'account_type'],
        unique=False
    )
    
    # Add composite index for organization_id + currency (for currency filtering)
    op.create_index(
        'idx_accounts_org_currency',
        'accounts',
        ['organization_id', 'currency'],
        unique=False
    )
    
    # Add index on created_at for sorting by creation date
    op.create_index(
        'idx_accounts_created_at',
        'accounts',
        ['created_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('idx_accounts_created_at', table_name='accounts')
    op.drop_index('idx_accounts_org_currency', table_name='accounts')
    op.drop_index('idx_accounts_org_type', table_name='accounts')
    op.drop_index('idx_accounts_org_status', table_name='accounts')
    op.drop_index('idx_accounts_org_parent', table_name='accounts')
