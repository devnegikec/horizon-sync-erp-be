"""Widen warehouses_extended.total_capacity to support fractional capacities.

Warehouse capacity is derived from active bin locations, whose capacity is
Numeric(15, 3). The warehouse column was Integer, which truncated fractional
volume totals. Widen it to Numeric(15, 3) so derived totals match the location
and capacity-service rollups exactly.

Revision ID: 107_warehouse_total_capacity_numeric
Revises: 106_extend_receiving_slip_flag_values
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "107_warehouse_total_capacity_numeric"
down_revision: str | Sequence[str] | None = "106_extend_receiving_slip_flag_values"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE warehouses_extended "
        "ALTER COLUMN total_capacity TYPE numeric(15, 3) "
        "USING total_capacity::numeric(15, 3)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE warehouses_extended "
        "ALTER COLUMN total_capacity TYPE integer "
        "USING total_capacity::integer"
    )
