"""Add qr_product_settings lookup table

Revision ID: 033_add_qr_product_settings
Revises: 032_add_public_marketing_module
Create Date: 2026-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "033_add_qr_product_settings"
down_revision = "032_add_public_marketing_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qr_product_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setting_type", sa.String(30), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_qr_prod_settings_org", "qr_product_settings", ["organization_id"]
    )
    op.create_index(
        "idx_qr_prod_settings_type", "qr_product_settings", ["setting_type"]
    )
    op.create_unique_constraint(
        "uq_qr_prod_settings_org_type_value",
        "qr_product_settings",
        ["organization_id", "setting_type", "value"],
    )


def downgrade() -> None:
    op.drop_table("qr_product_settings")
