"""add audit fields and enum to qr_activation_tracks

Revision ID: 540a6ccc80c0
Revises: 039_add_audit_logs_table
Create Date: 2026-04-20 22:23:55.927454
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '540a6ccc80c0'
down_revision: str | None = '039_add_audit_logs_table'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----------------------------
    # 1. Create Enum type
    # ----------------------------
    qr_type_enum = postgresql.ENUM(
        'shipper',
        'pallet',
        'container',
        name='qr_type_enum'
    )
    qr_type_enum.create(op.get_bind())

    # ----------------------------
    # 2. Alter qr_type column (String -> Enum)
    # ----------------------------
    op.alter_column(
        'qr_activation_tracks',
        'qr_type',
        type_=qr_type_enum,
        postgresql_using='qr_type::text::qr_type_enum'
    )

    # ----------------------------
    # 3. Add audit fields
    # ----------------------------
    op.add_column(
        'qr_activation_tracks',
        sa.Column('created_by', sa.UUID(), nullable=True)
    )
    op.add_column(
        'qr_activation_tracks',
        sa.Column('updated_by', sa.UUID(), nullable=True)
    )
    op.add_column(
        'qr_activation_tracks',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'qr_activation_tracks',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # ----------------------------
    # 4. Alter qr_code_link (Text -> String(600))
    # ----------------------------
    op.alter_column(
        'qr_activation_tracks',
        'qr_code_link',
        type_=sa.String(length=600)
    )

    # ----------------------------
    # 5. Add index on serial_number
    # ----------------------------
    op.create_index(
        'ix_qr_activation_tracks_serial_number',
        'qr_activation_tracks',
        ['serial_number']
    )


def downgrade() -> None:
    # ----------------------------
    # 1. Drop index
    # ----------------------------
    op.drop_index(
        'ix_qr_activation_tracks_serial_number',
        table_name='qr_activation_tracks'
    )

    # ----------------------------
    # 2. Revert qr_code_link type
    # ----------------------------
    op.alter_column(
        'qr_activation_tracks',
        'qr_code_link',
        type_=sa.Text()
    )

    # ----------------------------
    # 3. Drop audit fields
    # ----------------------------
    op.drop_column('qr_activation_tracks', 'deleted_at')
    op.drop_column('qr_activation_tracks', 'updated_at')
    op.drop_column('qr_activation_tracks', 'updated_by')
    op.drop_column('qr_activation_tracks', 'created_by')

    # ----------------------------
    # 4. Revert qr_type Enum -> String
    # ----------------------------
    op.alter_column(
        'qr_activation_tracks',
        'qr_type',
        type_=sa.String(length=25)
    )

    # Drop enum type
    qr_type_enum = postgresql.ENUM(
        'shipper',
        'pallet',
        'container',
        name='qr_type_enum'
    )
    qr_type_enum.drop(op.get_bind())
