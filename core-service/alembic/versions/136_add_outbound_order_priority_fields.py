"""Add prioritization columns to outbound orders.

Stores dispatch cutoff / wave / route on the outbound order so the values
can be copied onto generated pick lists and drive the configured
``pick.priority_fields`` (WF-007) sort order.

Revision ID: 136_add_outbound_order_priority_fields
Revises: 135_add_bin_stock_parent_qr_flag
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "136_add_outbound_order_priority_fields"
down_revision: str | Sequence[str] | None = "135_add_bin_stock_parent_qr_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbound_orders",
        sa.Column("dispatch_cutoff", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbound_orders",
        sa.Column("wave", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "outbound_orders",
        sa.Column("route", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outbound_orders", "route")
    op.drop_column("outbound_orders", "wave")
    op.drop_column("outbound_orders", "dispatch_cutoff")
