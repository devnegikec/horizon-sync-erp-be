"""Add tax columns to quotation_items table

Revision ID: 007
Revises: 006
Create Date: 2026-02-17

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("quotation_items")]

    if "tax_template_id" not in columns:
        op.add_column(
            "quotation_items",
            sa.Column(
                "tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "quotation_items_tax_template_id_fkey",
            "quotation_items",
            "tax_templates",
            ["tax_template_id"],
            ["id"],
        )

    if "tax_rate" not in columns:
        op.add_column(
            "quotation_items",
            sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True, server_default="0"),
        )

    if "tax_amount" not in columns:
        op.add_column(
            "quotation_items",
            sa.Column(
                "tax_amount", sa.Numeric(15, 2), nullable=True, server_default="0"
            ),
        )

    if "total_amount" not in columns:
        op.add_column(
            "quotation_items",
            sa.Column(
                "total_amount",
                sa.Numeric(15, 2),
                nullable=True,
            ),
        )
        # Backfill: total_amount = amount for existing rows
        op.execute(
            "UPDATE quotation_items SET total_amount = amount WHERE total_amount IS NULL"
        )
        op.alter_column(
            "quotation_items",
            "total_amount",
            existing_type=sa.Numeric(15, 2),
            nullable=False,
            server_default=sa.text("0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("quotation_items")]

    if "total_amount" in columns:
        op.drop_column("quotation_items", "total_amount")

    if "tax_amount" in columns:
        op.drop_column("quotation_items", "tax_amount")

    if "tax_rate" in columns:
        op.drop_column("quotation_items", "tax_rate")

    if "tax_template_id" in columns:
        op.drop_constraint(
            "quotation_items_tax_template_id_fkey",
            "quotation_items",
            type_="foreignkey",
        )
        op.drop_column("quotation_items", "tax_template_id")
