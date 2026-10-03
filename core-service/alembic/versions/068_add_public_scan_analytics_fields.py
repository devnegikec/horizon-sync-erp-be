"""Add public QR verification analytics fields.

Revision ID: 068_add_public_scan_analytics_fields
Revises: 067_add_qseal_cascade_tables
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_index

revision: str = "068_add_public_scan_analytics_fields"
down_revision: str | None = "067_add_qseal_cascade_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = (
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verification_status", sa.String(40), nullable=True),
        sa.Column("authentic", sa.Boolean(), nullable=True),
        sa.Column("qr_channel", sa.String(10), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column(
            "is_bot", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("location_source", sa.String(20), nullable=True),
        sa.Column("location_accuracy_meters", sa.Integer(), nullable=True),
    )
    for column in columns:
        if not has_column("qr_scan_events", column.name):
            op.add_column("qr_scan_events", column)

    if not has_index("qr_scan_events", "uq_qr_scan_events_event_id"):
        op.create_index(
            "uq_qr_scan_events_event_id",
            "qr_scan_events",
            ["event_id"],
            unique=True,
            postgresql_where=sa.text("event_id IS NOT NULL"),
        )
    if not has_index("qr_scan_events", "ix_qr_scan_events_verification_status"):
        op.create_index(
            "ix_qr_scan_events_verification_status",
            "qr_scan_events",
            ["verification_status"],
        )


def downgrade() -> None:
    for index_name in (
        "ix_qr_scan_events_verification_status",
        "uq_qr_scan_events_event_id",
    ):
        if has_index("qr_scan_events", index_name):
            op.drop_index(index_name, table_name="qr_scan_events")
    for column_name in (
        "location_accuracy_meters",
        "location_source",
        "is_bot",
        "ip_hash",
        "qr_channel",
        "authentic",
        "verification_status",
        "event_id",
    ):
        if has_column("qr_scan_events", column_name):
            op.drop_column("qr_scan_events", column_name)
