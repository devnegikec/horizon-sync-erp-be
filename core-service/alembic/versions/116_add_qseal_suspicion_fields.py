"""Add explainable suspicious-scan fields to QSeal events.

Revision ID: 116_add_qseal_suspicion_fields
Revises: 115_add_qseal_scan_context
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_index


revision: str = "116_add_qseal_suspicion_fields"
down_revision: str | None = "115_add_qseal_scan_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = (
        sa.Column("is_suspicious", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("risk_score", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "suspicious_reasons",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="not_flagged"),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        if not has_column("qr_scan_events", column.name):
            op.add_column("qr_scan_events", column)

    for name, column in (
        ("ix_qr_scan_events_is_suspicious", "is_suspicious"),
        ("ix_qr_scan_events_risk_score", "risk_score"),
        ("ix_qr_scan_events_review_status", "review_status"),
    ):
        if not has_index("qr_scan_events", name):
            op.create_index(name, "qr_scan_events", [column])


def downgrade() -> None:
    for name in (
        "ix_qr_scan_events_review_status",
        "ix_qr_scan_events_risk_score",
        "ix_qr_scan_events_is_suspicious",
    ):
        if has_index("qr_scan_events", name):
            op.drop_index(name, table_name="qr_scan_events")
    for column in (
        "flagged_at",
        "review_status",
        "suspicious_reasons",
        "risk_score",
        "is_suspicious",
    ):
        if has_column("qr_scan_events", column):
            op.drop_column("qr_scan_events", column)
