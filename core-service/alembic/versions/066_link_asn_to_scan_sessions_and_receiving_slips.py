"""Link ASN orders to scan sessions and receiving slips, add item-level rejection support

Revision ID: 066_link_asn_to_scan_sessions_and_receiving_slips
Revises: 065_add_stock_tables
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "066_link_asn_to_scan_sessions_and_receiving_slips"
down_revision: Union[str, None] = "065_add_stock_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add asn_order_id to scan_sessions ────────────────────────────
    op.add_column(
        "scan_sessions",
        sa.Column(
            "asn_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asn_orders.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # ── 2. Add asn_order_id to receiving_slips ──────────────────────────
    op.add_column(
        "receiving_slips",
        sa.Column(
            "asn_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asn_orders.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # ── 3. Drop old flag check constraint on receiving_slip_items ───────
    # Replace the old constraint that only allows ('ok','short','damaged')
    # with one that also allows 'rejected'.
    op.execute("""
        ALTER TABLE receiving_slip_items
        DROP CONSTRAINT IF EXISTS receiving_slip_items_flag_check
    """)

    # ── 4. Add rejection_reason column to receiving_slip_items ──────────
    op.add_column(
        "receiving_slip_items",
        sa.Column("rejection_reason", sa.Text, nullable=True),
    )

    # ── 5. Add rejected_by to receiving_slip_items ──────────────────────
    op.add_column(
        "receiving_slip_items",
        sa.Column(
            "rejected_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # ── 6. Add rejected_at to receiving_slip_items ──────────────────────
    op.add_column(
        "receiving_slip_items",
        sa.Column(
            "rejected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ── 7. Re-create flag check constraint with extended values ─────────
    op.execute("""
        ALTER TABLE receiving_slip_items
        ADD CONSTRAINT receiving_slip_items_flag_check
        CHECK (flag IN ('ok', 'short', 'damaged', 'rejected'))
    """)

    # ── 8. Add index on asn_order_id in receiving_slip_items (for mismatch queries) ──
    # Already covered by FK index on receiving_slips.asn_order_id;
    # receiving_slip_items join through slip_id.


def downgrade() -> None:
    # Drop flag constraint, revert columns
    op.execute("""
        ALTER TABLE receiving_slip_items
        DROP CONSTRAINT IF EXISTS receiving_slip_items_flag_check
    """)

    op.execute("""
        ALTER TABLE receiving_slip_items
        ADD CONSTRAINT receiving_slip_items_flag_check
        CHECK (flag IN ('ok', 'short', 'damaged'))
    """)

    op.drop_column("receiving_slip_items", "rejected_at")
    op.drop_column("receiving_slip_items", "rejected_by")
    op.drop_column("receiving_slip_items", "rejection_reason")

    op.drop_column("receiving_slips", "asn_order_id")
    op.drop_column("scan_sessions", "asn_order_id")
