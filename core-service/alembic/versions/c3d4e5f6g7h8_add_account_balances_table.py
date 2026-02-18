"""add account_balances table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2024-01-15 10:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create table only if it doesn't exist
    if "account_balances" not in existing_tables:
        op.create_table(
            "account_balances",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column(
                "debit_total",
                sa.Numeric(precision=19, scale=4),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "credit_total",
                sa.Numeric(precision=19, scale=4),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "balance",
                sa.Numeric(precision=19, scale=4),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "base_currency_balance",
                sa.Numeric(precision=19, scale=4),
                nullable=False,
                server_default="0",
            ),
            sa.Column("as_of_date", sa.Date(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["account_id"], ["accounts.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "account_id", "as_of_date", name="uq_account_balances_account_date"
            ),
        )

    # 2. Create indexes safely using native PG "IF NOT EXISTS"
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_balances_account_id ON account_balances (account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_balances_as_of_date ON account_balances (as_of_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_balances_account_date ON account_balances (account_id, as_of_date)"
    )


def downgrade() -> None:
    # Drop table safely (CASCADE handles indexes and constraints)
    op.execute("DROP TABLE IF EXISTS account_balances CASCADE")
