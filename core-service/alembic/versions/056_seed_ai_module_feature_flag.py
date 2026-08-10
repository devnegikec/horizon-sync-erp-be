"""seed ai_module_enabled feature flag (hidden + disabled by default)

Revision ID: 056_seed_ai_module_feature_flag
Revises: 055_fix_product_items_token_id_column
Create Date: 2026-06-07 10:40:00.000000

Seeds a GLOBAL-scoped feature flag `ai_module_enabled` that gates the AI
Hub (ASN ingestion, SOP Copilot, discrepancy detection, MCP tools).

It is seeded with enabled=false and visible=false so the AI tab stays
hidden for every organization user — including admins and owners — until
an administrator explicitly turns it on. Idempotent: only inserts when the
flag does not already exist, and never overwrites an existing row.
"""
import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "056_seed_ai_module_feature_flag"
down_revision = "055_fix_product_items_token_id_column"
branch_labels = None
depends_on = None


FLAG_NAME = "ai_module_enabled"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("feature_flags"):
        return

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO feature_flags
                (id, name, description, enabled, visible, scope,
                 tenant_id, user_id, rollout_percentage, created_at, updated_at)
            SELECT
                gen_random_uuid(), :name,
                'Gates the AI Hub (ASN ingestion, SOP Copilot, discrepancy '
                'detection, MCP tools). Hidden by default for all users.',
                false, false, 'GLOBAL', NULL, NULL, NULL, now(), now()
            WHERE NOT EXISTS (
                SELECT 1 FROM feature_flags
                WHERE name = :name AND scope = 'GLOBAL'
                  AND tenant_id IS NULL AND user_id IS NULL
            )
            """
        ),
        {"name": FLAG_NAME},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM feature_flags "
            "WHERE name = :name AND scope = 'GLOBAL' "
            "AND tenant_id IS NULL AND user_id IS NULL"
        ),
        {"name": FLAG_NAME},
    )
