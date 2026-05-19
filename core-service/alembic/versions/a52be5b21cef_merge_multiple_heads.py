"""merge_multiple_heads

Revision ID: a52be5b21cef
Revises: 047_extend_pick_lists_and_create_put_away_lists
Create Date: 2026-05-16 00:53:21.673446

"""
from collections.abc import Sequence
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "a52be5b21cef"
down_revision: Union[str, None] = (
    "042_add_scan_sessions_tables",
    "047_extend_pick_lists_and_create_put_away_lists",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
