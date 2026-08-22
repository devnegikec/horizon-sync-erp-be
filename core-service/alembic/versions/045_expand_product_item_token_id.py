"""Expand ProductItem token_id for signed QR URLs.

Revision ID: 045_expand_item_token_id
Revises: 044_qr_block_artifacts
Create Date: 2026-08-04
"""

import sqlalchemy as sa

from alembic import op

revision = "045_expand_item_token_id"
down_revision = "044_qr_block_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "product_items",
        "token_id",
        existing_type=sa.String(length=75),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "product_items",
        "token_id",
        existing_type=sa.Text(),
        type_=sa.String(length=75),
        existing_nullable=True,
    )
