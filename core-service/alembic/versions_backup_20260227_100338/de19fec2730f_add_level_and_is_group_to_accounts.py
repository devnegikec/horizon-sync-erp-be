"""add_level_and_is_group_to_accounts

Revision ID: de19fec2730f
Revises: bc78b582cd1f
Create Date: 2026-02-26 18:42:38.610943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de19fec2730f'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add level and is_group columns to accounts table
    op.add_column('accounts', sa.Column('level', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('accounts', sa.Column('is_group', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    # Remove level and is_group columns
    op.drop_column('accounts', 'is_group')
    op.drop_column('accounts', 'level')
