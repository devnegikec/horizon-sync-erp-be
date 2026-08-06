"""Merge multiple heads

Revision ID: 064_merge_heads
Revises: 062, 063_add_landing_page_configs, 063_add_qr_cta_configs
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "064_merge_heads"
down_revision: Union[str, tuple[str, ...], None] = (
    "062",
    "063_add_landing_page_configs",
    "063_add_qr_cta_configs",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
