"""add audit fields to qr_activation_parameters

Revision ID: 042_add_audit_fields_to_qr_activation
Revises: 041_add_parent_relation_to_qr_activation
Create Date: 2026-04-21 06:18:13.295142

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '042_add_audit_fields_to_qr_activation'
down_revision: str | None = '041_add_parent_relation_to_qr_activation'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
