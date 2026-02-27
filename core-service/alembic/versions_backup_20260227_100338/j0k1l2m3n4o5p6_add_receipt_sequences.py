"""add receipt sequences (one per year) for atomic receipt number generation

Revision ID: j0k1l2m3n4o5p6
Revises: i9j0k1l2m3n4
Create Date: 2025-02-23

Creates receipt_seq_2025 and receipt_seq_2026. Future years are created
on first use via the application (ensure_sequence_exists).
"""
from alembic import op
import sqlalchemy as sa

revision = "j0k1l2m3n4o5p6"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create receipt sequences for current and next year."""
    connection = op.get_bind()
    for year in (2025, 2026):
        seq_name = f"receipt_seq_{year}"
        connection.execute(sa.text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START 1"))
    # PostgreSQL 10+ has CREATE SEQUENCE IF NOT EXISTS; if older, use DO block
    # For PG < 10 compatibility (optional), uncomment below and remove CREATE above:
    # connection.execute(sa.text("""
    #     DO $$ DECLARE y int; BEGIN
    #       FOREACH y IN ARRAY ARRAY[2025, 2026] LOOP
    #         EXECUTE format('CREATE SEQUENCE IF NOT EXISTS receipt_seq_%s START 1', y);
    #       END LOOP;
    #     END $$;
    # """))


def downgrade() -> None:
    """Drop receipt sequences."""
    connection = op.get_bind()
    for year in (2025, 2026):
        seq_name = f"receipt_seq_{year}"
        connection.execute(sa.text(f"DROP SEQUENCE IF EXISTS {seq_name}"))
