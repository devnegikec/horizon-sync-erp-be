"""Seed the ``bin_stock_show_parent_qr`` GLOBAL feature flag.

Gates the scannable parent (master-pack) QR code column shown for each batch
in the WMS bin-stock dialog. The flag is created disabled (hidden by default)
and can be enabled globally via the admin UI or per-tenant through the tenant
feature-flag override endpoint.

Revision ID: 135_add_bin_stock_parent_qr_flag
Revises: 134_qr_product_unique_sku
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_table

revision: str = "135_add_bin_stock_parent_qr_flag"
down_revision: str | Sequence[str] | None = "134_qr_product_unique_sku"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FLAG_NAME = "bin_stock_show_parent_qr"
FLAG_DESCRIPTION = (
    "Show the scannable parent (master-pack) QR code column for each batch "
    "in the WMS bin stock dialog"
)


def upgrade() -> None:
    if not has_table("feature_flags"):
        return

    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT 1 FROM feature_flags WHERE name = :name AND scope = 'GLOBAL'"),
        {"name": FLAG_NAME},
    ).first()
    if existing:
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO feature_flags
                (id, name, description, enabled, visible, scope,
                 tenant_id, user_id, rollout_percentage, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :name, :description, false, true, 'GLOBAL',
                 NULL, NULL, NULL, now(), now())
            """
        ),
        {"name": FLAG_NAME, "description": FLAG_DESCRIPTION},
    )


def downgrade() -> None:
    if not has_table("feature_flags"):
        return

    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM feature_flags WHERE name = :name AND scope = 'GLOBAL'"),
        {"name": FLAG_NAME},
    )
