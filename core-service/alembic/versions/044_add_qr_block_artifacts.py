"""Add durable QR Block artifact metadata.

Revision ID: 044_qr_block_artifacts
Revises: 043_qr_credit_management
Create Date: 2026-08-04
"""

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_table

revision = "044_qr_block_artifacts"
down_revision = "043_qr_credit_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table("qr_blocks"):
        return
    columns = (
        ("artifact_object_key", sa.Text()),
        ("artifact_size_bytes", sa.BigInteger()),
        ("artifact_checksum_sha256", sa.String(length=64)),
        ("artifact_generated_at", sa.DateTime(timezone=True)),
    )
    for name, column_type in columns:
        if not has_column("qr_blocks", name):
            op.add_column("qr_blocks", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    op.drop_column("qr_blocks", "artifact_generated_at")
    op.drop_column("qr_blocks", "artifact_checksum_sha256")
    op.drop_column("qr_blocks", "artifact_size_bytes")
    op.drop_column("qr_blocks", "artifact_object_key")
