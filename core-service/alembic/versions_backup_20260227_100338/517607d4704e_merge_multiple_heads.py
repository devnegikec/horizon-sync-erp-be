"""merge multiple heads

Revision ID: 517607d4704e
Revises: 688600c42d82, p8q7r6s5t4u3
Create Date: 2026-02-26 22:28:25.088236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '517607d4704e'
down_revision: Union[str, None] = ('688600c42d82', 'p8q7r6s5t4u3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
