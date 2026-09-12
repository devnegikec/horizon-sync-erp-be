"""Extend receiving_slip_items.flag to support hold/excess/quarantine flags

The inbound exception workflow writes flag values beyond the original
('ok','short','damaged','rejected') set: `excess` (unexpected SKU on an ASN),
`hold`, and `quarantine`. The existing check constraint rejects those values,
so end-of-session slip generation raises a CheckViolation and the slip lines
are left as plain 'ok' instead of being flagged for manager review.

Revision ID: 106_extend_receiving_slip_flag_values
Revises: 105_add_transfer_pick_created_notification_type
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "106_extend_receiving_slip_flag_values"
down_revision: str | Sequence[str] | None = (
    "105_add_transfer_pick_created_notification_type"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALLOWED_FLAGS = ("ok", "short", "damaged", "rejected", "excess", "hold", "quarantine")


def upgrade() -> None:
    op.execute(
        "ALTER TABLE receiving_slip_items "
        "DROP CONSTRAINT IF EXISTS receiving_slip_items_flag_check"
    )
    op.execute(
        "ALTER TABLE receiving_slip_items "
        "ADD CONSTRAINT receiving_slip_items_flag_check "
        "CHECK (flag IN ('ok', 'short', 'damaged', 'rejected', 'excess', 'hold', 'quarantine'))"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE receiving_slip_items "
        "DROP CONSTRAINT IF EXISTS receiving_slip_items_flag_check"
    )
    op.execute(
        "ALTER TABLE receiving_slip_items "
        "ADD CONSTRAINT receiving_slip_items_flag_check "
        "CHECK (flag IN ('ok', 'short', 'damaged', 'rejected'))"
    )
