"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-01-23 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get inspector to check if tables exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create enum types if they don't exist
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'organizationtype') THEN CREATE TYPE organizationtype AS ENUM ('enterprise', 'business', 'startup', 'individual'); END IF; END$$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'organizationstatus') THEN CREATE TYPE organizationstatus AS ENUM ('active', 'inactive', 'suspended', 'trial'); END IF; END$$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usertype') THEN CREATE TYPE usertype AS ENUM ('system_admin', 'organization_admin', 'user', 'guest'); END IF; END$$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstatus') THEN CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'suspended', 'pending'); END IF; END$$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resourcetype') THEN CREATE TYPE resourcetype AS ENUM ('user', 'organization', 'team', 'role', 'permission'); END IF; END$$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'actiontype') THEN CREATE TYPE actiontype AS ENUM ('create', 'read', 'update', 'delete', 'manage', 'execute'); END IF; END$$;"
    )

    # Create organizations table
    if "organizations" not in tables:
        op.create_table(
            "organizations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("address_line1", sa.String(length=255), nullable=True),
            sa.Column("address_line2", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=100), nullable=True),
            sa.Column("state", sa.String(length=100), nullable=True),
            sa.Column("postal_code", sa.String(length=20), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column(
                "organization_type",
                postgresql.ENUM(
                    "enterprise",
                    "business",
                    "startup",
                    "individual",
                    name="organizationtype",
                    create_type=False,
                ),
                nullable=True,
            ),
            sa.Column("industry", sa.String(length=100), nullable=True),
            sa.Column("tax_id", sa.String(length=100), nullable=True),
            sa.Column("logo_url", sa.String(length=500), nullable=True),
            sa.Column("primary_color", sa.String(length=7), nullable=True),
            sa.Column("domain", sa.String(length=255), nullable=True),
            sa.Column("sso_enabled", sa.Boolean(), nullable=True),
            sa.Column("sso_provider", sa.String(length=50), nullable=True),
            sa.Column(
                "sso_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "active",
                    "inactive",
                    "suspended",
                    "trial",
                    name="organizationstatus",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column(
                "extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_organizations_id"), "organizations", ["id"], unique=False
        )
        op.create_index(
            op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True
        )

    # Create users table
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("first_name", sa.String(length=100), nullable=False),
            sa.Column("last_name", sa.String(length=100), nullable=False),
            sa.Column("display_name", sa.String(length=200), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("avatar_url", sa.String(length=500), nullable=True),
            sa.Column(
                "user_type",
                postgresql.ENUM(
                    "system_admin",
                    "organization_admin",
                    "user",
                    "guest",
                    name="usertype",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "active",
                    "inactive",
                    "suspended",
                    "pending",
                    name="userstatus",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("email_verified", sa.Boolean(), nullable=False),
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("mfa_enabled", sa.Boolean(), nullable=True),
            sa.Column("mfa_secret", sa.String(length=255), nullable=True),
            sa.Column(
                "mfa_backup_codes",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login_ip", sa.String(length=45), nullable=True),
            sa.Column("failed_login_attempts", sa.Integer(), nullable=True),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("timezone", sa.String(length=50), nullable=True),
            sa.Column("language", sa.String(length=10), nullable=True),
            sa.Column(
                "extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # Create roles table
    if "roles" not in tables:
        op.create_table(
            "roles",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=True),
            sa.Column("hierarchy_level", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["organization_id"], ["organizations.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_roles_code"), "roles", ["code"], unique=False)
        op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
        op.create_index(
            op.f("ix_roles_organization_id"), "roles", ["organization_id"], unique=False
        )

    # Create permissions table
    if "permissions" not in tables:
        op.create_table(
            "permissions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "resource",
                postgresql.ENUM(
                    "user",
                    "organization",
                    "team",
                    "role",
                    "permission",
                    name="resourcetype",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "action",
                postgresql.ENUM(
                    "create",
                    "read",
                    "update",
                    "delete",
                    "manage",
                    "execute",
                    name="actiontype",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("module", sa.String(length=50), nullable=True),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_permissions_code"), "permissions", ["code"], unique=True
        )
        op.create_index(op.f("ix_permissions_id"), "permissions", ["id"], unique=False)

    # Create refresh_tokens table
    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("token_family", sa.String(length=255), nullable=True),
            sa.Column("device_id", sa.String(length=255), nullable=True),
            sa.Column("device_name", sa.String(length=255), nullable=True),
            sa.Column("device_type", sa.String(length=50), nullable=True),
            sa.Column("os_info", sa.String(length=100), nullable=True),
            sa.Column("browser_info", sa.String(length=100), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_reason", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_refresh_tokens_expires_at"),
            "refresh_tokens",
            ["expires_at"],
            unique=False,
        )
        op.create_index(
            op.f("ix_refresh_tokens_token_family"),
            "refresh_tokens",
            ["token_family"],
            unique=False,
        )
        op.create_index(
            op.f("ix_refresh_tokens_token_hash"),
            "refresh_tokens",
            ["token_hash"],
            unique=True,
        )
        op.create_index(
            op.f("ix_refresh_tokens_user_id"),
            "refresh_tokens",
            ["user_id"],
            unique=False,
        )

    # Create email_verifications table
    if "email_verifications" not in tables:
        op.create_table(
            "email_verifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_email_verifications_token_hash"),
            "email_verifications",
            ["token_hash"],
            unique=True,
        )

    # Create role_permissions table
    if "role_permissions" not in tables:
        op.create_table(
            "role_permissions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.ForeignKeyConstraint(
                ["permission_id"], ["permissions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_role_permissions_permission_id"),
            "role_permissions",
            ["permission_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_role_permissions_role_id"),
            "role_permissions",
            ["role_id"],
            unique=False,
        )

    # Create user_organization_roles table
    if "user_organization_roles" not in tables:
        op.create_table(
            "user_organization_roles",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["invited_by_id"],
                ["users.id"],
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"], ["organizations.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_user_organization_roles_organization_id"),
            "user_organization_roles",
            ["organization_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_user_organization_roles_role_id"),
            "user_organization_roles",
            ["role_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_user_organization_roles_user_id"),
            "user_organization_roles",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("user_organization_roles")
    op.drop_table("role_permissions")
    op.drop_table("email_verifications")
    op.drop_table("refresh_tokens")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("organizations")
