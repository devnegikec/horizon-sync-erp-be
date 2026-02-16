"""add_accounts_table_for_chart_of_accounts

Revision ID: 610526d12875
Revises: 001_core_db_initialization
Create Date: 2026-02-17 00:33:50.272217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '610526d12875'
down_revision: Union[str, None] = '001_core_db_initialization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create AccountType enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE accounttype AS ENUM (
                'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create AccountStatus enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE accountstatus AS ENUM (
                'ACTIVE', 'INACTIVE', 'ARCHIVED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create accounts table using raw SQL
    op.execute("""
        CREATE TABLE accounts (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL,
            account_code VARCHAR(50) NOT NULL,
            account_name VARCHAR(200) NOT NULL,
            account_type accounttype NOT NULL,
            parent_account_id UUID,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            status accountstatus NOT NULL DEFAULT 'ACTIVE',
            is_posting_account BOOLEAN NOT NULL DEFAULT true,
            description TEXT,
            created_by VARCHAR(100) NOT NULL,
            updated_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_accounts_parent_account_id FOREIGN KEY (parent_account_id) REFERENCES accounts(id)
        )
    """)
    
    # Create indexes
    op.create_index('ix_accounts_organization_id', 'accounts', ['organization_id'])
    op.create_index('ix_accounts_account_code', 'accounts', ['account_code'])
    op.create_index('ix_accounts_account_type', 'accounts', ['account_type'])
    op.create_index('ix_accounts_parent_account_id', 'accounts', ['parent_account_id'])
    op.create_index('ix_accounts_status', 'accounts', ['status'])
    
    # Create composite unique constraint for organization_id + account_code
    op.create_unique_constraint(
        'uq_accounts_organization_account_code',
        'accounts',
        ['organization_id', 'account_code']
    )


def downgrade() -> None:
    # Drop accounts table
    op.drop_table('accounts')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS accountstatus')
    op.execute('DROP TYPE IF EXISTS accounttype')
