"""Add missing billing/subscription columns to organizations

Revision ID: 014
Revises: 013
Create Date: 2026-06-07 11:00:00

The Organization model references several billing/subscription columns
(max_users, max_credits, customer_since, billing_cycle, trial_end_date,
next_billing_date, last_billed_date, billing_contact_email) that were never
created by an earlier migration — they only existed in older dev databases
that were restored from backups. On a freshly-migrated database these
columns are missing, so creating an organization fails with a generic
DATABASE_ERROR.

This migration adds those columns idempotently so org creation works on
any database state.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# Revision identifiers
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


# (column_name, sqlalchemy type)
_COLUMNS = [
    ("trial_end_date", sa.DateTime(timezone=False)),
    ("max_users", sa.Integer()),
    ("max_credits", sa.Integer()),
    ("billing_contact_email", sa.String(255)),
    ("billing_cycle", sa.String(20)),
    ("customer_since", sa.DateTime(timezone=True)),
    ("last_billed_date", sa.DateTime(timezone=False)),
    ("next_billing_date", sa.DateTime(timezone=False)),
    ("parent_organization_id", sa.Uuid()),
]

_PARENT_FK = "fk_organizations_parent_organization_id"


def _existing_columns(inspector, table_name: str) -> set:
    return {c["name"] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("organizations"):
        return

    existing = _existing_columns(inspector, "organizations")
    for name, col_type in _COLUMNS:
        if name not in existing:
            op.add_column("organizations", sa.Column(name, col_type, nullable=True))

    # Self-referential FK for parent_organization_id (idempotent).
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("organizations")}
    if _PARENT_FK not in fk_names:
        op.create_foreign_key(
            _PARENT_FK,
            "organizations",
            "organizations",
            ["parent_organization_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("organizations"):
        return

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("organizations")}
    if _PARENT_FK in fk_names:
        op.drop_constraint(_PARENT_FK, "organizations", type_="foreignkey")

    existing = _existing_columns(inspector, "organizations")
    for name, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("organizations", name)
