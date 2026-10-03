"""merge_multiple_heads

Revision ID: 048_merge_multiple_heads
Revises: 042_bulk_import, 047_extend_pick_lists_and_create_put_away_lists
Create Date: 2026-05-16 00:53:21.673446

Merges the parallel branches that diverged from 041_create_core_tables_baseline:
  - 042_bulk_import               (bulk import jobs table)
  - 047_extend_pick_lists_and_create_put_away_lists  (end of WMS warehouse locations chain)

NOTE: 042_add_scan_sessions_tables is intentionally NOT listed here. It is
already pulled into the 047 branch via the `depends_on` relationship on
044_add_receiving_slips_tables, so listing it again as a merge input makes
Alembic try to delete the same head twice (KeyError on a fresh DB).
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "048_merge_multiple_heads"
down_revision: tuple = (
    "042_bulk_import",
    "047_extend_pick_lists_and_create_put_away_lists",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
