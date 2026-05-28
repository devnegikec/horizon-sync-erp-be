"""add_asn_to_communication_doctype

Revision ID: 4672f880d63d
Revises: 048_add_asn_orders_table
Create Date: 2026-05-28 15:46:55.550308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4672f880d63d'
down_revision: Union[str, None] = '048_add_asn_orders_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE communicationdoctype ADD VALUE 'asn';")


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    # To remove 'asn', the enum would need to be fully recreated.
    pass
