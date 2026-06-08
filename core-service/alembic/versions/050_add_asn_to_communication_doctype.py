"""add_asn_to_communication_doctype

Revision ID: 050_add_asn_to_communication_doctype
Revises: 049_add_asn_orders_table
Create Date: 2026-05-28 15:46:55.550308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '050_add_asn_to_communication_doctype'
down_revision: Union[str, None] = '049_add_asn_orders_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    op.execute("ALTER TYPE communicationdoctype ADD VALUE 'asn';")


def downgrade() -> None:
    # PostgreSQL does not support dropping individual enum values.
    # To remove 'asn', the enum would need to be fully recreated.
    pass
