"""Add packing-slip dispatch support to dispatch records.

Dispatch can now be created from a packing slip (final reconciliation before
gate-out) in addition to the legacy verified-gate-session path. This makes
``pick_list_id`` and ``gate_session_id`` nullable and adds
``packing_slip_id``.

Revision ID: 112_dispatch_from_packing_slip
Revises: 111_packing_slips
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "112_dispatch_from_packing_slip"
down_revision: str | Sequence[str] | None = "111_packing_slips"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "dispatch_records",
        "pick_list_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "dispatch_records",
        "gate_session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "dispatch_records",
        sa.Column("packing_slip_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "dispatch_records_packing_slip_id_fkey",
        "dispatch_records",
        "packing_slips",
        ["packing_slip_id"],
        ["id"],
    )
    op.create_index(
        "ix_dispatch_records_packing_slip_id",
        "dispatch_records",
        ["packing_slip_id"],
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE dispatch_records "
        "DROP CONSTRAINT IF EXISTS dispatch_records_packing_slip_id_fkey"
    )
    op.drop_index(
        "ix_dispatch_records_packing_slip_id", table_name="dispatch_records"
    )
    # Packing-slip dispatches leave pick_list_id/gate_session_id NULL, so
    # remove them before restoring the legacy columns' NOT NULL constraints.
    op.execute(
        "DELETE FROM dispatch_records "
        "WHERE pick_list_id IS NULL OR gate_session_id IS NULL"
    )
    op.drop_column("dispatch_records", "packing_slip_id")
    op.alter_column(
        "dispatch_records",
        "gate_session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "dispatch_records",
        "pick_list_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
