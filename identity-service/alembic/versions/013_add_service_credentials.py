"""Add service_credentials table for machine-to-machine auth

Revision ID: 013
Revises: 012_add_wms_resourcetype_enum_values
Create Date: 2026-06-01 21:45:00

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i["name"] == index_name for i in inspector.get_indexes(table_name))

    if not inspector.has_table("service_credentials"):
        op.create_table(
            "service_credentials",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("client_id", sa.String(255), nullable=False, unique=True),
            sa.Column("client_secret_hash", sa.String(255), nullable=False),
            sa.Column("service_name", sa.String(255), nullable=False),
            sa.Column("permissions", postgresql.JSONB, nullable=False, server_default="[]"),
            sa.Column("scopes", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_index("service_credentials", "ix_service_credentials_client_id"):
        op.create_index("ix_service_credentials_client_id", "service_credentials", ["client_id"])
    if not _has_index("service_credentials", "ix_service_credentials_active"):
        op.create_index(
            "ix_service_credentials_active", "service_credentials", ["is_active", "client_id"]
        )


def downgrade() -> None:
    op.drop_index("ix_service_credentials_active", table_name="service_credentials")
    op.drop_index("ix_service_credentials_client_id", table_name="service_credentials")
    op.drop_table("service_credentials")
