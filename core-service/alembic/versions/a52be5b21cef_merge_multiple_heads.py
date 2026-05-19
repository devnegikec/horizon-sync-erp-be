"""merge_multiple_heads

Revision ID: a52be5b21cef
Revises: 042_add_scan_sessions_tables, 042_bulk_import, 047_extend_pick_lists_and_create_put_away_lists
Create Date: 2026-05-16 00:53:21.673446

Merges three parallel branches that all diverged from 041_create_core_tables_baseline:
  - 042_add_scan_sessions_tables  (WMS inbound scan sessions)
  - 042_bulk_import               (bulk import jobs table)
  - 047_extend_pick_lists_and_create_put_away_lists  (end of WMS warehouse locations chain)
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a52be5b21cef"
down_revision: tuple = (
    "042_add_scan_sessions_tables",
    "042_bulk_import",
    "047_extend_pick_lists_and_create_put_away_lists",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
