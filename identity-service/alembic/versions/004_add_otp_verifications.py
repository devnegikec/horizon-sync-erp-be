"""add otp_verifications table

Revision ID: 004
Revises: 003
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "otp_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("otp_type", sa.String(20), nullable=False),  # email | mobile
        sa.Column("target", sa.String(255), nullable=False),   # email address or phone
        sa.Column("otp_code", sa.String(10), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_verifications_target", "otp_verifications", ["target"])
    op.create_index("ix_otp_verifications_otp_type", "otp_verifications", ["otp_type"])


def downgrade() -> None:
    op.drop_index("ix_otp_verifications_otp_type", table_name="otp_verifications")
    op.drop_index("ix_otp_verifications_target", table_name="otp_verifications")
    op.drop_table("otp_verifications")
