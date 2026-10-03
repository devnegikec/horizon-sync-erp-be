"""Merge the two Phase-0 heads before UOM FK-ization.

Revision ID: 077_merge_phase0_heads
Revises: 075_add_items_per_master_pack, 075_merge_dev_qseal_heads
"""

from collections.abc import Sequence

revision: str = "077_merge_phase0_heads"
down_revision: tuple[str, str] = (
    "075_add_items_per_master_pack",
    "075_merge_dev_qseal_heads",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the two migration branches without changing the schema."""


def downgrade() -> None:
    """Split back to the two parent migration heads."""
