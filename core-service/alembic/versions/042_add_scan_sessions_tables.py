"""add scan_sessions and scan_session_items tables

Revision ID: 042_add_scan_sessions_tables
Revises: 041_create_core_tables_baseline
Create Date: 2026-05-10 10:00:00.000000

Creates the scan_sessions and scan_session_items tables for QR-based
inbound receiving and gate verification workflows.

- scan_sessions: Groups QR scans into inbound or gate sessions
- scan_session_items: Individual QR scans within a session

Requirements: 5.1, 5.2
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "042_add_scan_sessions_tables"
down_revision = "041_create_core_tables_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    # ── scan_sessions table ───────────────────────────────────────────────────
    if not inspector.has_table("scan_sessions"):
        op.create_table(
            "scan_sessions",
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
                "session_type",
                sa.String(20),
                nullable=False,
            ),
            sa.Column(
                "worker_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column(
                "warehouse_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("warehouses_extended.id"),
                nullable=False,
            ),
            sa.Column("dock_location", sa.String(255), nullable=True),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="open",
            ),
            sa.Column(
                "total_boxes_scanned",
                sa.Integer,
                server_default="0",
            ),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "ended_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            # CHECK constraints
            sa.CheckConstraint(
                "session_type IN ('inbound', 'gate')",
                name="chk_session_type",
            ),
            sa.CheckConstraint(
                "status IN ('open', 'closed')",
                name="chk_session_status",
            ),
        )

        # Indexes for scan_sessions
        op.create_index("idx_ss_org", "scan_sessions", ["organization_id"])
        op.create_index("idx_ss_worker", "scan_sessions", ["worker_id"])
        op.create_index("idx_ss_status", "scan_sessions", ["status"])
        op.create_index("idx_ss_warehouse", "scan_sessions", ["warehouse_id"])

    # ── scan_session_items table ──────────────────────────────────────────────
    if not inspector.has_table("scan_session_items"):
        op.create_table(
            "scan_session_items",
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
                "session_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("scan_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "qr_identifier",
                sa.String(255),
                nullable=False,
            ),
            sa.Column(
                "sku",
                sa.String(100),
                nullable=False,
            ),
            sa.Column(
                "quantity",
                sa.Integer,
                nullable=False,
            ),
            sa.Column(
                "batch_number",
                sa.String(100),
                nullable=False,
            ),
            sa.Column(
                "raw_qr_data",
                sa.Text,
                nullable=False,
            ),
            sa.Column(
                "scanned_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            # Unique constraint: no duplicate QR within same session
            sa.UniqueConstraint(
                "session_id",
                "qr_identifier",
                name="uq_session_qr",
            ),
        )

        # Indexes for scan_session_items
        op.create_index("idx_ssi_session", "scan_session_items", ["session_id"])
        op.create_index("idx_ssi_sku", "scan_session_items", ["sku"])


def downgrade() -> None:
    op.drop_table("scan_session_items")
    op.drop_table("scan_sessions")
