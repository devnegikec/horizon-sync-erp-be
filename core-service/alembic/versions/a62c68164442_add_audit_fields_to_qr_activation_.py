"""add audit fields to qr_activation_parameters

Revision ID: a62c68164442
Revises: e18bb13c20f4
Create Date: 2026-04-21 06:18:13.295142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a62c68164442'
down_revision: Union[str, None] = 'e18bb13c20f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'qr_activation_parameters',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column(
        'qr_activation_parameters',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('qr_activation_parameters', 'deleted_at')
    op.drop_column('qr_activation_parameters', 'updated_at')