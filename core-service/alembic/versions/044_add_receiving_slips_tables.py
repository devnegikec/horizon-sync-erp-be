"""Add receiving_slips and receiving_slip_items tables

Revision ID: 044_add_receiving_slips_tables
Revises: 043_add_bin_stock_levels_and_location_allocations
Create Date: 2025-07-14

Creates the receiving_slips and receiving_slip_items tables for the
warehouse QR-based inbound workflow. Receiving slips are generated from
closed scan sessions and go through a review workflow before put-away.

Requirements: 6.1, 7.1
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "044_add_receiving_slips_tables"
down_revision = "043_add_bin_stock_levels_and_location_allocations"
branch_labels = None
depends_on = ("042_add_scan_sessions_tables",)


def upgrade() -> None:
    # ── receiving_slips ────────────────────────────────────────────
    op.create_table(
        "receiving_slips",
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
        sa.Column("slip_number", sa.String(100), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scan_sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses_extended.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("total_boxes", sa.Integer(), server_default="0"),
        sa.Column("total_items", sa.Integer(), server_default="0"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "status IN ('pending_review', 'pending_putaway', 'putaway_complete', 'rejected')",
            name="chk_slip_status",
        ),
    )

    # Indexes for receiving_slips
    op.create_index("idx_rs_org", "receiving_slips", ["organization_id"])
    op.create_index("idx_rs_session", "receiving_slips", ["session_id"])
    op.create_index("idx_rs_warehouse", "receiving_slips", ["warehouse_id"])
    op.create_index("idx_rs_status", "receiving_slips", ["status"])

    # ── receiving_slip_items ───────────────────────────────────────
    op.create_table(
        "receiving_slip_items",
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
            "slip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("receiving_slips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("box_count", sa.Integer(), server_default="0"),
        sa.Column("flag", sa.String(20), server_default="ok"),
        sa.Column("notes", sa.Text(), nullable=True),
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
            "flag IN ('ok', 'short', 'damaged')",
            name="chk_item_flag",
        ),
    )

    # Indexes for receiving_slip_items
    op.create_index("idx_rsi_slip", "receiving_slip_items", ["slip_id"])
    op.create_index("idx_rsi_sku", "receiving_slip_items", ["sku"])


def downgrade() -> None:
    op.drop_index("idx_rsi_sku", table_name="receiving_slip_items")
    op.drop_index("idx_rsi_slip", table_name="receiving_slip_items")
    op.drop_table("receiving_slip_items")

    op.drop_index("idx_rs_status", table_name="receiving_slips")
    op.drop_index("idx_rs_warehouse", table_name="receiving_slips")
    op.drop_index("idx_rs_session", table_name="receiving_slips")
    op.drop_index("idx_rs_org", table_name="receiving_slips")
    op.drop_table("receiving_slips")
