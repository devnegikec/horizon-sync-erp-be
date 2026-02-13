"""Add customers table

Revision ID: 001_add_customers_table
Revises: 001
Create Date: 2026-02-12 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_add_customers_table"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get inspector to check if table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create enum types used in this migration - check if it exists first
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'customerstatus') THEN
                CREATE TYPE customerstatus AS ENUM ('active', 'inactive', 'blocked');
            END IF;
        END$$;
    """
    )

    # Create customers table if it doesn't exist
    if "customers" not in tables:
        op.create_table(
            "customers",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("customer_name", sa.String(length=255), nullable=False),
            sa.Column("customer_code", sa.String(length=50), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("address_line1", sa.String(length=255), nullable=True),
            sa.Column("address_line2", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=100), nullable=True),
            sa.Column("state", sa.String(length=100), nullable=True),
            sa.Column("postal_code", sa.String(length=20), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column("tax_number", sa.String(length=50), nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "active",
                    "inactive",
                    "blocked",
                    name="customerstatus",
                    create_type=False,
                ),
                nullable=True,
            ),
            sa.Column("credit_limit", sa.Numeric(precision=15, scale=2), nullable=True),
            sa.Column(
                "outstanding_balance", sa.Numeric(precision=15, scale=2), nullable=True
            ),
            sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_customers_customer_code"), "customers", ["customer_code"], unique=False
        )
        op.create_index(
            op.f("ix_customers_organization_id"),
            "customers",
            ["organization_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_customers_organization_id"), table_name="customers")
    op.drop_index(op.f("ix_customers_customer_code"), table_name="customers")
    op.drop_table("customers")
    op.execute("DROP TYPE customerstatus")
