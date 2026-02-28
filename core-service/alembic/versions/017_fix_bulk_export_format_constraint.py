"""Create bulk_export_jobs table if missing and fix file_format CHECK constraint

Revision ID: 017_fix_bulk_export_format
Revises: 016_merge_heads
Create Date: 2026-02-28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "017_fix_bulk_export_format"
down_revision = "016_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the table if it doesn't exist
    op.create_table(
        "bulk_export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_by_id", UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=True),
        sa.Column("file_format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING", index=True),
        sa.Column("total_rows", sa.String(20), nullable=False, server_default="0"),
        sa.Column("filters", JSONB, nullable=True),
        sa.Column("selected_columns", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')", name="chk_bulk_export_status"),
        sa.CheckConstraint("file_format IN ('csv', 'xlsx', 'json', 'pdf')", name="chk_bulk_export_format"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("bulk_export_jobs")
