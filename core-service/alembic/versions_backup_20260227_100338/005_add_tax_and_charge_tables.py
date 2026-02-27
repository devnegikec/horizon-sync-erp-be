"""Add tax and charge tables

Revision ID: 005
Revises: 004
Create Date: 2026-01-27 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004_add_sourcing_flow_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get inspector to check if tables exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create tax_templates table
    if "tax_templates" not in tables:
        op.create_table(
            "tax_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("template_code", sa.String(length=100), nullable=False),
            sa.Column("template_name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("tax_category", sa.String(length=50), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("applicability_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes for tax_templates
        op.create_index(
            op.f("ix_tax_templates_organization_id"),
            "tax_templates",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_tax_templates_template_code"),
            "tax_templates",
            ["template_code"],
            unique=False,
        )
        op.create_index(
            op.f("ix_tax_templates_is_default"),
            "tax_templates",
            ["is_default"],
            unique=False,
        )
        op.create_index(
            op.f("ix_tax_templates_deleted_at"),
            "tax_templates",
            ["deleted_at"],
            unique=False,
        )
        # Composite index for organization and tax_category (with WHERE clause for active templates)
        op.create_index(
            "ix_tax_templates_org_category",
            "tax_templates",
            ["organization_id", "tax_category"],
            unique=False,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )
        # Composite index for default templates
        op.create_index(
            "ix_tax_templates_default",
            "tax_templates",
            ["organization_id", "is_default", "tax_category"],
            unique=False,
            postgresql_where=sa.text("is_default = TRUE"),
        )

    # Create tax_rules table
    if "tax_rules" not in tables:
        op.create_table(
            "tax_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tax_template_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rule_name", sa.String(length=255), nullable=False),
            sa.Column("tax_type", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), nullable=False),
            sa.Column("account_head_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_compound", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("applicability_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            sa.ForeignKeyConstraint(
                ["tax_template_id"],
                ["tax_templates.id"],
                name="tax_rules_tax_template_id_fkey",
                ondelete="CASCADE",
            ),
        )

        # Create indexes for tax_rules
        op.create_index(
            op.f("ix_tax_rules_tax_template_id"),
            "tax_rules",
            ["tax_template_id"],
            unique=False,
        )
        # Composite index for template and sequence
        op.create_index(
            "ix_tax_rules_template_sequence",
            "tax_rules",
            ["tax_template_id", "sequence"],
            unique=False,
        )

    # Create charge_templates table
    if "charge_templates" not in tables:
        op.create_table(
            "charge_templates",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("template_code", sa.String(length=100), nullable=False),
            sa.Column("template_name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("charge_type", sa.String(length=50), nullable=False),
            sa.Column("calculation_method", sa.String(length=20), nullable=False),
            sa.Column("fixed_amount", sa.Numeric(precision=15, scale=2), nullable=True),
            sa.Column("percentage_rate", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("base_on", sa.String(length=20), nullable=True),
            sa.Column("account_head_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("applicability_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes for charge_templates
        op.create_index(
            op.f("ix_charge_templates_organization_id"),
            "charge_templates",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_charge_templates_template_code"),
            "charge_templates",
            ["template_code"],
            unique=False,
        )
        op.create_index(
            op.f("ix_charge_templates_charge_type"),
            "charge_templates",
            ["charge_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_charge_templates_deleted_at"),
            "charge_templates",
            ["deleted_at"],
            unique=False,
        )
        # Composite index for organization and charge_type (with WHERE clause for active templates)
        op.create_index(
            "ix_charge_templates_org_type",
            "charge_templates",
            ["organization_id", "charge_type"],
            unique=False,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    # Create transaction_tax_breakdown table
    if "transaction_tax_breakdown" not in tables:
        op.create_table(
            "transaction_tax_breakdown",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("transaction_type", sa.String(length=50), nullable=False),
            sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tax_template_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tax_rule_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tax_type", sa.String(length=100), nullable=False),
            sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), nullable=False),
            sa.Column("taxable_amount", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("tax_amount", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("is_compound", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("account_head_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["tax_template_id"],
                ["tax_templates.id"],
                name="transaction_tax_breakdown_tax_template_id_fkey",
            ),
            sa.ForeignKeyConstraint(
                ["tax_rule_id"],
                ["tax_rules.id"],
                name="transaction_tax_breakdown_tax_rule_id_fkey",
            ),
        )

        # Create indexes for transaction_tax_breakdown
        op.create_index(
            op.f("ix_transaction_tax_breakdown_organization_id"),
            "transaction_tax_breakdown",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_transaction_tax_breakdown_transaction_type"),
            "transaction_tax_breakdown",
            ["transaction_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_transaction_tax_breakdown_transaction_id"),
            "transaction_tax_breakdown",
            ["transaction_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_transaction_tax_breakdown_tax_type"),
            "transaction_tax_breakdown",
            ["tax_type"],
            unique=False,
        )
        # Composite index for transaction lookup
        op.create_index(
            "ix_trans_tax_breakdown_trans",
            "transaction_tax_breakdown",
            ["transaction_type", "transaction_id"],
            unique=False,
        )
        # Composite index for reporting
        op.create_index(
            "ix_trans_tax_breakdown_org_date",
            "transaction_tax_breakdown",
            ["organization_id", "created_at"],
            unique=False,
        )
        # Composite index for tax type reporting
        op.create_index(
            "ix_trans_tax_breakdown_tax_type",
            "transaction_tax_breakdown",
            ["organization_id", "tax_type", "created_at"],
            unique=False,
        )

    # Create transaction_charge_breakdown table
    if "transaction_charge_breakdown" not in tables:
        op.create_table(
            "transaction_charge_breakdown",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("transaction_type", sa.String(length=50), nullable=False),
            sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("charge_template_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("charge_type", sa.String(length=50), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("calculation_method", sa.String(length=20), nullable=False),
            sa.Column("charge_amount", sa.Numeric(precision=15, scale=2), nullable=False),
            sa.Column("account_head_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_auto_calculated", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["charge_template_id"],
                ["charge_templates.id"],
                name="transaction_charge_breakdown_charge_template_id_fkey",
            ),
        )

        # Create indexes for transaction_charge_breakdown
        op.create_index(
            op.f("ix_transaction_charge_breakdown_organization_id"),
            "transaction_charge_breakdown",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_transaction_charge_breakdown_transaction_type"),
            "transaction_charge_breakdown",
            ["transaction_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_transaction_charge_breakdown_transaction_id"),
            "transaction_charge_breakdown",
            ["transaction_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_transaction_charge_breakdown_charge_type"),
            "transaction_charge_breakdown",
            ["charge_type"],
            unique=False,
        )
        # Composite index for transaction lookup
        op.create_index(
            "ix_trans_charge_breakdown_trans",
            "transaction_charge_breakdown",
            ["transaction_type", "transaction_id"],
            unique=False,
        )
        # Composite index for reporting
        op.create_index(
            "ix_trans_charge_breakdown_org_date",
            "transaction_charge_breakdown",
            ["organization_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("transaction_charge_breakdown")
    op.drop_table("transaction_tax_breakdown")
    op.drop_table("charge_templates")
    op.drop_table("tax_rules")
    op.drop_table("tax_templates")
