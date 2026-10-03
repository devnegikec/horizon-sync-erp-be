"""Add pick_idempotency_keys table

Revision ID: 093_add_pick_idempotency
Revises: 092_add_pick_exceptions
Create Date: 2026-08-29

Adds the server-side dedup table for idempotent pick mutations (PR-04 / T-04,
NFR-003 + EX-017). One row per (organization, operation, idempotency_key);
the successful response is stored as JSON so a replay returns the same result
without re-executing the mutation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "093_add_pick_idempotency"
down_revision: str | Sequence[str] | None = "092_add_pick_exceptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if has_table("pick_idempotency_keys"):
        return

    op.create_table(
        "pick_idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("pick_list_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=True),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
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
            "organization_id",
            "operation",
            "idempotency_key",
            name="uq_pick_idempotency_org_op_key",
        ),
    )
    op.create_index(
        "ix_pick_idempotency_organization_id",
        "pick_idempotency_keys",
        ["organization_id"],
    )
    op.create_index(
        "ix_pick_idempotency_pick_list_id",
        "pick_idempotency_keys",
        ["pick_list_id"],
    )
    op.create_index(
        "ix_pick_idempotency_created_at",
        "pick_idempotency_keys",
        ["created_at"],
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pick_idempotency_keys")
