"""merge core migration heads

Revision ID: 133_merge_core_migration_heads
Revises: 078_add_qseal_activation_requests, 110_add_receiving_slip_putaway_in_progress_status, 114_remove_receiving_stage_bins
Create Date: 2026-09-14 12:28:43.925434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '133_merge_core_migration_heads'
down_revision: Union[str, None] = ('078_add_qseal_activation_requests', '110_add_receiving_slip_putaway_in_progress_status', '114_remove_receiving_stage_bins', '132_exchange_rate_org_scope')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
