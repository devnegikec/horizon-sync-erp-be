"""Extend existing tables for tax and charges

Revision ID: 006
Revises: 005
Create Date: 2026-01-27 11:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get inspector to check existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add columns to items table
    items_columns = [col["name"] for col in inspector.get_columns("items")]
    if "sales_tax_template_id" not in items_columns:
        op.add_column(
            "items",
            sa.Column(
                "sales_tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "items_sales_tax_template_id_fkey",
            "items",
            "tax_templates",
            ["sales_tax_template_id"],
            ["id"],
        )

    if "purchase_tax_template_id" not in items_columns:
        op.add_column(
            "items",
            sa.Column(
                "purchase_tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "items_purchase_tax_template_id_fkey",
            "items",
            "tax_templates",
            ["purchase_tax_template_id"],
            ["id"],
        )

    # Add columns to item_groups table
    item_groups_columns = [col["name"] for col in inspector.get_columns("item_groups")]
    if "sales_tax_template_id" not in item_groups_columns:
        op.add_column(
            "item_groups",
            sa.Column(
                "sales_tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "item_groups_sales_tax_template_id_fkey",
            "item_groups",
            "tax_templates",
            ["sales_tax_template_id"],
            ["id"],
        )

    if "purchase_tax_template_id" not in item_groups_columns:
        op.add_column(
            "item_groups",
            sa.Column(
                "purchase_tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "item_groups_purchase_tax_template_id_fkey",
            "item_groups",
            "tax_templates",
            ["purchase_tax_template_id"],
            ["id"],
        )

    # Create organization_settings table if it doesn't exist
    tables = inspector.get_table_names()
    if "organization_settings" not in tables:
        op.create_table(
            "organization_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "default_sales_tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column(
                "default_purchase_tax_template_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create index on organization_id
        op.create_index(
            op.f("ix_organization_settings_organization_id"),
            "organization_settings",
            ["organization_id"],
            unique=True,
        )

        # Create foreign keys for tax templates
        op.create_foreign_key(
            "organization_settings_default_sales_tax_template_id_fkey",
            "organization_settings",
            "tax_templates",
            ["default_sales_tax_template_id"],
            ["id"],
        )
        op.create_foreign_key(
            "organization_settings_default_purchase_tax_template_id_fkey",
            "organization_settings",
            "tax_templates",
            ["default_purchase_tax_template_id"],
            ["id"],
        )
    else:
        # If table exists, add columns if they don't exist
        org_settings_columns = [
            col["name"] for col in inspector.get_columns("organization_settings")
        ]
        if "default_sales_tax_template_id" not in org_settings_columns:
            op.add_column(
                "organization_settings",
                sa.Column(
                    "default_sales_tax_template_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
            op.create_foreign_key(
                "organization_settings_default_sales_tax_template_id_fkey",
                "organization_settings",
                "tax_templates",
                ["default_sales_tax_template_id"],
                ["id"],
            )

        if "default_purchase_tax_template_id" not in org_settings_columns:
            op.add_column(
                "organization_settings",
                sa.Column(
                    "default_purchase_tax_template_id",
                    postgresql.UUID(as_uuid=True),
                    nullable=True,
                ),
            )
            op.create_foreign_key(
                "organization_settings_default_purchase_tax_template_id_fkey",
                "organization_settings",
                "tax_templates",
                ["default_purchase_tax_template_id"],
                ["id"],
            )

    # Add columns to customers table
    customers_columns = [col["name"] for col in inspector.get_columns("customers")]
    if "is_tax_exempt" not in customers_columns:
        op.add_column(
            "customers",
            sa.Column(
                "is_tax_exempt",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )

    if "tax_exemption_certificate_no" not in customers_columns:
        op.add_column(
            "customers",
            sa.Column(
                "tax_exemption_certificate_no",
                sa.String(length=100),
                nullable=True,
            ),
        )

    # Add columns to transaction tables: quotations, sales_orders, purchase_orders, invoices
    transaction_tables = ["quotations", "sales_orders", "purchase_orders", "invoices"]

    for table_name in transaction_tables:
        if table_name in tables:
            table_columns = [col["name"] for col in inspector.get_columns(table_name)]

            if "net_total" not in table_columns:
                op.add_column(
                    table_name,
                    sa.Column(
                        "net_total",
                        sa.Numeric(precision=15, scale=2),
                        nullable=False,
                        server_default="0",
                    ),
                )

            if "total_tax" not in table_columns:
                op.add_column(
                    table_name,
                    sa.Column(
                        "total_tax",
                        sa.Numeric(precision=15, scale=2),
                        nullable=False,
                        server_default="0",
                    ),
                )

            if "total_charges" not in table_columns:
                op.add_column(
                    table_name,
                    sa.Column(
                        "total_charges",
                        sa.Numeric(precision=15, scale=2),
                        nullable=False,
                        server_default="0",
                    ),
                )


def downgrade() -> None:
    # Get inspector to check existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Remove columns from transaction tables
    transaction_tables = ["quotations", "sales_orders", "purchase_orders", "invoices"]

    for table_name in transaction_tables:
        if table_name in tables:
            table_columns = [col["name"] for col in inspector.get_columns(table_name)]

            if "total_charges" in table_columns:
                op.drop_column(table_name, "total_charges")

            if "total_tax" in table_columns:
                op.drop_column(table_name, "total_tax")

            if "net_total" in table_columns:
                op.drop_column(table_name, "net_total")

    # Remove columns from customers table
    customers_columns = [col["name"] for col in inspector.get_columns("customers")]
    if "tax_exemption_certificate_no" in customers_columns:
        op.drop_column("customers", "tax_exemption_certificate_no")

    if "is_tax_exempt" in customers_columns:
        op.drop_column("customers", "is_tax_exempt")

    # Remove columns from organization_settings table (or drop table if we created it)
    if "organization_settings" in tables:
        org_settings_columns = [
            col["name"] for col in inspector.get_columns("organization_settings")
        ]
        if "default_purchase_tax_template_id" in org_settings_columns:
            op.drop_constraint(
                "organization_settings_default_purchase_tax_template_id_fkey",
                "organization_settings",
                type_="foreignkey",
            )
            op.drop_column("organization_settings", "default_purchase_tax_template_id")

        if "default_sales_tax_template_id" in org_settings_columns:
            op.drop_constraint(
                "organization_settings_default_sales_tax_template_id_fkey",
                "organization_settings",
                type_="foreignkey",
            )
            op.drop_column("organization_settings", "default_sales_tax_template_id")

    # Remove columns from item_groups table
    item_groups_columns = [col["name"] for col in inspector.get_columns("item_groups")]
    if "purchase_tax_template_id" in item_groups_columns:
        op.drop_constraint(
            "item_groups_purchase_tax_template_id_fkey",
            "item_groups",
            type_="foreignkey",
        )
        op.drop_column("item_groups", "purchase_tax_template_id")

    if "sales_tax_template_id" in item_groups_columns:
        op.drop_constraint(
            "item_groups_sales_tax_template_id_fkey",
            "item_groups",
            type_="foreignkey",
        )
        op.drop_column("item_groups", "sales_tax_template_id")

    # Remove columns from items table
    items_columns = [col["name"] for col in inspector.get_columns("items")]
    if "purchase_tax_template_id" in items_columns:
        op.drop_constraint(
            "items_purchase_tax_template_id_fkey",
            "items",
            type_="foreignkey",
        )
        op.drop_column("items", "purchase_tax_template_id")

    if "sales_tax_template_id" in items_columns:
        op.drop_constraint(
            "items_sales_tax_template_id_fkey",
            "items",
            type_="foreignkey",
        )
        op.drop_column("items", "sales_tax_template_id")
