"""Add qr_cta_configs table for configurable Call-to-Action buttons

Revision ID: 063_add_qr_cta_configs
Revises: 062_enhance_qr_scan_events
Create Date: 2026-07-13
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "063_add_qr_cta_configs"
down_revision: Union[str, None] = "062_enhance_qr_scan_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not has_table("qr_cta_configs"):
        op.create_table(
            "qr_cta_configs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column(
                "product_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qr_products.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "cta_type",
                sa.String(50),
                nullable=False,
            ),
            sa.Column(
                "cta_label",
                sa.String(100),
                nullable=False,
            ),
            sa.Column(
                "cta_target",
                sa.Text,
                nullable=True,
            ),
            sa.Column(
                "display_order",
                sa.Integer,
                server_default="0",
            ),
            sa.Column(
                "is_active",
                sa.Boolean,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.create_index("idx_cta_configs_org", "qr_cta_configs", ["organization_id"])
        op.create_index("idx_cta_configs_product", "qr_cta_configs", ["product_id"])


def downgrade() -> None:
    if has_table("qr_cta_configs"):
        op.drop_table("qr_cta_configs")
