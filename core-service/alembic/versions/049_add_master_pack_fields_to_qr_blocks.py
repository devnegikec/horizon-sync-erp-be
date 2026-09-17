"""Add master-pack configuration to QR blocks.

Revision ID: 049_qr_block_master_pack
Revises: 048_add_qr_products_sku
Create Date: 2026-08-11
"""

import sqlalchemy as sa

from alembic import op

revision = "049_qr_block_master_pack"
down_revision = "048_add_qr_products_sku"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("qr_blocks")
    }
    if "master_pack_enabled" not in columns:
        op.add_column(
            "qr_blocks",
            sa.Column(
                "master_pack_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "master_pack_size" not in columns:
        op.add_column(
            "qr_blocks",
            sa.Column("master_pack_size", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("qr_blocks")
    }
    if "master_pack_size" in columns:
        op.drop_column("qr_blocks", "master_pack_size")
    if "master_pack_enabled" in columns:
        op.drop_column("qr_blocks", "master_pack_enabled")
