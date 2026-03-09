"""Create bulk_export_jobs table if missing and fix file_format CHECK constraint

Revision ID: 018_fix_bulk_export_format
Revises: 017_add_bank_accounts_table
Create Date: 2026-02-28
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine.reflection import Inspector

from alembic import op

# revision identifiers, used by Alembic.
revision = "018_fix_bulk_export_format"
down_revision = "017_add_bank_accounts_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get the current connection and inspect existing tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # Create the table only if it doesn't exist
    if "bulk_export_jobs" not in existing_tables:
        op.create_table(
            "bulk_export_jobs",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id", UUID(as_uuid=True), nullable=False, index=True
            ),
            sa.Column("created_by_id", UUID(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("file_path", sa.String(255), nullable=True),
            sa.Column("file_format", sa.String(20), nullable=False),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="PENDING",
                index=True,
            ),
            sa.Column("total_rows", sa.String(20), nullable=False, server_default="0"),
            sa.Column("filters", JSONB, nullable=True),
            sa.Column("selected_columns", JSONB, nullable=True),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            # Constraints
            sa.CheckConstraint(
                "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
                name="chk_bulk_export_status",
            ),
            sa.CheckConstraint(
                "file_format IN ('csv', 'xlsx', 'json', 'pdf')",
                name="chk_bulk_export_format",
            ),
        )


def downgrade() -> None:
    # Check existence before dropping to avoid errors during rollback
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "bulk_export_jobs" in existing_tables:
        op.drop_table("bulk_export_jobs")
