"""add_async_task_fields_to_qr_blocks

Revision ID: 037
Revises: 036_add_brands_enhance_qr_models
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '037'
down_revision = '036_add_brands_enhance_qr_models'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to qr_blocks table (only the ones not already added by 036)
    op.add_column('qr_blocks', sa.Column('error_message', sa.Text, nullable=True))
    op.add_column('qr_blocks', sa.Column('progress_current', sa.Integer, nullable=True))
    op.add_column('qr_blocks', sa.Column('progress_total', sa.Integer, nullable=True))

    # Add index on task_id column (if it doesn't already exist)
    try:
        op.create_index('idx_qr_blocks_task_id', 'qr_blocks', ['task_id'], unique=False)
    except Exception:
        pass  # Index might already exist

    # Backfill existing blocks
    op.execute("""
        UPDATE qr_blocks
        SET task_status = 'success'
        WHERE status = 'completed' AND task_status IS NULL
    """)

    op.execute("""
        UPDATE qr_blocks
        SET task_status = 'failure'
        WHERE status = 'failed' AND task_status IS NULL
    """)


def downgrade():
    # Remove index (if it exists)
    try:
        op.drop_index('idx_qr_blocks_task_id', table_name='qr_blocks')
    except Exception:
        pass

    # Remove columns (only the ones we added in this migration)
    op.drop_column('qr_blocks', 'progress_total')
    op.drop_column('qr_blocks', 'progress_current')
    op.drop_column('qr_blocks', 'error_message')
    # Note: task_status and task_id are from migration 036, so we don't drop them here
