"""add QSeal activation history and product counters"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_table

revision = "075_add_qseal_activation_history_and_counter"
down_revision = "074_add_pick_list_case_loose_and_assignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if has_table("qr_activation_parameters") and not has_column("qr_activation_parameters", "history"):
        op.add_column(
            "qr_activation_parameters",
            sa.Column("history", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if has_table("qr_products") and not has_column("qr_products", "num_activated_qr"):
        op.add_column(
            "qr_products",
            sa.Column("num_activated_qr", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if has_table("qr_products") and has_column("qr_products", "num_activated_qr"):
        op.drop_column("qr_products", "num_activated_qr")
    if has_table("qr_activation_parameters") and has_column("qr_activation_parameters", "history"):
        op.drop_column("qr_activation_parameters", "history")
