"""Add missing columns to organizations table

Revision ID: 014
Revises: 013
Create Date: 2026-07-22 12:00:00

Adds all columns present in the SQLAlchemy Organization model but missing from
the database schema, and renames seat_limit/credit_limit to max_users/max_credits.
"""

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def _add_column_if_missing(table, column_name, column_type_sql):
    op.execute(
        f"DO $$ BEGIN "
        f"IF NOT EXISTS (SELECT 1 FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column_name}') THEN "
        f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type_sql}; "
        f"END IF; END $$;"
    )


def upgrade():
    # 1. Rename seat_limit -> max_users
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='organizations' AND column_name='seat_limit') "
        "AND NOT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='organizations' AND column_name='max_users') THEN "
        "ALTER TABLE organizations RENAME COLUMN seat_limit TO max_users; "
        "END IF; END $$;"
    )

    # 2. Rename credit_limit -> max_credits
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='organizations' AND column_name='credit_limit') "
        "AND NOT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name='organizations' AND column_name='max_credits') THEN "
        "ALTER TABLE organizations RENAME COLUMN credit_limit TO max_credits; "
        "END IF; END $$;"
    )

    # 3. Add missing columns
    _add_column_if_missing(
        "organizations", "trial_end_date", "TIMESTAMP WITH TIME ZONE"
    )
    _add_column_if_missing("organizations", "billing_contact_email", "VARCHAR(255)")
    _add_column_if_missing("organizations", "billing_cycle", "VARCHAR(20)")
    _add_column_if_missing(
        "organizations", "customer_since", "TIMESTAMP WITH TIME ZONE"
    )
    _add_column_if_missing(
        "organizations", "last_billed_date", "TIMESTAMP WITH TIME ZONE"
    )
    _add_column_if_missing(
        "organizations", "next_billing_date", "TIMESTAMP WITH TIME ZONE"
    )
    _add_column_if_missing("organizations", "parent_organization_id", "UUID")

    # 4. FK for parent_organization_id
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name='fk_organizations_parent_organization_id') THEN "
        "ALTER TABLE organizations ADD CONSTRAINT fk_organizations_parent_organization_id "
        "FOREIGN KEY (parent_organization_id) REFERENCES organizations(id); "
        "END IF; END $$;"
    )

    # 5. FK for owner_id
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name='fk_organizations_owner_id') THEN "
        "ALTER TABLE organizations ADD CONSTRAINT fk_organizations_owner_id "
        "FOREIGN KEY (owner_id) REFERENCES users(id); "
        "END IF; END $$;"
    )


def downgrade():
    pass
