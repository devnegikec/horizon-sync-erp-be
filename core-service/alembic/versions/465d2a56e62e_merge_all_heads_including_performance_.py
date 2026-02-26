"""merge all heads including performance indexes

Revision ID: 465d2a56e62e
Revises: 517607d4704e, 729ac5afda0a
Create Date: 2026-02-26 22:31:43.890673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '465d2a56e62e'
down_revision: Union[str, None] = ('517607d4704e', '729ac5afda0a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
