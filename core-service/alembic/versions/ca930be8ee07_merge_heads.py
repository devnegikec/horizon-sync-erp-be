"""merge_heads

Revision ID: ca930be8ee07
Revises: 008, 729ac5afda0a, h8i9j0k1l2m3
Create Date: 2026-02-19 18:05:42.094447

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca930be8ee07'
down_revision: Union[str, None] = ('008', '729ac5afda0a', 'h8i9j0k1l2m3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
