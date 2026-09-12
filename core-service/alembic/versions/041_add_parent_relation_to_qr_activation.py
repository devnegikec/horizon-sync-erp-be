"""add parent relation to qr_activation_parameters

Revision ID: 041_add_parent_relation_to_qr_activation
Revises: 040_add_audit_fields_and_enum_to_qr
Create Date: 2026-04-21 05:38:06.234844

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '041_add_parent_relation_to_qr_activation'
down_revision: str | None = '040_add_audit_fields_and_enum_to_qr'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
