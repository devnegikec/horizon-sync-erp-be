"""Add the missing item_groups default fields and merge the 132 heads.

Revision ID: 133_item_group_default_fields
Revises: 132_add_system_config, 132_exchange_rate_org_scope
Create Date: 2026-10-01

The ``ItemGroup`` model has declared ``default_valuation_method``,
``default_uom``, ``sales_tax_template_id`` and ``purchase_tax_template_id``, but
**no migration ever created them**. They only exist in databases that were
bootstrapped with the legacy ``core-service/scripts/*.sql`` files (which is how
the staging database was built).

Any database built purely from Alembic — i.e. every freshly provisioned
environment — therefore raises ``UndefinedColumn`` the moment an ``ItemGroup`` is
queried. That breaks ``POST /api/v1/setup/organization-defaults`` (organization
onboarding), which in turn blocks creating items and warehouses for a new org.

This migration:
  1. merges the two ``132_*`` heads (``132_add_system_config`` and
     ``132_exchange_rate_org_scope``) back into a single head, and
  2. adds the four columns with the same definitions the staging database has.

Every step is guarded, so it is a no-op on databases that already have the
columns.
"""

from sqlalchemy import Column, text
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "133_item_group_default_fields"
down_revision = ("132_add_system_config", "132_exchange_rate_org_scope")
branch_labels = None
depends_on = None

COLUMNS = {
    "default_valuation_method": postgresql.ENUM(
        name="valuationmethod", create_type=False
    ),
    "default_uom": postgresql.VARCHAR(length=50),
    "sales_tax_template_id": postgresql.UUID(as_uuid=True),
    "purchase_tax_template_id": postgresql.UUID(as_uuid=True),
}

FKS = (
    ("item_groups_sales_tax_template_id_fkey", "sales_tax_template_id"),
    ("item_groups_purchase_tax_template_id_fkey", "purchase_tax_template_id"),
)


def _has_table(conn, table: str) -> bool:
    return (
        conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar()
        is not None
    )


def _has_column(conn, table: str, column: str) -> bool:
    return (
        conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        ).fetchone()
        is not None
    )


def _has_constraint(conn, name: str) -> bool:
    return (
        conn.execute(
            text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": name}
        ).fetchone()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _has_table(conn, "item_groups"):
        return

    for column, type_ in COLUMNS.items():
        if not _has_column(conn, "item_groups", column):
            op.add_column("item_groups", Column(column, type_, nullable=True))

    if not _has_table(conn, "tax_templates"):
        return

    for name, column in FKS:
        if _has_column(conn, "item_groups", column) and not _has_constraint(conn, name):
            op.create_foreign_key(
                name, "item_groups", "tax_templates", [column], ["id"]
            )


def downgrade():
    conn = op.get_bind()
    if not _has_table(conn, "item_groups"):
        return

    for name, _column in FKS:
        if _has_constraint(conn, name):
            op.drop_constraint(name, "item_groups", type_="foreignkey")

    for column in COLUMNS:
        if _has_column(conn, "item_groups", column):
            op.drop_column("item_groups", column)
