"""Repair missing QSeal suspicion columns on ``qr_scan_events``.

Revision 116 can be marked as applied after its guarded operations were skipped
on a partially initialized database.  The ORM and the summary/history queries
then reference columns that are absent from the live table.  Re-check the live
schema here so the repair is applied even when Alembic already passed revision
116.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_index, has_table


revision: str = "137_repair_qr_scan_suspicion_fields"
down_revision: str | Sequence[str] | None = "136_repair_audit_log_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ensure all suspicion fields and dashboard indexes exist."""
    if not has_table("qr_scan_events"):
        return

    columns = (
        sa.Column(
            "is_suspicious",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "risk_score",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "suspicious_reasons",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "review_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'not_flagged'"),
        ),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        if not has_column("qr_scan_events", column.name):
            op.add_column("qr_scan_events", column)

    for index_name, column_name in (
        ("ix_qr_scan_events_is_suspicious", "is_suspicious"),
        ("ix_qr_scan_events_risk_score", "risk_score"),
        ("ix_qr_scan_events_review_status", "review_status"),
    ):
        if not has_index("qr_scan_events", index_name):
            op.create_index(index_name, "qr_scan_events", [column_name])


def downgrade() -> None:
    """Remove the objects repaired by this migration."""
    if not has_table("qr_scan_events"):
        return

    for index_name in (
        "ix_qr_scan_events_review_status",
        "ix_qr_scan_events_risk_score",
        "ix_qr_scan_events_is_suspicious",
    ):
        if has_index("qr_scan_events", index_name):
            op.drop_index(index_name, table_name="qr_scan_events")

    for column_name in (
        "flagged_at",
        "review_status",
        "suspicious_reasons",
        "risk_score",
        "is_suspicious",
    ):
        if has_column("qr_scan_events", column_name):
            op.drop_column("qr_scan_events", column_name)
