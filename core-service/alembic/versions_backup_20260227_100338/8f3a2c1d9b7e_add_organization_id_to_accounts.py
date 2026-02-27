"""add_organization_id_to_accounts

Revision ID: 8f3a2c1d9b7e
Revises: 610526d12875
Create Date: 2026-02-17 16:35:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8f3a2c1d9b7e"
down_revision: Union[str, None] = "610526d12875"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE accounts
        ADD COLUMN IF NOT EXISTS organization_id UUID
        """
    )

    op.execute(
        """
        UPDATE accounts
        SET organization_id = '00000000-0000-0000-0000-000000000000'
        WHERE organization_id IS NULL
        """
    )

    op.execute(
        """
        ALTER TABLE accounts
        ALTER COLUMN organization_id SET NOT NULL
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_accounts_organization_id
        ON accounts (organization_id)
        """
    )

    op.execute(
        """
        ALTER TABLE accounts
        DROP CONSTRAINT IF EXISTS uq_accounts_account_code
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_accounts_organization_account_code'
            ) THEN
                ALTER TABLE accounts
                ADD CONSTRAINT uq_accounts_organization_account_code
                UNIQUE (organization_id, account_code);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE accounts
        DROP CONSTRAINT IF EXISTS uq_accounts_organization_account_code
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_accounts_account_code'
            ) THEN
                ALTER TABLE accounts
                ADD CONSTRAINT uq_accounts_account_code UNIQUE (account_code);
            END IF;
        END $$;
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_accounts_organization_id")

    op.execute(
        """
        ALTER TABLE accounts
        DROP COLUMN IF EXISTS organization_id
        """
    )
