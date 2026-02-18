"""add_sourcing_flow_tables

Revision ID: 004_add_sourcing_flow_tables
Revises: 001_core_db_initialization
Create Date: 2026-02-18 17:45:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "004_add_sourcing_flow_tables"
down_revision: Union[str, None] = "001_core_db_initialization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
