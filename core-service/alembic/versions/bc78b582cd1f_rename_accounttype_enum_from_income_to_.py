"""Rename_accounttype_enum_from_income_to_revenue

Revision ID: bc78b582cd1f
Revises: 510768f71563
Create Date: 2026-02-26 11:12:37.481471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc78b582cd1f'
down_revision: Union[str, None] = '510768f71563'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE accounttype RENAME VALUE 'income' TO 'revenue';")


def downgrade() -> None:
    op.execute("ALTER TYPE accounttype RENAME VALUE 'revenue' TO 'income';")
