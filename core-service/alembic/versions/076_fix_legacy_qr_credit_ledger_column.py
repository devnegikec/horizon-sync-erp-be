"""Allow legacy QR-credit ledger rows without a legacy quantity column.

Some databases were migrated from the original ``quantity_deducted`` ledger
schema and still contain that column as NOT NULL alongside the newer
``amount`` column.  Credit additions do not have a quantity-deducted value,
so the legacy column must be nullable.
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_table

revision = "076_fix_legacy_qr_credit_ledger_column"
down_revision = (
    "075_add_qseal_activation_history_and_counter",
    "075_merge_dev_qseal_heads",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table("qr_credit_ledger") and has_column(
        "qr_credit_ledger", "quantity_deducted"
    ):
        op.alter_column(
            "qr_credit_ledger",
            "quantity_deducted",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    if has_table("qr_credit_ledger") and has_column(
        "qr_credit_ledger", "quantity_deducted"
    ):
        op.alter_column(
            "qr_credit_ledger",
            "quantity_deducted",
            existing_type=sa.Integer(),
            nullable=False,
        )
