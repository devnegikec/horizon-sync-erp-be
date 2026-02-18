"""add account_audit_log table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2024-01-15 10:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine.reflection import Inspector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create account_audit_log table safely"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create table only if it doesn't exist
    if "account_audit_log" not in existing_tables:
        op.create_table(
            "account_audit_log",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "account_id",
                UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("user_id", sa.String(100), nullable=False),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column("changes", JSONB, nullable=False),
            sa.Column("audit_metadata", JSONB, nullable=True),
            sa.CheckConstraint(
                "action IN ('CREATE', 'UPDATE', 'DELETE', 'STATUS_CHANGE')",
                name="valid_action",
            ),
        )

    # 2. Create indexes safely using native PG "IF NOT EXISTS"
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_account ON account_audit_log (account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON account_audit_log (timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_user ON account_audit_log (user_id)"
    )


def downgrade() -> None:
    """Drop account_audit_log table safely"""
    op.execute("DROP TABLE IF EXISTS account_audit_log CASCADE")
