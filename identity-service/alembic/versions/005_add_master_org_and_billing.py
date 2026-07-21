"""Add master organization support and billing fields

Revision ID: 005
Revises: 004
Create Date: 2026-03-26 15:00:00.000000

"""

import sqlalchemy as sa
from datetime import datetime, timezone
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add master organization support and billing fields"""

    # Add new enum values (PG 11+ supports ADD VALUE in transactions)
    op.execute("ALTER TYPE organizationtype ADD VALUE IF NOT EXISTS 'master'")
    op.execute("ALTER TYPE organizationtype ADD VALUE IF NOT EXISTS 'customer'")
    op.execute("ALTER TYPE organizationstatus ADD VALUE IF NOT EXISTS 'overdue'")
    op.execute("ALTER TYPE organizationstatus ADD VALUE IF NOT EXISTS 'deactivated'")

    # Add billing and subscription fields to organizations table
    op.add_column(
        "organizations",
        sa.Column(
            "billing_status",
            postgresql.ENUM(
                "active",
                "inactive",
                "suspended",
                "trial",
                "overdue",
                "deactivated",
                name="organizationstatus",
            ),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("subscription_start_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("subscription_end_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("seat_limit", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "organizations",
        sa.Column("credit_limit", sa.Integer(), nullable=False, server_default="1000"),
    )

    # Update existing organizations to have 'customer' type (except the master org we'll create)
    op.execute(
        "UPDATE organizations SET organization_type = 'customer' WHERE organization_type != 'master'"
    )

    # Create unique constraint for master organization (only one allowed)
    op.execute("""
        CREATE OR REPLACE FUNCTION check_single_master_org() RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.organization_type = 'master' THEN
                IF EXISTS (
                    SELECT 1 FROM organizations
                    WHERE organization_type = 'master'
                    AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid)
                    AND deleted_at IS NULL
                ) THEN
                    RAISE EXCEPTION 'Only one master organization is allowed';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER single_master_org_trigger
        BEFORE INSERT OR UPDATE ON organizations
        FOR EACH ROW EXECUTE FUNCTION check_single_master_org();
    """)

    # Create the Master Organization
    master_org_id = "00000000-0000-0000-0000-000000000001"  # Fixed UUID for master org

    # Check if master org already exists
    result = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT COUNT(*) FROM organizations WHERE organization_type = 'master'"
            )
        )
        .fetchone()
    )

    if result[0] == 0:
        op.execute(f"""
            INSERT INTO organizations (
                id, name, slug, display_name, description,
                organization_type, status, billing_status, is_active,
                seat_limit, credit_limit, base_currency,
                created_at, updated_at
            ) VALUES (
                '{master_org_id}',
                'Master Organization',
                'master-org',
                'System Administration',
                'Master organization for system administration and B2B billing management',
                'master',
                'active',
                'active',
                true,
                999999,  -- Unlimited seats for master org
                999999,  -- Unlimited credits for master org
                'USD',
                '{datetime.now(timezone.utc).isoformat()}',
                '{datetime.now(timezone.utc).isoformat()}'
            )
        """)

    # Create index for faster queries on organization_type and billing_status
    op.create_index("ix_organizations_type", "organizations", ["organization_type"])
    op.create_index(
        "ix_organizations_billing_status", "organizations", ["billing_status"]
    )


def downgrade() -> None:
    """Remove master organization support and billing fields"""

    # Drop indexes
    op.drop_index("ix_organizations_billing_status", "organizations")
    op.drop_index("ix_organizations_type", "organizations")

    # Drop constraint and trigger
    op.execute("DROP TRIGGER IF EXISTS single_master_org_trigger ON organizations")
    op.execute("DROP FUNCTION IF EXISTS check_single_master_org()")

    # Remove master organization
    op.execute("DELETE FROM organizations WHERE organization_type = 'master'")

    # Remove added columns
    op.drop_column("organizations", "credit_limit")
    op.drop_column("organizations", "seat_limit")
    op.drop_column("organizations", "subscription_end_date")
    op.drop_column("organizations", "subscription_start_date")
    op.drop_column("organizations", "billing_status")

    # Note: Cannot easily remove enum values in PostgreSQL, they would remain but unused
