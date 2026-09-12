"""Link vehicle arrivals to scan sessions and receiving slips.

Revision ID: 077_link_vehicle_arrival_to_sessions_and_slips
Revises: 076_add_vehicle_arrival_tables
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "077_link_vehicle_arrival_to_sessions_and_slips"
down_revision: str | Sequence[str] | None = "076_add_vehicle_arrival_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Add vehicle_arrival_id to scan_sessions ─────────────────────
    op.add_column(
        "scan_sessions",
        sa.Column(
            "vehicle_arrival_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_arrivals.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_scan_sessions_vehicle_arrival_id",
        "scan_sessions",
        ["vehicle_arrival_id"],
    )

    # ── 2. Add vehicle_arrival_id to receiving_slips ───────────────────
    op.add_column(
        "receiving_slips",
        sa.Column(
            "vehicle_arrival_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_arrivals.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_receiving_slips_vehicle_arrival_id",
        "receiving_slips",
        ["vehicle_arrival_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_receiving_slips_vehicle_arrival_id", table_name="receiving_slips")
    op.drop_column("receiving_slips", "vehicle_arrival_id")
    op.drop_index("ix_scan_sessions_vehicle_arrival_id", table_name="scan_sessions")
    op.drop_column("scan_sessions", "vehicle_arrival_id")
