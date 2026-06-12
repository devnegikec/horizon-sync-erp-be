"""Add wms_workers and wms_devices tables

Revision ID: 057_add_wms_workers_and_devices
Revises: 056_create_missing_erp_tables
Create Date: 2026-06-11

Creates:
  - wms_workers table for warehouse worker management with barcode login
  - wms_devices table for warehouse device management
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table, has_type

# revision identifiers, used by Alembic.
revision = "057_add_wms_workers_and_devices"
down_revision = "056_create_missing_erp_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create wmsworkerstatus enum
    if not has_type("wmsworkerstatus"):
        op.execute(
            "CREATE TYPE wmsworkerstatus AS ENUM ('active', 'inactive', 'disabled')"
        )

    # Create wmsdevicestatus enum
    if not has_type("wmsdevicestatus"):
        op.execute(
            "CREATE TYPE wmsdevicestatus AS ENUM ('active', 'inactive', 'maintenance')"
        )

    if not has_table("wms_workers"):
        op.create_table(
            "wms_workers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("first_name", sa.String(100), nullable=False),
            sa.Column("last_name", sa.String(100), nullable=False),
            sa.Column("display_name", sa.String(200), nullable=True),
            sa.Column("email", sa.String(255), nullable=True, index=True),
            sa.Column("phone", sa.String(20), nullable=True),
            sa.Column("login_username", sa.String(100), nullable=True, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=True),
            sa.Column("barcode", sa.String(100), nullable=True, index=True, unique=True),
            sa.Column("role", sa.String(50), nullable=False, server_default="operator"),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "active", "inactive", "disabled",
                    name="wmsworkerstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="active",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        )

    if not has_table("wms_devices"):
        op.create_table(
            "wms_devices",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("device_code", sa.String(100), nullable=False, index=True),
            sa.Column("device_type", sa.String(100), nullable=True),
            sa.Column("manufacturer", sa.String(255), nullable=True),
            sa.Column("model", sa.String(255), nullable=True),
            sa.Column("serial_number", sa.String(255), nullable=True),
            sa.Column("os_version", sa.String(100), nullable=True),
            sa.Column("assigned_to_worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wms_workers.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "active", "inactive", "maintenance",
                    name="wmsdevicestatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="active",
            ),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    if has_table("wms_devices"):
        op.drop_table("wms_devices")
    if has_table("wms_workers"):
        op.drop_table("wms_workers")
    if has_type("wmsdevicestatus"):
        op.execute("DROP TYPE IF EXISTS wmsdevicestatus")
    if has_type("wmsworkerstatus"):
        op.execute("DROP TYPE IF EXISTS wmsworkerstatus")
