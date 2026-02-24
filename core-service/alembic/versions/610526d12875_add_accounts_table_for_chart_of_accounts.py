"""add_accounts_table_for_chart_of_accounts

Revision ID: 610526d12875
Revises: 009
Create Date: 2026-02-17 00:33:50.272217

Linear path: 008 -> 009 -> 610526d12875 -> ... -> l2m3n4o5p6q7r8 -> 010_merge -> 011 -> 012
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "610526d12875"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create AccountType enum if it doesn't exist
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE accounttype AS ENUM (
                'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """
    )

    # Create AccountStatus enum if it doesn't exist
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE accountstatus AS ENUM (
                'ACTIVE', 'INACTIVE', 'ARCHIVED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """
    )

    # Create accounts table using raw SQL
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
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
    """
    )

    # Create indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_accounts_organization_id ON accounts (organization_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_accounts_account_code ON accounts (account_code)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_accounts_account_type ON accounts (account_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_accounts_parent_account_id ON accounts (parent_account_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_accounts_status ON accounts (status)")

    # Create composite unique constraint for organization_id + account_code
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_accounts_organization_account_code') THEN
                ALTER TABLE accounts ADD CONSTRAINT uq_accounts_organization_account_code UNIQUE (organization_id, account_code);
            END IF;
        END $$;
    """
    )


def downgrade() -> None:
    # Drop accounts table
    op.drop_table("accounts")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS accountstatus")
    op.execute("DROP TYPE IF EXISTS accounttype")
