"""add converted_to_sales_order to quotations

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-02-19 10:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6g7h8i9j0k1"
down_revision: Union[str, None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add converted_to_sales_order column to quotations table"""
    op.add_column(
        "quotations",
        sa.Column(
            "converted_to_sales_order",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "idx_quotations_converted_to_sales_order",
        "quotations",
        ["converted_to_sales_order"],
    )


def downgrade() -> None:
    """Remove converted_to_sales_order column from quotations table"""
    op.drop_index("idx_quotations_converted_to_sales_order", table_name="quotations")
    op.drop_column("quotations", "converted_to_sales_order")
