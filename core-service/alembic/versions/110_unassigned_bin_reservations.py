"""Allow unassigned (worker-less) bin reservations for order-driven pick lists.

Order-driven pick lists reserve their resolved bins at creation time. An
unassigned pick list (no worker yet) still needs a short-TTL hold so the bin
is not silently double-allocated to another pick list, which requires
``bin_reservations.worker_id`` to be nullable.

Revision ID: 110_unassigned_bin_reservations
Revises: 109_link_asn_to_outbound_order
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "110_unassigned_bin_reservations"
down_revision: str | Sequence[str] | None = "109_link_asn_to_outbound_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "bin_reservations",
        "worker_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Safe only when no worker-less holds remain; re-nulling is not attempted.
    op.alter_column(
        "bin_reservations",
        "worker_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
