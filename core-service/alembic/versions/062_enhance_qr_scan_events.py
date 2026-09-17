"""Enhance QR scan events and add scan interactions.

Revision ID: 062_enhance_qr_scan_events
Revises: 061_add_bin_location_and_putaway_to_receiving_slip_items
Create Date: 2026-07-13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_index, has_table

revision: str = "062_enhance_qr_scan_events"
down_revision: Union[str, None] = (
    "061_add_bin_location_and_putaway_to_receiving_slip_items"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = (
        sa.Column("user_agent_raw", sa.Text, nullable=True),
        sa.Column("user_agent_parsed", postgresql.JSONB, nullable=True),
        sa.Column("qr_type", sa.String(30), nullable=True),
        sa.Column("cta_action", sa.String(50), nullable=True),
        sa.Column("referrer_url", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
    )
    for column in columns:
        if not has_column("qr_scan_events", column.name):
            op.add_column("qr_scan_events", column)

    if not has_table("qr_scan_interactions"):
        op.create_table(
            "qr_scan_interactions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column(
                "scan_event_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qr_scan_events.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("interaction_type", sa.String(50), nullable=False),
            sa.Column("interaction_target", sa.Text, nullable=True),
            sa.Column("interaction_data", postgresql.JSONB, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )

    if not has_index("qr_scan_interactions", "idx_qr_interactions_org"):
        op.create_index(
            "idx_qr_interactions_org",
            "qr_scan_interactions",
            ["organization_id"],
        )
    if not has_index("qr_scan_interactions", "idx_qr_interactions_scan"):
        op.create_index(
            "idx_qr_interactions_scan",
            "qr_scan_interactions",
            ["scan_event_id"],
        )


def downgrade() -> None:
    if has_table("qr_scan_interactions"):
        op.drop_table("qr_scan_interactions")
    for column_name in (
        "language",
        "referrer_url",
        "cta_action",
        "qr_type",
        "user_agent_parsed",
        "user_agent_raw",
    ):
        if has_column("qr_scan_events", column_name):
            op.drop_column("qr_scan_events", column_name)
