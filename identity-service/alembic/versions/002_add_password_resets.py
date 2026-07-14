"""add password resets table

Revision ID: 002
Revises: 001
Create Date: 2024-01-23

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create password_resets table
    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])
    op.create_index(
        "ix_password_resets_token_hash", "password_resets", ["token_hash"], unique=True
    )
    op.create_index("ix_password_resets_expires_at", "password_resets", ["expires_at"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_password_resets_expires_at", table_name="password_resets")
    op.drop_index("ix_password_resets_token_hash", table_name="password_resets")
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")

    # Drop table
    op.drop_table("password_resets")
