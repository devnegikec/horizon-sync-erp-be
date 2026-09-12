"""Merge the receiving-slip status head into the single lineage.

The ``112_merge_all_remaining_heads_into_single_`` merge missed
``110_add_receiving_slip_putaway_in_progress_status``, leaving it as a second
head. This merge folds it into the current tip so ``alembic upgrade head`` has
a single target.

Revision ID: 117_merge_receiving_slip_status_head
Revises: 110_add_receiving_slip_putaway_in_progress_status, 116_index_qseal_parameters_serial_number
Create Date: 2026-09-12
"""

from collections.abc import Sequence

revision: str = "117_merge_receiving_slip_status_head"
down_revision: str | Sequence[str] | None = (
    "110_add_receiving_slip_putaway_in_progress_status",
    "116_index_qseal_parameters_serial_number",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
