"""add_system_config_table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-17 18:05:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create table if it doesn't exist
    if "system_config" not in existing_tables:
        op.create_table(
            "system_config",
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("updated_by", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("key"),
        )

    # 2. Insert default values using ON CONFLICT to prevent migration failure on re-run
    op.execute(
        """
        INSERT INTO system_config (key, value, updated_by) VALUES
        ('base_currency', 'USD', 'system'),
        ('account_code_format', '^[0-9]{4}-[0-9]{2}$', 'system')
        ON CONFLICT (key) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Drop table safely
    op.execute("DROP TABLE IF EXISTS system_config CASCADE")
