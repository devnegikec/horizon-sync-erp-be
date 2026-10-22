"""Add item-group columns used by the current ORM model.

Revision ID: 117_add_missing_item_group_columns
Revises: 116_add_qseal_suspicion_fields

The item-group model gained valuation and tax-template fields, but the
corresponding migration was never added.  On databases created from the
older baseline, any item-group insert therefore failed with an undefined
column error and was returned as HTTP 503 by the database error handler.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.alembic_guards import has_column, has_constraint, has_table, has_type

revision: str = "117_add_missing_item_group_columns"
down_revision: str | Sequence[str] | None = "116_add_qseal_suspicion_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_foreign_key(name: str, column: str) -> None:
    if (
        has_table("tax_templates")
        and has_column("item_groups", column)
        and not has_constraint("item_groups", name)
    ):
        op.create_foreign_key(
            name,
            "item_groups",
            "tax_templates",
            [column],
            ["id"],
        )


def upgrade() -> None:
    if not has_table("item_groups"):
        return

    if not has_column("item_groups", "default_valuation_method"):
        valuation_type = postgresql.ENUM(
            "fifo",
            "lifo",
            "moving_average",
            "standard",
            name="valuationmethod",
            create_type=False,
        )
        if not has_type("valuationmethod"):
            op.execute(
                "CREATE TYPE valuationmethod AS ENUM "
                "('fifo', 'lifo', 'moving_average', 'standard')"
            )
        op.add_column(
            "item_groups",
            sa.Column("default_valuation_method", valuation_type, nullable=True),
        )

    for column in ("sales_tax_template_id", "purchase_tax_template_id"):
        if not has_column("item_groups", column):
            op.add_column(
                "item_groups",
                sa.Column(
                    column,
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )

    _add_foreign_key(
        "fk_item_groups_sales_tax_template_id_tax_templates",
        "sales_tax_template_id",
    )
    _add_foreign_key(
        "fk_item_groups_purchase_tax_template_id_tax_templates",
        "purchase_tax_template_id",
    )


def downgrade() -> None:
    for name, column in (
        (
            "fk_item_groups_purchase_tax_template_id_tax_templates",
            "purchase_tax_template_id",
        ),
        (
            "fk_item_groups_sales_tax_template_id_tax_templates",
            "sales_tax_template_id",
        ),
    ):
        if has_constraint("item_groups", name):
            op.drop_constraint(name, "item_groups", type_="foreignkey")
        if has_column("item_groups", column):
            op.drop_column("item_groups", column)

    if has_column("item_groups", "default_valuation_method"):
        op.drop_column("item_groups", "default_valuation_method")
