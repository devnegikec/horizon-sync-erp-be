"""Add ``putaway_in_progress`` to the receiving slip status check constraint.

The receiving slip lifecycle gained a ``putaway_in_progress`` state (set when a
put-away list is created, cleared once every list is complete). The original
``chk_slip_status`` check constraint only allows ``pending_review``,
``pending_putaway``, ``putaway_complete`` and ``rejected``, so persisting the
new state raises a CheckViolation. This widens the constraint accordingly.

Revision ID: 110_add_receiving_slip_putaway_in_progress_status
Revises: 109_link_asn_to_outbound_order
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "110_add_receiving_slip_putaway_in_progress_status"
down_revision: str | Sequence[str] | None = "109_link_asn_to_outbound_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE receiving_slips DROP CONSTRAINT IF EXISTS chk_slip_status")
    op.execute(
        "ALTER TABLE receiving_slips ADD CONSTRAINT chk_slip_status "
        "CHECK (status IN ('pending_review', 'pending_putaway', "
        "'putaway_in_progress', 'putaway_complete', 'rejected'))"
    )


def downgrade() -> None:
    # Rows still in `putaway_in_progress` would violate the restored
    # constraint, so move them back to the closest legacy state first.
    op.execute(
        "UPDATE receiving_slips SET status = 'pending_putaway' "
        "WHERE status = 'putaway_in_progress'"
    )
    op.execute("ALTER TABLE receiving_slips DROP CONSTRAINT IF EXISTS chk_slip_status")
    op.execute(
        "ALTER TABLE receiving_slips ADD CONSTRAINT chk_slip_status "
        "CHECK (status IN ('pending_review', 'pending_putaway', "
        "'putaway_complete', 'rejected'))"
    )
