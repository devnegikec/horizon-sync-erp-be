"""Add pick_exceptions and pick_exception_audit tables

Revision ID: 092_add_pick_exceptions
Revises: 091_add_pick_settings
Create Date: 2026-08-29

Adds the reason-code & exception framework (PR-03 / T-02) plus the immutable
audit trail for exceptions/approvals/overrides (PR-03 / T-05, WF-023 / NFR-005).

``pick_exceptions`` holds one row per reason-coded exception raised against a
pick list item. ``pick_exception_audit`` is append-only: the service layer only
ever inserts rows, never updates or deletes them.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "092_add_pick_exceptions"
down_revision: str | Sequence[str] | None = "091_add_pick_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid() -> sa.types.TypeEngine:
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    if not has_table("pick_exceptions"):
        op.create_table(
            "pick_exceptions",
            sa.Column("id", _uuid(), nullable=False),
            sa.Column("organization_id", _uuid(), nullable=False),
            sa.Column("pick_list_id", _uuid(), nullable=False),
            sa.Column("pick_list_item_id", _uuid(), nullable=False),
            sa.Column("reason_code", sa.String(length=80), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("reported_by", _uuid(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("approver", _uuid(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("quantity", sa.Numeric(15, 3), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            sa.ForeignKeyConstraint(
                ["pick_list_id"], ["pick_lists.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["pick_list_item_id"],
                ["pick_list_items.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_pick_exceptions_organization_id",
            "pick_exceptions",
            ["organization_id"],
        )
        op.create_index(
            "ix_pick_exceptions_pick_list_id",
            "pick_exceptions",
            ["pick_list_id"],
        )
        op.create_index(
            "ix_pick_exceptions_pick_list_item_id",
            "pick_exceptions",
            ["pick_list_item_id"],
        )
        op.create_index(
            "ix_pick_exceptions_reason_code", "pick_exceptions", ["reason_code"]
        )
        op.create_index("ix_pick_exceptions_severity", "pick_exceptions", ["severity"])
        op.create_index(
            "ix_pick_exceptions_reported_by", "pick_exceptions", ["reported_by"]
        )
        op.create_index("ix_pick_exceptions_status", "pick_exceptions", ["status"])
        op.create_index("ix_pick_exceptions_approver", "pick_exceptions", ["approver"])
        op.create_index(
            "ix_pick_exceptions_created_at", "pick_exceptions", ["created_at"]
        )

    if not has_table("pick_exception_audit"):
        op.create_table(
            "pick_exception_audit",
            sa.Column("id", _uuid(), nullable=False),
            sa.Column("organization_id", _uuid(), nullable=False),
            sa.Column("exception_id", _uuid(), nullable=False),
            sa.Column("event_type", sa.String(length=40), nullable=False),
            sa.Column("actor_id", _uuid(), nullable=True),
            sa.Column("from_state", sa.String(length=30), nullable=True),
            sa.Column("to_state", sa.String(length=30), nullable=True),
            sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["exception_id"], ["pick_exceptions.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_pick_exception_audit_organization_id",
            "pick_exception_audit",
            ["organization_id"],
        )
        op.create_index(
            "ix_pick_exception_audit_exception_id",
            "pick_exception_audit",
            ["exception_id"],
        )
        op.create_index(
            "ix_pick_exception_audit_event_type",
            "pick_exception_audit",
            ["event_type"],
        )
        op.create_index(
            "ix_pick_exception_audit_actor_id",
            "pick_exception_audit",
            ["actor_id"],
        )
        op.create_index(
            "ix_pick_exception_audit_created_at",
            "pick_exception_audit",
            ["created_at"],
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pick_exception_audit")
    op.execute("DROP TABLE IF EXISTS pick_exceptions")
