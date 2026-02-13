"""Merge bulk import/export jobs and quotations/sales orders heads

Revision ID: 003_merge_bulk_and_quotations
Revises: 002_add_bulk_import_export_jobs, 002
Create Date: 2026-02-12 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_merge_bulk_and_quotations"
down_revision = ("002_add_bulk_import_export_jobs", "002")
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
