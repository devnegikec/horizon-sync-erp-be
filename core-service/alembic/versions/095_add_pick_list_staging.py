"""Add staging columns to pick_lists

Revision ID: 095_add_pick_list_staging
Revises: 094_add_pick_exception_notification_type
Create Date: 2026-08-29

Adds the staging-lane assignment + timestamp for the outbound staging flow
(PR-10 / T-10, WF-019/020). The staging lane is a ``warehouse_locations`` row
with ``location_type = 'staging'`` (no new table).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "095_add_pick_list_staging"
down_revision: str | Sequence[str] | None = "094_add_pick_exception_notification_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("pick_lists"):
        return

    if not has_column("pick_lists", "staging_location_id"):
        op.add_column(
            "pick_lists",
            sa.Column("staging_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_pick_lists_staging_location_id",
            "pick_lists",
            "warehouse_locations",
            ["staging_location_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not has_column("pick_lists", "staged_at"):
        op.add_column(
            "pick_lists",
            sa.Column("staged_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if has_column("pick_lists", "staging_location_id"):
        op.drop_constraint(
            "fk_pick_lists_staging_location_id", "pick_lists", type_="foreignkey"
        )
        op.drop_column("pick_lists", "staging_location_id")
    if has_column("pick_lists", "staged_at"):
        op.drop_column("pick_lists", "staged_at")
