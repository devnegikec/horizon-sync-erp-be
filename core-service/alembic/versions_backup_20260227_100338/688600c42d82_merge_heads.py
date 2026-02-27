"""merge_heads

Revision ID: 688600c42d82
Revises: bc78b582cd1f, de19fec2730f
Create Date: 2026-02-26 18:43:24.959904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '688600c42d82'
down_revision: Union[str, None] = ('bc78b582cd1f', 'de19fec2730f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
