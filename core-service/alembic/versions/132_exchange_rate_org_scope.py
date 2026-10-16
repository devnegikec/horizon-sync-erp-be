"""Scope exchange rates per organization.

Revision ID: 132_exchange_rate_org_scope
Revises: 131_add_floor_plan_layout_doc
Create Date: 2026-09-29

``exchange_rates.organization_id`` existed but was not part of the unique
constraint and the API never filtered on it, so every organization shared one
global rate table (and one org could read/modify another org's rates).

This migration drops the global uniqueness on (from, to, effective_date) and
replaces it with an organization-scoped one. Null ``organization_id`` rows
remain allowed (legacy global rates) and are treated as distinct by Postgres
(NULLS DISTINCT).
"""

from alembic import op

revision = "132_exchange_rate_org_scope"
down_revision = "131_add_floor_plan_layout_doc"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "uq_exchange_rate_currency_date",
        "exchange_rates",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_exchange_rate_currency_org_date",
        "exchange_rates",
        ["from_currency", "to_currency", "effective_date", "organization_id"],
    )


def downgrade():
    op.drop_constraint(
        "uq_exchange_rate_currency_org_date",
        "exchange_rates",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_exchange_rate_currency_date",
        "exchange_rates",
        ["from_currency", "to_currency", "effective_date"],
    )
