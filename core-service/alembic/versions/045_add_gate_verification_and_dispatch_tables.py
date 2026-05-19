"""Add gate_verification_sessions, gate_verification_items, and dispatch_records tables

Revision ID: 045_add_gate_verification_and_dispatch_tables
Revises: 044_add_receiving_slips_tables
Create Date: 2025-07-14

Creates the gate verification and dispatch tables for the warehouse
QR-based outbound workflow:

- gate_verification_sessions: Security gate sessions linked to completed pick lists
- gate_verification_items: Individual QR scans at the gate (verified/unauthorized)
- dispatch_records: Final dispatch records linking pick list, gate session, and vehicle

Requirements: 12.1, 12.6, 13.1
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "045_add_gate_verification_and_dispatch_tables"
down_revision = "044_add_receiving_slips_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── gate_verification_sessions ─────────────────────────────────
    op.create_table(
        "gate_verification_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "pick_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pick_lists.id"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses_extended.id"),
            nullable=False,
        ),
        sa.Column(
            "worker_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("vehicle_number", sa.String(100), nullable=True),
        sa.Column("driver_name", sa.String(255), nullable=True),
        sa.Column("driver_contact", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="open",
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'verified', 'cancelled')",
            name="chk_gate_status",
        ),
    )

    # Indexes for gate_verification_sessions
    op.create_index("idx_gvs_org", "gate_verification_sessions", ["organization_id"])
    op.create_index("idx_gvs_pick_list", "gate_verification_sessions", ["pick_list_id"])
    op.create_index("idx_gvs_status", "gate_verification_sessions", ["status"])

    # ── gate_verification_items ────────────────────────────────────
    op.create_table(
        "gate_verification_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gate_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gate_verification_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qr_identifier", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="verified",
        ),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('verified', 'unauthorized')",
            name="chk_gvi_status",
        ),
        sa.UniqueConstraint(
            "gate_session_id",
            "qr_identifier",
            name="uq_gate_session_qr",
        ),
    )

    # Indexes for gate_verification_items
    op.create_index("idx_gvi_session", "gate_verification_items", ["gate_session_id"])
    op.create_index("idx_gvi_status", "gate_verification_items", ["status"])

    # ── dispatch_records ───────────────────────────────────────────
    op.create_table(
        "dispatch_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("dispatch_number", sa.String(100), nullable=False),
        sa.Column(
            "pick_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pick_lists.id"),
            nullable=False,
        ),
        sa.Column(
            "gate_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gate_verification_sessions.id"),
            nullable=False,
        ),
        sa.Column("invoice_reference", sa.String(255), nullable=True),
        sa.Column("vehicle_number", sa.String(100), nullable=True),
        sa.Column("driver_name", sa.String(255), nullable=True),
        sa.Column(
            "dispatched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Indexes for dispatch_records
    op.create_index("idx_dr_org", "dispatch_records", ["organization_id"])
    op.create_index("idx_dr_pick_list", "dispatch_records", ["pick_list_id"])
    op.create_index("idx_dr_gate_session", "dispatch_records", ["gate_session_id"])
    op.create_index("idx_dr_dispatch_number", "dispatch_records", ["dispatch_number"])


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index("idx_dr_dispatch_number", table_name="dispatch_records")
    op.drop_index("idx_dr_gate_session", table_name="dispatch_records")
    op.drop_index("idx_dr_pick_list", table_name="dispatch_records")
    op.drop_index("idx_dr_org", table_name="dispatch_records")
    op.drop_table("dispatch_records")

    op.drop_index("idx_gvi_status", table_name="gate_verification_items")
    op.drop_index("idx_gvi_session", table_name="gate_verification_items")
    op.drop_table("gate_verification_items")

    op.drop_index("idx_gvs_status", table_name="gate_verification_sessions")
    op.drop_index("idx_gvs_pick_list", table_name="gate_verification_sessions")
    op.drop_index("idx_gvs_org", table_name="gate_verification_sessions")
    op.drop_table("gate_verification_sessions")
