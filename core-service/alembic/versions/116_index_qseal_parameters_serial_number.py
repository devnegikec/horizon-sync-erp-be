"""Index qseal_parameters.serial_number for master-pack grouping lookups.

Receiving-slip / put-away / packing-slip responses resolve unit serials via
``QSealParameters.serial_number``. This column was previously unindexed, so the
``IN`` lookup did a sequential scan on large slips.

Revision ID: 116_index_qseal_parameters_serial_number
Revises: 115_put_away_item_serial_nos
Create Date: 2026-09-12
"""

from collections.abc import Sequence

from alembic import op

from app.alembic_guards import has_index, has_table

revision: str = "116_index_qseal_parameters_serial_number"
down_revision: str | Sequence[str] | None = "115_put_away_item_serial_nos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("qseal_parameters") and not has_index(
        "qseal_parameters", "ix_qseal_parameters_serial_number"
    ):
        op.create_index(
            "ix_qseal_parameters_serial_number",
            "qseal_parameters",
            ["serial_number"],
        )


def downgrade() -> None:
    if has_index("qseal_parameters", "ix_qseal_parameters_serial_number"):
        op.drop_index(
            "ix_qseal_parameters_serial_number", table_name="qseal_parameters"
        )
