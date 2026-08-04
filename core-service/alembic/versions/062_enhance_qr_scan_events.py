"""Enhance qr_scan_events with user-agent, CTA, geo enrichment + add qr_scan_interactions

Revision ID: 062_enhance_qr_scan_events
Revises: 061_add_bin_location_and_putaway_to_receiving_slip_items
Create Date: 2026-07-13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "062_enhance_qr_scan_events"
down_revision: Union[
    str, None
] = "061_add_bin_location_and_putaway_to_receiving_slip_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add columns to qr_scan_events ─────────────────────────────────────
    op.add_column(
        "qr_scan_events",
        sa.Column("user_agent_raw", sa.Text, nullable=True),
    )
    op.add_column(
        "qr_scan_events",
        sa.Column("user_agent_parsed", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "qr_scan_events",
        sa.Column("qr_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "qr_scan_events",
        sa.Column("cta_action", sa.String(50), nullable=True),
    )
    op.add_column(
        "qr_scan_events",
        sa.Column("referrer_url", sa.Text, nullable=True),
    )
    op.add_column(
        "qr_scan_events",
        sa.Column("language", sa.String(10), nullable=True),
    )

    # ── Create qr_scan_interactions ───────────────────────────────────────
    op.create_table(
        "qr_scan_interactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "scan_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qr_scan_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "interaction_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "interaction_target",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "interaction_data",
            postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_qr_interactions_org",
        "qr_scan_interactions",
        ["organization_id"],
    )
    op.create_index(
        "idx_qr_interactions_scan",
        "qr_scan_interactions",
        ["scan_event_id"],
    )


def downgrade() -> None:
    op.drop_table("qr_scan_interactions")
    op.drop_column("qr_scan_events", "language")
    op.drop_column("qr_scan_events", "referrer_url")
    op.drop_column("qr_scan_events", "cta_action")
    op.drop_column("qr_scan_events", "qr_type")
    op.drop_column("qr_scan_events", "user_agent_parsed")
    op.drop_column("qr_scan_events", "user_agent_raw")
