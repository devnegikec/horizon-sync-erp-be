"""add default_accounts table

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2024-01-15 11:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine.reflection import Inspector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create default_accounts table safely"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create table only if it doesn't exist
    if "default_accounts" not in existing_tables:
        op.create_table(
            "default_accounts",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("transaction_type", sa.String(100), nullable=False),
            sa.Column("scenario", sa.String(100), nullable=True),
            sa.Column(
                "account_id",
                UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.UniqueConstraint(
                "organization_id",
                "transaction_type",
                "scenario",
                name="uq_default_accounts_org_type_scenario",
            ),
        )

    # 2. Create indexes safely using native PG "IF NOT EXISTS"
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_default_accounts_transaction_type ON default_accounts (transaction_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_default_accounts_scenario ON default_accounts (scenario)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_default_accounts_organization_id ON default_accounts (organization_id)"
    )


def downgrade() -> None:
    """Drop default_accounts table safely"""
    op.execute("DROP TABLE IF EXISTS default_accounts CASCADE")
