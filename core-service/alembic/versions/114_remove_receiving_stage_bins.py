"""Deactivate legacy RECEIVING-STAGE bins.

Direct put-away and the RECEIVING-STAGE staging bin were removed. This
deactivates any RECEIVING-STAGE ``warehouse_locations`` rows that earlier
migrations (078) or runtime code created, so they stop appearing in the
Location Tree.

Revision ID: 114_remove_receiving_stage_bins
Revises: 113_packing_slip_fk_numeric_stock
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

from app.alembic_guards import has_table

revision: str = "114_remove_receiving_stage_bins"
down_revision: str | Sequence[str] | None = "113_packing_slip_fk_numeric_stock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("warehouse_locations"):
        return
    op.get_bind().execute(
        sa.text(
            "UPDATE warehouse_locations "
            "SET is_active = false, is_available = false "
            "WHERE code = 'RECEIVING-STAGE'"
        )
    )


def downgrade() -> None:
    # Intentionally a no-op: RECEIVING-STAGE is permanently deprecated. We do
    # not reactivate rows on downgrade, because some of them may have been
    # inactive before this migration and we cannot restore their prior state.
    return
