"""Allow 'cancelled' status for inbound/gate scan sessions.

Cancelling a session (mobile app "Cancel & Start Fresh" flow) marks the
session as 'cancelled' instead of 'closed' so it remains distinguishable from
a session that was ended and produced a receiving slip.

Revision ID: 089_add_scan_session_cancelled_status
Revises: 088_merge_vehicle_arrival_heads
"""

from collections.abc import Sequence

from alembic import op

revision: str = "089_add_scan_session_cancelled_status"
down_revision: str | Sequence[str] | None = "088_merge_vehicle_arrival_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("chk_session_status", "scan_sessions", type_="check")
    op.create_check_constraint(
        "chk_session_status",
        "scan_sessions",
        "status IN ('open', 'closed', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_session_status", "scan_sessions", type_="check")
    op.create_check_constraint(
        "chk_session_status",
        "scan_sessions",
        "status IN ('open', 'closed')",
    )
