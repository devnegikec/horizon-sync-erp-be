"""Add pick_settings table

Revision ID: 091_add_pick_settings
Revises: 090_add_qr_code_to_warehouse_locations
Create Date: 2026-08-28

Adds the tenant-scoped ``pick_settings`` table (PR-02 / T-17) backing the
``pick.*`` config keys. One row per (organization, key) override; values are
stored as JSON to support bool / int / float / enum / list types.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "091_add_pick_settings"
down_revision: str | Sequence[str] | None = "090_add_qr_code_to_warehouse_locations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("pick_settings"):
        return

    op.create_table(
        "pick_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "key", name="uq_pick_settings_org_key"
        ),
    )
    op.create_index(
        "ix_pick_settings_organization_id",
        "pick_settings",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pick_settings_organization_id", table_name="pick_settings"
    )
    op.drop_table("pick_settings")
