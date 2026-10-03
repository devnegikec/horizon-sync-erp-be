"""Add scanned_item_tracking table

Revision ID: 067
Revises: 066_link_asn_to_scan_sessions_and_receiving_slips
Create Date: 2026-08-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "067_add_scanned_item_tracking"
down_revision: Union[str, None] = "066_link_asn_to_scan_sessions_and_receiving_slips"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scanned_item_tracking",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("warehouses_extended.id"), nullable=False),

        # Scan context
        sa.Column("scan_session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("scan_sessions.id"), nullable=False),
        sa.Column("scan_session_item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("scan_session_items.id"), nullable=False, unique=True),
        sa.Column("qr_identifier", sa.String(255), nullable=False),

        # Item details
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),

        # Receiving axis
        sa.Column("receiving_status", sa.String(30), nullable=False, server_default="scanned"),
        sa.Column("receiving_slip_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("receiving_slips.id"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),

        # Put-away axis
        sa.Column("putaway_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("put_away_list_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("put_away_lists.id"), nullable=True),
        sa.Column("put_away_item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("put_away_list_items.id"), nullable=True),
        sa.Column("bin_location_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("warehouse_locations.id"), nullable=True),
        sa.Column("putaway_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("putaway_by", postgresql.UUID(as_uuid=True), nullable=True),

        # Derived
        sa.Column("stock_entered", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("stock_entered_at", sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column("scanned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # Indexes
    op.create_index("idx_tracking_receiving", "scanned_item_tracking",
                    ["receiving_status", "warehouse_id"])
    op.create_index("idx_tracking_putaway", "scanned_item_tracking",
                    ["putaway_status", "warehouse_id"])
    op.create_index("idx_tracking_stock", "scanned_item_tracking",
                    ["stock_entered", "warehouse_id"],
                    postgresql_where=sa.text("stock_entered = TRUE"))
    op.create_index("idx_tracking_qr", "scanned_item_tracking", ["qr_identifier"])
    op.create_index("idx_tracking_session", "scanned_item_tracking", ["scan_session_id"])


def downgrade() -> None:
    op.drop_table("scanned_item_tracking")
