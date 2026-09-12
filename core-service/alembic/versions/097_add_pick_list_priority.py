"""Add prioritization + task-aging columns to pick_lists

Revision ID: 097_add_pick_list_priority
Revises: 096_add_handling_units
Create Date: 2026-08-30

Adds the priority/cutoff/wave/route/SLA fields used for task prioritization
(WF-007) and task aging (ALT-011) on pick lists (PR-12 / T-12).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "097_add_pick_list_priority"
down_revision: str | Sequence[str] | None = "096_add_handling_units"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("pick_lists"):
        return

    if not has_column("pick_lists", "priority"):
        op.add_column(
            "pick_lists",
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        )
    if not has_column("pick_lists", "dispatch_cutoff"):
        op.add_column(
            "pick_lists",
            sa.Column("dispatch_cutoff", sa.DateTime(timezone=True), nullable=True),
        )
    if not has_column("pick_lists", "wave"):
        op.add_column(
            "pick_lists",
            sa.Column("wave", sa.String(length=100), nullable=True),
        )
    if not has_column("pick_lists", "route"):
        op.add_column(
            "pick_lists",
            sa.Column("route", sa.String(length=100), nullable=True),
        )
    if not has_column("pick_lists", "sla_minutes"):
        op.add_column(
            "pick_lists",
            sa.Column("sla_minutes", sa.Integer(), nullable=True),
        )

    op.create_index("ix_pick_lists_priority", "pick_lists", ["priority"])
    op.create_index("ix_pick_lists_dispatch_cutoff", "pick_lists", ["dispatch_cutoff"])


def downgrade() -> None:
    if has_table("pick_lists"):
        op.drop_index("ix_pick_lists_priority", table_name="pick_lists")
        op.drop_index("ix_pick_lists_dispatch_cutoff", table_name="pick_lists")

    if has_column("pick_lists", "priority"):
        op.drop_column("pick_lists", "priority")
    if has_column("pick_lists", "dispatch_cutoff"):
        op.drop_column("pick_lists", "dispatch_cutoff")
    if has_column("pick_lists", "wave"):
        op.drop_column("pick_lists", "wave")
    if has_column("pick_lists", "route"):
        op.drop_column("pick_lists", "route")
    if has_column("pick_lists", "sla_minutes"):
        op.drop_column("pick_lists", "sla_minutes")
