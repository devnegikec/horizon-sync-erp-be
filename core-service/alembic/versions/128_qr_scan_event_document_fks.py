"""Typed document FKs on qr_scan_events (T3.5).

Adds nullable ``asn_order_id``, ``scan_session_id`` and ``dispatch_record_id``
columns so scan events can be correlated to their documents by key instead of
parsing ``extra_data`` strings. The columns are plain UUIDs (no DB-level FK),
matching the repo's "plain UUIDs" pattern; the SQLAlchemy ``ForeignKey`` in the
model governs fresh ``create_all`` databases.

Revision ID: 128_qr_scan_event_document_fks
Revises: 127_receipt_serial_identity
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_index, has_table

revision: str = "128_qr_scan_event_document_fks"
down_revision: str | Sequence[str] | None = "127_receipt_serial_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("asn_order_id", "scan_session_id", "dispatch_record_id")


def upgrade() -> None:
    if not has_table("qr_scan_events"):
        return

    for column in COLUMNS:
        if not has_column("qr_scan_events", column):
            op.add_column(
                "qr_scan_events",
                sa.Column(column, postgresql.UUID(as_uuid=True), nullable=True),
            )
        index_name = f"ix_qr_scan_events_{column}"
        if not has_index("qr_scan_events", index_name):
            op.create_index(index_name, "qr_scan_events", [column])


def downgrade() -> None:
    if not has_table("qr_scan_events"):
        return

    for column in COLUMNS:
        index_name = f"ix_qr_scan_events_{column}"
        if has_index("qr_scan_events", index_name):
            op.drop_index(index_name, table_name="qr_scan_events")
        if has_column("qr_scan_events", column):
            op.drop_column("qr_scan_events", column)
