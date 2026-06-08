"""Add qr_product_settings lookup table

Revision ID: 033_add_qr_product_settings
Revises: 032_add_public_marketing_module
Create Date: 2026-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "033_add_qr_product_settings"
down_revision = "032_add_public_marketing_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists
    inspector = inspect(op.get_bind())
    if not inspector.has_table('qr_product_settings'):
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
    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    def _has_constraint(table_name: str, constraint_name: str) -> bool:
        return any(c['name'] == constraint_name for c in inspector.get_unique_constraints(table_name))

    if not _has_index('qr_product_settings', 'idx_qr_prod_settings_org'):
        op.create_index(
            "idx_qr_prod_settings_org", "qr_product_settings", ["organization_id"]
        )
    if not _has_index('qr_product_settings', 'idx_qr_prod_settings_type'):
        op.create_index(
            "idx_qr_prod_settings_type", "qr_product_settings", ["setting_type"]
        )
    if not _has_constraint('qr_product_settings', 'uq_qr_prod_settings_org_type_value'):
        op.create_unique_constraint(
            "uq_qr_prod_settings_org_type_value",
            "qr_product_settings",
            ["organization_id", "setting_type", "value"],
        )


def downgrade() -> None:
    op.drop_table("qr_product_settings")
