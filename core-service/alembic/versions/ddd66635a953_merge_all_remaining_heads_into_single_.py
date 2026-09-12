"""merge all remaining heads into single lineage

Revision ID: ddd66635a953
Revises: 079_add_inbound_short_balance_ledger, 089_add_scan_session_cancelled_status, 106_backfill_uom_type, 112_dispatch_from_packing_slip
Create Date: 2026-09-08 18:04:35.942188

NOTE: 042_add_scan_sessions_tables is intentionally NOT listed here. It is
already pulled into the main branch via the ``depends_on`` relationship on
044_add_receiving_slips_tables, so listing it again as a merge input makes
Alembic delete the same head twice (KeyError).

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddd66635a953'
down_revision: Union[str, None] = ('079_add_inbound_short_balance_ledger', '089_add_scan_session_cancelled_status', '106_backfill_uom_type', '112_dispatch_from_packing_slip')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
