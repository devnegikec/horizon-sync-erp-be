"""Rename accounttype enum from income to revenue

Revision ID: 510768f71563
Revises: 015_invoice_party_id
Create Date: 2026-02-26 11:12:24.683013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '510768f71563'
down_revision: Union[str, None] = '015_invoice_party_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
