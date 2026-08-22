"""Merge dev and QSeal analytics migration heads.

Revision ID: 075_merge_dev_qseal_heads
Revises: 070_merge_qr_analytics_heads, 074_add_pick_list_case_loose_and_assignment
"""

from collections.abc import Sequence

revision: str = "075_merge_dev_qseal_heads"
down_revision: tuple[str, str] = (
    "070_merge_qr_analytics_heads",
    "074_add_pick_list_case_loose_and_assignment",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the two migration branches without changing the schema."""


def downgrade() -> None:
    """Split back to the two parent migration heads."""
