"""Merge heads: consolidated to single baseline

Revision ID: 016_merge_heads
Revises: 001_merged_complete_schema
Create Date: 2026-02-26

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "016_merge_heads"
down_revision = "001_merged_complete_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
