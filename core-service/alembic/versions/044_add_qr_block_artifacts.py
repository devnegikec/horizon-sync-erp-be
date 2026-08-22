"""Add durable QR Block artifact metadata.

Revision ID: 044_qr_block_artifacts
Revises: 043_qr_credit_management
Create Date: 2026-08-04
"""

import sqlalchemy as sa

from alembic import op

revision = "044_qr_block_artifacts"
down_revision = "043_qr_credit_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "qr_blocks",
        sa.Column("artifact_object_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "qr_blocks",
        sa.Column("artifact_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "qr_blocks",
        sa.Column(
            "artifact_checksum_sha256",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "qr_blocks",
        sa.Column(
            "artifact_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("qr_blocks", "artifact_generated_at")
    op.drop_column("qr_blocks", "artifact_checksum_sha256")
    op.drop_column("qr_blocks", "artifact_size_bytes")
    op.drop_column("qr_blocks", "artifact_object_key")
