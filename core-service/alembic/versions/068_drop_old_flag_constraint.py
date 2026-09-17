"""Drop old chk_item_flag constraint — conflicts with rejected flag

The old chk_item_flag constraint only allows ('ok','short','damaged') and
blocks the 'rejected' flag value. The newer receiving_slip_items_flag_check
already covers all four values.

Revision ID: 068_drop_old_flag_constraint
Revises: 067_add_scanned_item_tracking
Create Date: 2026-08-12
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers
revision: str = "068_drop_old_flag_constraint"
down_revision: Union[str, None] = "067_add_scanned_item_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE receiving_slip_items DROP CONSTRAINT IF EXISTS chk_item_flag"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE receiving_slip_items ADD CONSTRAINT chk_item_flag "
        "CHECK (flag::text = ANY (ARRAY['ok'::text, 'short'::text, 'damaged'::text]))"
    )
