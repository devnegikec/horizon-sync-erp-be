"""add parent relation to qr_activation_parameters

Revision ID: e18bb13c20f4
Revises: 540a6ccc80c0
Create Date: 2026-04-21 05:38:06.234844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e18bb13c20f4'
down_revision: Union[str, None] = '540a6ccc80c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'qr_activation_parameters',
        sa.Column('parent_id', sa.UUID(), nullable=True)
    )

    op.add_column(
        'qr_activation_parameters',
        sa.Column('parent_app_id', sa.UUID(), nullable=True)
    )

    op.create_foreign_key(
        'fk_qr_params_parent_id',
        'qr_activation_parameters',
        'qr_activation_tracks',
        ['parent_id'],
        ['id']
    )

    op.create_foreign_key(
        'fk_qr_params_parent_app_id',
        'qr_activation_parameters',
        'qr_activation_tracks',
        ['parent_app_id'],
        ['id']
    )

    


def downgrade() -> None:
    pass
