"""Add bin_location_id and put_away tracking columns to receiving_slip_items

Revision ID: 061_add_bin_location_and_putaway_to_receiving_slip_items
Revises: 060_add_warehouse_floor_plans
Create Date: 2026-07-13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "061_add_bin_location_and_putaway_to_receiving_slip_items"
down_revision: Union[str, None] = "060_add_warehouse_floor_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add put-away tracking columns to receiving_slip_items
    op.add_column(
        "receiving_slip_items",
        sa.Column(
            "bin_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_rsi_bin_location",
        "receiving_slip_items",
        ["bin_location_id"],
    )
    op.add_column(
        "receiving_slip_items",
        sa.Column(
            "put_away_status",
            sa.String(20),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "receiving_slip_items",
        sa.Column(
            "put_away_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "receiving_slip_items",
        sa.Column(
            "put_away_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("receiving_slip_items", "put_away_by")
    op.drop_column("receiving_slip_items", "put_away_at")
    op.drop_column("receiving_slip_items", "put_away_status")
    op.drop_index("idx_rsi_bin_location", table_name="receiving_slip_items")
    op.drop_column("receiving_slip_items", "bin_location_id")
