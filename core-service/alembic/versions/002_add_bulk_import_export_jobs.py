"""Add bulk import and export job tables

Revision ID: 002_add_bulk_import_export_jobs
Revises: 
Create Date: 2026-02-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_add_bulk_import_export_jobs"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bulk_import_jobs table
    op.create_table(
        "bulk_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bulk_import_jobs_organization_id",
        "bulk_import_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_bulk_import_jobs_status", "bulk_import_jobs", ["status"], unique=False
    )

    # Create bulk_export_jobs table
    op.create_table(
        "bulk_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=True),
        sa.Column("file_format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("total_rows", sa.String(20), nullable=False, server_default="0"),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("selected_columns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bulk_export_jobs_organization_id",
        "bulk_export_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_bulk_export_jobs_status", "bulk_export_jobs", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_bulk_export_jobs_status", table_name="bulk_export_jobs")
    op.drop_index(
        "ix_bulk_export_jobs_organization_id", table_name="bulk_export_jobs"
    )
    op.drop_table("bulk_export_jobs")
    op.drop_index("ix_bulk_import_jobs_status", table_name="bulk_import_jobs")
    op.drop_index(
        "ix_bulk_import_jobs_organization_id", table_name="bulk_import_jobs"
    )
    op.drop_table("bulk_import_jobs")
